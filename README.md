# Task API (Week 7 - Connect to an AI API)

A FastAPI CRUD API for a to-do list, now running with PostgreSQL in Docker.
The public API remains the same as A2; only the storage implementation changed
from SQLite to a PostgreSQL repository.

The project now includes a narrow AI workflow: `POST /triage` classifies one
support message into a fixed, validated JSON result. The existing PostgreSQL,
Docker, and Supabase authentication features remain available.

## Stack

- FastAPI
- PostgreSQL 16
- Docker Compose
- Psycopg 3
- Supabase Auth
- Gemini through its OpenAI-compatible API

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

The LLM provider is configured with three environment variables:

```env
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=your-gemini-api-key
LLM_MODEL=gemini-3.6-flash
```

Changing those three values is enough to use another OpenAI-compatible
provider. `LLM_ENABLED=false` disables model calls and returns a deterministic
low-confidence `other` result.

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
| Triage | `POST` | `/triage` | Classifies a support message with validated JSON |

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

## AI triage

`POST /triage` accepts:

```json
{"text":"The dashboard crashes every time I click Save."}
```

and returns:

```json
{
  "category": "bug",
  "urgency": "high",
  "confidence": 0.94,
  "reason": "The customer reports a repeatable dashboard failure."
}
```

Run it with:

```powershell
curl.exe -i -X POST http://localhost:8000/triage `
  -H "Content-Type: application/json" `
  -d '{"text":"The dashboard crashes every time I click Save."}'
```

Invalid input is rejected with `400` before a model call. Model output is
parsed and validated against `llm/schema.py`; malformed output gets exactly one
repair attempt, then returns `422` and is written to
`logs/quarantine.jsonl`. Model calls use a 30-second timeout, no SDK retries,
and application retries only timeouts, `429`, and `5xx` responses with
bounded exponential backoff.

Each model response writes prompt version, model, token counts, duration, and
repair status to `logs/cost.jsonl`. The logs are ignored by Git.

## Evaluation

The eight labelled cases are in `evals/cases.json`. Run the live evaluation
after configuring Gemini:

```powershell
.\.venv\Scripts\python.exe evals\run.py
```

The result must be recorded here with the date and prompt version after the
run.

**Evaluation result (2026-09-17, prompt `triage-v1`):** `6/8` category
matches (`75%`). The final two cases were blocked by Gemini's free-tier
per-minute quota after five requests, so this is a quota-limited result rather
than a claim that all eight model judgements were successful. The two failed
requests were recorded by the runner as provider `429` errors.

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
