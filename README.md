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

---

## Stage 7: AI vs. Me

**Prompt I used for the AI:**
> "Build a FastAPI CRUD app for a to-do list with in-memory storage, input validation, and specific 400/404 error
> messages. Title is required and cannot be empty. Follow REST best practices. Output the code."

**What the AI did better (and what I understood):**
The AI used FastAPI's `Pydantic` `BaseModel` pattern strictly, which gives you built-in type validation and OpenAPI
schema generation for request bodies out of the box. I used plain dictionaries (`payload: dict`) for closer manual
control over the `400` status requirements.

**What it got wrong or quietly ignored:**
Because the AI used `Pydantic`, passing missing JSON fields automatically throws a `422 Unprocessable Entity` response,
rather than the `400 Bad Request` explicitly requested in the prompt and assignment instructions. It also structured the
404 response payloads as `{"detail": "Task not found"}` because of `HTTPException`, ignoring the assignment's explicit
rule to return `{"error": "Task not found"}`.

**What my prompt forgot to specify & what the AI decided silently:**
I forgot to specify the exact schema shape (`{"error": "message"}`) and how to handle updates (`PUT`). The AI silently
completely skipped implementing the `PUT` endpoint because I didn't explicitly ask for it to do an "Update" route. It
also created a global `current_id` variable instead of deriving the next ID dynamically from the array.
