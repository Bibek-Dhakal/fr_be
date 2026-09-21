# Task API & Background Reporting Service

A FastAPI CRUD API for a to-do list, now running with PostgreSQL in Docker.
The public API remains the same as A2; only the storage implementation changed
from SQLite to a PostgreSQL repository.

The project now includes a narrow AI workflow: `POST /triage` classifies one
support message into a fixed, validated JSON result. The existing PostgreSQL,
Docker, and Supabase authentication features remain available. It also includes a robust background jobs pipeline using
Inngest and Playwright to generate PDF reports, as well as a dynamic AI workflow engine.

## Stack

- FastAPI
- PostgreSQL 16
- Docker Compose
- Psycopg 3
- Supabase Auth
- Gemini through its OpenAI-compatible API
- Inngest Python SDK for durable background jobs
- Playwright (Headless Chromium) for PDF rendering
- SQLite (Dedicated dataset for PDF report generation and workflow state)

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
docker compose up --build -d
```

Seed the PDF reporting database (`report.db`) with 200 required shop orders:

```powershell
docker compose exec app python -m app.seed
```

The API is available at [http://localhost:8000](http://localhost:8000), and
Swagger UI is available at [http://localhost:8000/docs](http://localhost:8000/docs).

Start the local Inngest Dev Server in a second terminal:

```powershell
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```

Its dashboard is available at [http://localhost:8288](http://localhost:8288).
Local development requires no account, secret, or paid service.

The `db` service uses the named `postgres_data` volume. The `app` service waits
for PostgreSQL to become healthy before starting. `app/schema.sql` creates the
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

The route handlers in `app/main.py` keep the same endpoint paths, request
validation, response shapes, and status codes as A2. They call the
`PostgresTaskRepository` in `app/repository.py` instead of executing database
queries themselves. This is the storage swap required by the assignment:
the service/API behavior stays stable while the repository changes.

## Application layout

Runtime Python modules live under `app/`, with the LLM package in
`app/llm/`, its versioned prompt assets in `app/prompts/`, and the PostgreSQL
initialization schema in `app/schema.sql`. Start the API with the
`app.main:app` Uvicorn module path. The `evals/` directory is evaluation
tooling rather than application runtime code.

Documentation is organized under `docs/`: assignment history and job-card
materials are in [`docs/assignments/`](docs/assignments/), and interface and
database evidence is in [`docs/screenshots/`](docs/screenshots/). These
folders contain documentation only; they are not imported by the application.

## Endpoints

| Operation         | Method         | Endpoint                 | Description                                      |
|-------------------|----------------|--------------------------|--------------------------------------------------|
| API info          | `GET`          | `/`                      | Returns API information                          |
| Health check      | `GET`          | `/health`                | Returns service health                           |
| List              | `GET`          | `/tasks`                 | Returns all tasks                                |
| Read              | `GET`          | `/tasks/{id}`            | Returns one task                                 |
| Create            | `POST`         | `/tasks`                 | Creates a task                                   |
| Update            | `PUT`          | `/tasks/{id}`            | Updates a task                                   |
| Delete            | `DELETE`       | `/tasks/{id}`            | Deletes a task                                   |
| Sign up           | `POST`         | `/auth/signup`           | Creates a Supabase user                          |
| Log in            | `POST`         | `/auth/login`            | Returns access and refresh tokens                |
| Log out           | `POST`         | `/auth/logout`           | Protected; signs out the current session         |
| Public info       | `GET`          | `/public/info`           | Public, no token required                        |
| Profile           | `GET`          | `/protected/profile`     | Protected; verifies the bearer token             |
| Dashboard         | `GET`          | `/protected/dashboard`   | Protected; verifies the bearer token             |
| Triage            | `POST`         | `/triage`                | Classifies a support message with validated JSON |
| Start report      | `POST`         | `/reports`               | Validates a topic and queues a background report |
| Report status     | `GET`          | `/reports/{id}`          | Returns pending, done, or failed report state    |
| Start PDF report  | `POST`         | `/pdf-reports`           | Queues generation of the sales PDF               |
| PDF status        | `GET`          | `/pdf-reports/{id}`      | Returns PDF background queue status              |
| Download PDF      | `GET`          | `/pdf-reports/{id}/file` | Returns the actual PDF file generated            |
| Start AI Workflow | `POST`         | `/workflows`             | Submits nodes, edges, and input for AI graph     |
| Workflow status   | `GET`          | `/workflows/{id}`        | Polling endpoint for real-time node execution    |
| Inngest functions | `GET/POST/PUT` | `/api/inngest`           | Inngest Dev Server integration                   |

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
{
  "text": "The dashboard crashes every time I click Save."
}
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
parsed and validated against `app/llm/schema.py`; malformed output gets exactly one
repair attempt, then returns `422` and is written to
`logs/quarantine.jsonl`. Model calls use a 30-second timeout, no SDK retries,
and application retries only timeouts, `429`, and `5xx` responses with
bounded exponential backoff.

Each model response writes prompt version, model, token counts, duration, and
repair status to `logs/cost.jsonl`. The logs are ignored by Git.

## BE-06 background reports

`POST /reports` accepts `{"topic":"cats"}` and returns `202 Accepted` with an
ID and `pending` status without doing slow work. `GET /reports/{id}` first
returns `pending`, then `done` with a result, or `failed` with an error.
Unknown IDs return `404`; missing or blank topics return `400` before an event
is sent.

| Function              | Trigger              | Behavior                                     |
|-----------------------|----------------------|----------------------------------------------|
| `say-hello`           | `test/hello`         | Five-second durable sleep and greeting       |
| `make-report`         | `report/requested`   | Eight-second sleep, build step, retries=2    |
| `heartbeat`           | `* * * * *`          | Logs pending/done/failed counts every minute |
| `generate-pdf-report` | `pdf/requested`      | Queries DB and renders HTML -> PDF           |
| `execute-workflow`    | `workflow/requested` | Evaluates AI decision nodes along a graph    |

`make-report` is limited to two concurrent runs. Its database update only
transitions `pending` to `done`, so duplicate events cannot build the same
report twice. This idempotency guard matters because delivery and worker
retries can legitimately run a job more than once.

## BE-08 PDF Report Generator

This project supports an HTML-to-PDF reporting pipeline utilizing **Playwright Headless Chromium**. The generation
logic (`query` -> `render` -> `store`) natively incorporates the BE-06 background job stretch pattern. Generating a
large HTML table inside a web request hangs the server; moving this slow work completely out of the request solves
performance latency for clients waiting to do other actions.

## BE-09 AI Workflow Execution

This stage introduces a visual AI workflow runner connected to a dedicated React frontend. The FastAPI backend exposes
conditional logic endpoints (`POST /workflows`) that accept a serialized React Flow graph (nodes and edges) along with
user input text.

The execution is processed in the background using Inngest:

1. The background worker parses the provided graph and isolates the starting root node.
2. The LLM evaluates the node's custom prompt against the user's text. The model is constrained to output exclusively
   `YES` or `NO`.
3. The engine uses the model's decision to route traversal across the exact matching edge to the next connected node.
4. Active execution state, the currently processing node, and historical decision logs are written to SQLite and
   streamed to the frontend for visualization.

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

## BE-07 AI assignment stage summary

- Stage 0: provider configuration and stub mode
- Stage 1: triage endpoint, input validation, and output schema
- Stage 2: versioned prompt asset and endpoint wiring
- Stage 3: parsing, validation, one repair attempt, and quarantine
- Stage 4: timeout, retry policy, cost logging, and kill switch
- Stage 5: evaluation set, results, and publication

## W4 stage summary

- Stage 0: Supabase client and environment configuration
- Stage 1: signup and login routes
- Stage 2: public route and bearer-header protection
- Stage 3: Supabase token verification
- Stage 4: reusable auth dependency and logout
- Stage 5: Swagger bearer authorization
- Stage 6: this README and GitHub publication

## Documentation assets

- [BE-07 job card](docs/assignments/be-07-job-card.md)
- [Swagger UI screenshot](docs/screenshots/swagger-screenshot.jpeg)
- [Database browser screenshot](docs/screenshots/db-browser-screenshot.jpeg)
- [Inngest Dashboard](docs/screenshots/inngest-dashboard.jpeg)
- [PDF Report](docs/screenshots/pdf-report.jpeg)

The active stack uses PostgreSQL and Docker Compose. The screenshots document
prior and current assignment evidence; they do not describe a second runtime
or database configuration.
