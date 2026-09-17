import os

from fastapi import Depends, FastAPI, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import APITimeoutError

from app.repository import PostgresTaskRepository
from app.supabase_client import create_supabase_client
from app.llm.client import complete_triage
from app.llm.client import PROMPT_VERSION
from app.llm.parse import parse_triage_output
from app.llm.quarantine import quarantine_triage
from app.llm.schema import TriageRequest, TriageResult
from app.reports import functions as report_functions
from app.reports import inngest_client, report_store
from inngest.fast_api import serve as serve_inngest
import inngest

app = FastAPI(
    title="Task API",
    description="A simple CRUD API managing a to-do list.",
    version="1.0",
)
repository = PostgresTaskRepository()
supabase = None
bearer_scheme = HTTPBearer(auto_error=False)


def auth_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


class AuthFailure(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


def require_credentials(payload: dict) -> tuple[str, str] | JSONResponse:
    email = payload.get("email")
    password = payload.get("password")
    if (
        not isinstance(email, str)
        or not email.strip()
        or not isinstance(password, str)
        or not password
    ):
        return auth_error("Email and password are required", 400)
    return email.strip(), password


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthFailure("Access token required")
    token = credentials.credentials

    try:
        response = supabase.auth.get_user(token)
    except Exception:
        raise AuthFailure("Invalid or expired token")

    if response.user is None:
        raise AuthFailure("Invalid or expired token")
    return {"token": token, "user": response.user}


@app.on_event("startup")
def initialize_database() -> None:
    global supabase
    repository.initialize()
    supabase = create_supabase_client()


@app.exception_handler(AuthFailure)
def auth_failure_handler(_request: Request, exc: AuthFailure):
    return auth_error(exc.message, 401)


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED, summary="Sign Up")
def signup(payload: dict):
    """Creates a Supabase user account."""
    credentials = require_credentials(payload)
    if isinstance(credentials, JSONResponse):
        return credentials

    email, password = credentials
    try:
        response = supabase.auth.sign_up(
            {"email": email, "password": password}
        )
    except Exception:
        return auth_error("Unable to create account", 400)

    if response.user is None:
        return auth_error("Unable to create account", 400)
    return {"user": response.user}


@app.post("/auth/login", summary="Log In")
def login(payload: dict):
    """Authenticates a user with Supabase and returns session tokens."""
    credentials = require_credentials(payload)
    if isinstance(credentials, JSONResponse):
        return credentials

    email, password = credentials
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception:
        return auth_error("Invalid login credentials", 401)

    if response.session is None:
        return auth_error("Invalid login credentials", 401)

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }


@app.post(
    "/triage",
    response_model=TriageResult,
    summary="Triage Support Message",
)
def triage(payload: dict):
    """Classifies a support message into a closed, validated result shape."""
    try:
        request = TriageRequest.model_validate(payload)
    except ValidationError as error:
        field = error.errors()[0].get("loc", ["field"])[0]
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid field: {field}"},
        )

    if os.getenv("LLM_ENABLED", "true").lower() == "false" or os.getenv("LLM_STUB") == "1":
        return TriageResult(
            category="other",
            urgency="normal",
            confidence=0.1,
            reason="Stub mode is enabled; human review is required.",
        )
    try:
        raw_output = complete_triage(request.text)
        try:
            return parse_triage_output(raw_output)
        except ValueError as first_error:
            repaired_output = complete_triage(
                request.text,
                previous_output=raw_output,
                validation_error=str(first_error),
                repair=True,
            )
            try:
                return parse_triage_output(repaired_output)
            except ValueError as final_error:
                quarantine_triage(
                    request.text,
                    repaired_output,
                    str(final_error),
                    PROMPT_VERSION,
                )
                return JSONResponse(
                    status_code=422,
                    content={"error": "Model output could not be validated"},
                )
    except APITimeoutError:
        return JSONResponse(
            status_code=504,
            content={"error": "The AI provider timed out"},
        )
    except Exception as error:
        return JSONResponse(status_code=502, content={"error": str(error)})


def extract_access_token(authorization: str | None) -> str | JSONResponse:
    if not authorization or not authorization.startswith("Bearer "):
        return auth_error("Access token required", 401)

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return auth_error("Access token required", 401)
    return token


@app.get("/public/info", summary="Public Information")
def public_info():
    """Returns information that does not require authentication."""
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", summary="Protected Profile")
def protected_profile(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated user's profile."""
    user = current_user["user"]
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/protected/dashboard", summary="Protected Dashboard")
def protected_dashboard(_current_user: dict = Depends(get_current_user)):
    """Returns a protected dashboard response."""
    return {"message": "Welcome to your protected dashboard."}


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log Out")
def logout(current_user: dict = Depends(get_current_user)):
    """Terminates the current Supabase session."""
    try:
        supabase.auth.sign_out(current_user["token"])
    except Exception:
        return auth_error("Unable to log out", 401)
    return None


@app.get("/", summary="API Info")
def root():
    """Returns the API description and available endpoints."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health Check")
def health():
    """Returns the health status of the API."""
    return {"status": "ok"}


@app.post("/reports", status_code=status.HTTP_202_ACCEPTED, summary="Start Report")
async def create_report(payload: dict):
    topic = payload.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return JSONResponse(status_code=400, content={"error": "Topic is required"})

    report = report_store.create(topic.strip())
    if os.getenv("INNGEST_STUB") != "1":
        try:
            await inngest_client.send(
                inngest.Event(
                    name="report/requested",
                    data={"id": report["id"], "topic": report["topic"]},
                )
            )
        except Exception as error:
            report_store.fail(report["id"], str(error))
            return JSONResponse(
                status_code=503,
                content={"error": "Unable to queue report"},
            )
    return {"id": report["id"], "status": report["status"]}


@app.get("/reports/{report_id}", summary="Get Report Status")
def get_report(report_id: str):
    report = report_store.get(report_id)
    if report is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Report {report_id} not found"},
        )
    return report


@app.get("/tasks", summary="List Tasks")
def get_tasks():
    """Returns the complete list of tasks from the repository."""
    return repository.list_tasks()


@app.get("/tasks/{task_id}", summary="Get Single Task")
def get_task(task_id: int):
    """Returns a specific task by ID from the repository."""
    task = repository.get_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return task


@app.post("/tasks", status_code=status.HTTP_201_CREATED, summary="Create Task")
def create_task(payload: dict):
    """Creates a new task in the repository. Title is required."""
    title = payload.get("title")
    if not title or not str(title).strip():
        return JSONResponse(
            status_code=400, content={"error": "Title is missing or empty"}
        )
    return repository.create_task(str(title).strip())


@app.put("/tasks/{task_id}", summary="Update Task")
def update_task(task_id: int, payload: dict):
    """Updates an existing task's title or done status in the repository."""
    if not payload:
        return JSONResponse(
            status_code=400, content={"error": "Request body is empty"}
        )

    current_task = repository.get_task(task_id)
    if current_task is None:
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )

    new_title = current_task["title"]
    new_done = current_task["done"]

    if "title" in payload:
        title = payload["title"]
        if not title or not str(title).strip():
            return JSONResponse(
                status_code=400, content={"error": "Title is missing or empty"}
            )
        new_title = str(title).strip()

    if "done" in payload:
        new_done = bool(payload["done"])

    return repository.update_task(task_id, new_title, new_done)


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Task",
)
def delete_task(task_id: int):
    """Deletes a task by ID from the repository."""
    if not repository.delete_task(task_id):
        return JSONResponse(
            status_code=404, content={"error": f"Task {task_id} not found"}
        )
    return None


serve_inngest(app, inngest_client, report_functions)
