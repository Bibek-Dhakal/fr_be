from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse

from repository import PostgresTaskRepository
from supabase_client import create_supabase_client

app = FastAPI(
    title="Task API",
    description="A simple CRUD API managing a to-do list.",
    version="1.0",
)
repository = PostgresTaskRepository()
supabase = None


def auth_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


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


@app.on_event("startup")
def initialize_database() -> None:
    global supabase
    repository.initialize()
    supabase = create_supabase_client()


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
def protected_profile(authorization: str | None = Header(default=None)):
    """Verifies a bearer token and returns the authenticated user's profile."""
    token = extract_access_token(authorization)
    if isinstance(token, JSONResponse):
        return token

    try:
        response = supabase.auth.get_user(token)
    except Exception:
        return auth_error("Invalid or expired token", 401)

    user = response.user
    if user is None:
        return auth_error("Invalid or expired token", 401)

    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/", summary="API Info")
def root():
    """Returns the API description and available endpoints."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health Check")
def health():
    """Returns the health status of the API."""
    return {"status": "ok"}


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
