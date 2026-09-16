# Task API (Week 3 - A3 Containerize Your Stack)

A FastAPI CRUD API for a to-do list, now running with PostgreSQL in Docker.
The public API remains the same as A2; only the storage implementation changed
from SQLite to a PostgreSQL repository.

## Stack

- FastAPI
- PostgreSQL 16
- Docker Compose
- Psycopg 3

## Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

`.env` is ignored by Git. It contains the local PostgreSQL credentials and
connection string. `.env.example` is committed so another developer knows which
variables are required.

## Run the complete stack

Install Docker Desktop, then run:

```powershell
docker compose up --build
```

The API is available at [http://localhost:8000](http://localhost:8000), and
Swagger UI is available at [http://localhost:8000/docs](http://localhost:8000/docs).

The `db` service uses the named `postgres_data` volume. The `app` service waits
for PostgreSQL to become healthy before starting. `schema.sql` creates the
`tasks` table and inserts the three example tasks only when the table is empty.

Stop the stack without deleting data:

```powershell
docker compose down
```

To intentionally delete the persisted database volume:

```powershell
docker compose down -v
```

## A3 architecture

The route handlers in `main.py` keep the same endpoint paths, request
validation, response shapes, and status codes as A2. They call the
`PostgresTaskRepository` in `repository.py` instead of executing database
queries themselves. This is the storage swap required by the assignment:
the service/API behavior stays stable while the repository changes.

## Endpoints

| Operation | Method | Endpoint | Description |
| --- | --- | --- | --- |
| API info | `GET` | `/` | Returns API information |
| Health check | `GET` | `/health` | Returns service health |
| List | `GET` | `/tasks` | Returns all tasks |
| Read | `GET` | `/tasks/{id}` | Returns one task |
| Create | `POST` | `/tasks` | Creates a task |
| Update | `PUT` | `/tasks/{id}` | Updates a task |
| Delete | `DELETE` | `/tasks/{id}` | Deletes a task |

Unknown IDs return `404` with `{"error": "Task {id} not found"}`. Missing or
empty titles return `400`.

## Persistence proof

1. Start the stack with `docker compose up --build`.
2. Create a task through Swagger UI or with:

   ```powershell
   curl.exe -i -X POST http://localhost:8000/tasks `
     -H "Content-Type: application/json" `
     -d '{"title":"Survives restart"}'
   ```

3. Stop only the application:

   ```powershell
   docker compose stop app
   ```

4. Restart the application and confirm the task remains:

   ```powershell
   docker compose start app
   curl.exe http://localhost:8000/tasks
   ```

5. Restart both containers without removing the volume:

   ```powershell
   docker compose down
   docker compose up --build
   curl.exe http://localhost:8000/tasks
   ```

The task remains because PostgreSQL data is stored in the `postgres_data`
Docker volume. Do not use `docker compose down -v` during this persistence
test because that deliberately removes the database.

## Previous A2 artifacts

The repository retains the A2 SQLite artifacts and screenshots in Git history.
The active A3 stack uses PostgreSQL and Docker Compose.
