from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Task API",
    description="A simple CRUD API managing a to-do list.",
    version="1.0"
)

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Read a book", "done": True},
    {"id": 3, "title": "Write some code", "done": False}
]


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
    """Returns the complete list of tasks."""
    return tasks


@app.get("/tasks/{task_id}", summary="Get Single Task")
def get_task(task_id: int):
    """Returns a specific task by ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


@app.post("/tasks", status_code=status.HTTP_201_CREATED, summary="Create Task")
def create_task(payload: dict):
    """Creates a new task. Title is required."""
    title = payload.get("title")
    if not title or not str(title).strip():
        return JSONResponse(status_code=400, content={"error": "Title is missing or empty"})

    new_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {"id": new_id, "title": str(title).strip(), "done": False}
    tasks.append(new_task)
    return new_task


@app.put("/tasks/{task_id}", summary="Update Task")
def update_task(task_id: int, payload: dict):
    """Updates an existing task's title or done status."""
    if not payload:
        return JSONResponse(status_code=400, content={"error": "Request body is empty"})

    for task in tasks:
        if task["id"] == task_id:
            if "title" in payload:
                title = payload["title"]
                if not title or not str(title).strip():
                    return JSONResponse(status_code=400, content={"error": "Title is missing or empty"})
                task["title"] = str(title).strip()
            if "done" in payload:
                task["done"] = bool(payload["done"])
            return task

    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Task")
def delete_task(task_id: int):
    """Deletes a task by ID."""
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            del tasks[i]
            return None

    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
