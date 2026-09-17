# Assignment history

This project keeps the prior assignment record alongside the current
implementation. A2 is historical because A3 replaced SQLite with PostgreSQL,
but its stages and API contract remain part of the repository history.

## A2 - SQLite stages 0-5

- **Stage 0 - API foundation:** established the FastAPI task service and its
  initial CRUD contract.
- **Stage 1 - SQLite connection:** added the SQLite database file and startup
  initialization for the `tasks` table.
- **Stage 2 - Persistent CRUD:** moved task create, read, update, and delete
  operations from in-memory storage to SQLite queries.
- **Stage 3 - Validation and errors:** retained required-title validation,
  `400` responses for invalid input, and `404` responses for unknown task IDs.
- **Stage 4 - SQL inspection:** documented the SQL used to inspect and verify
  persisted records in DB Browser for SQLite.
- **Stage 5 - evidence and publication:** captured Swagger/database evidence
  and published the A2 documentation. The screenshots remain under
  [`../screenshots/`](../screenshots/).

## A3 - Docker and PostgreSQL

A3 kept the A2 routes, validation, response shapes, and status codes while
moving database access into `PostgresTaskRepository`. Docker Compose now runs
the FastAPI service with PostgreSQL 16, a health check, a named
`postgres_data` volume, and `app/schema.sql` initialization. The active
runtime details are in the root [README](../../README.md).

## W4 - Supabase Auth stages

- **Stage 0:** Supabase client and environment configuration.
- **Stage 1:** signup and login routes.
- **Stage 2:** public route and bearer-header protection.
- **Stage 3:** Supabase token verification.
- **Stage 4:** reusable auth dependency and logout.
- **Stage 5:** Swagger bearer authorization.
- **Stage 6:** README documentation and GitHub publication.

## BE-07 - AI stages

- **Stage 0:** provider configuration and deterministic stub mode.
- **Stage 1:** triage endpoint, input validation, and output schema.
- **Stage 2:** versioned prompt asset and endpoint wiring.
- **Stage 3:** parsing, validation, one repair attempt, and quarantine.
- **Stage 4:** timeout, retry policy, cost logging, and kill switch.
- **Stage 5:** evaluation set, results, and publication.

All four assignment histories are retained deliberately. Later stages extend
or replace runtime components without deleting the earlier assignment record.
