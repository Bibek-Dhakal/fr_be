# Task API (Week 2 - A1 CRUD Assignment)

This is a simple, in-memory CRUD (Create, Read, Update, Delete) API for managing a to-do list, built using Python and
FastAPI.

## How to Install & Run

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.min.txt
   ```

3. **Start the development server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## Endpoints Table

| Operation | Method   | Endpoint      | Description                              |
|-----------|----------|---------------|------------------------------------------|
| Meta      | `GET`    | `/`           | Returns API info                         |
| Meta      | `GET`    | `/health`     | Health check endpoint                    |
| Read      | `GET`    | `/tasks`      | List all tasks                           |
| Read      | `GET`    | `/tasks/{id}` | Get a specific task by ID                |
| Create    | `POST`   | `/tasks`      | Add a new task                           |
| Update    | `PUT`    | `/tasks/{id}` | Update task details (title, done status) |
| Delete    | `DELETE` | `/tasks/{id}` | Remove a task                            |

## Example Request

**Create a new task:**

for Windows PowerShell, use the following command:

```bash
curl.exe -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "@test_data/task_post_body.json"
```

for macOS/Linux, use the following command:

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "@test_data/task_post_body.json"
```

**Output:**

```http
HTTP/1.1 201 Created
date: Wed, 16 Sep 2026 12:16:56 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

FastAPI automatically generates a Swagger UI interface. Once the server is running, visit:
[http://localhost:8000/docs](http://localhost:8000/docs)

*(Screenshot of Swagger UI)*
![Swagger UI Screenshot](./swagger_screenshot.jpeg)
