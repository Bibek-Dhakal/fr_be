# Task API (Week 4 - Auth Login and Protect)

A FastAPI CRUD API for a to-do list, now running with PostgreSQL in Docker.
The public API remains the same as A2; only the storage implementation changed
from SQLite to a PostgreSQL repository.

W4 adds Supabase Auth configuration. Authentication routes and protected
endpoints are added stage by stage.

## Stack

- FastAPI
- PostgreSQL 16
- Docker Compose
- Psycopg 3
- Supabase Auth

## Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

`.env` is ignored by Git. It contains the local PostgreSQL credentials and
connection string, plus the Supabase project URL and anon key. `.env.example`
is committed so another developer knows which variables are required.

Create a Supabase project, then copy the values from **Project Settings ->
API** into `.env`:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

The application creates the Supabase client during startup and fails with a
clear configuration error if either value is missing. Never commit `.env` or
real Supabase keys.

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
| Sign up | `POST` | `/auth/signup` | Creates a Supabase user |
| Log in | `POST` | `/auth/login` | Returns access and refresh tokens |
| Log out | `POST` | `/auth/logout` | Protected; signs out the current session |
| Public info | `GET` | `/public/info` | Public, no token required |
| Profile | `GET` | `/protected/profile` | Protected; verifies the bearer token |
| Dashboard | `GET` | `/protected/dashboard` | Protected; verifies the bearer token |

Unknown IDs return `404` with `{"error": "Task {id} not found"}`. Missing or
empty titles return `400`.

Protected endpoints require:

```text
Authorization: Bearer <access_token>
```

Missing or malformed tokens return `401` with
`{"error": "Access token required"}`. Invalid or expired tokens return `401`
with `{"error": "Invalid or expired token"}`.

## Auth flow

Sign up:

```powershell
curl.exe -i -X POST http://localhost:8000/auth/signup `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"password123"}'
```

Log in and copy the returned `access_token`:

```powershell
curl.exe -i -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"password123"}'
```

Use the token with the protected profile route:

```powershell
curl.exe -i http://localhost:8000/protected/profile `
  -H "Authorization: Bearer <access_token>"
```

Swagger UI at `/docs` includes the **Authorize** button and bearer security
metadata for `/protected/profile`, `/protected/dashboard`, and
`/auth/logout`.

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

## W4 stage summary

- Stage 0: Supabase client and environment configuration
- Stage 1: signup and login routes
- Stage 2: public route and bearer-header protection
- Stage 3: Supabase token verification
- Stage 4: reusable auth dependency and logout
- Stage 5: Swagger bearer authorization
- Stage 6: this README and GitHub publication

## Previous A2 artifacts

The repository retains the A2 SQLite artifacts and screenshots in Git history.
The active A3 stack uses PostgreSQL and Docker Compose.
