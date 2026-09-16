from fastapi import FastAPI, status
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


@app.on_event("startup")
def initialize_database() -> None:
    global supabase
    repository.initialize()
    supabase = create_supabase_client()


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
