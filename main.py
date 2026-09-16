import sqlite3

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Task API",
    description="A simple CRUD API managing a to-do list.",
    version="1.0"
)


def get_db_connection():
    conn = sqlite3.connect("tasks.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS tasks
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       title
                       TEXT
                       NOT
                       NULL,
                       done
                       BOOLEAN
                       NOT
                       NULL
                       CHECK (
                       done
                       IN
                   (
                       0,
                       1
                   ))
                       )
                   """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [("Buy milk", 0), ("Read a book", 1), ("Write some code", 0)]
        )
    conn.commit()
    conn.close()


init_db()


def row_to_dict(row):
    d = dict(row)
    d["done"] = bool(d["done"])
    return d


# Temporary in-memory list (will be completely removed in stage 3)
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
    """Returns the complete list of tasks from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]


@app.get("/tasks/{task_id}", summary="Get Single Task")
def get_task(task_id: int):
    """Returns a specific task by ID from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row_to_dict(row)

    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


@app.post("/tasks", status_code=status.HTTP_201_CREATED, summary="Create Task")
def create_task(payload: dict):
    """Creates a new task in the database. Title is required."""
    title = payload.get("title")
    if not title or not str(title).strip():
        return JSONResponse(status_code=400, content={"error": "Title is missing or empty"})

    conn = get_db_connection()
    cursor = conn.cursor()
    # Insert new record using parameterized queries to prevent SQL injection
    cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (str(title).strip(), 0))
    conn.commit()
    new_id = cursor.lastrowid

    # Fetch the newly created record
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
    new_task = row_to_dict(cursor.fetchone())
    conn.close()

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
