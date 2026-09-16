from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI()

tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Read a book", "done": True},
    {"id": 3, "title": "Write some code", "done": False}
]


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: dict):
    title = payload.get("title")
    if not title or not str(title).strip():
        return JSONResponse(status_code=400, content={"error": "Title is missing or empty"})

    new_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {"id": new_id, "title": str(title).strip(), "done": False}
    tasks.append(new_task)
    return new_task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: dict):
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


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            del tasks[i]
            return
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
