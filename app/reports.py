import asyncio
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Iterator

import inngest
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("report-api")


class ReportStore:
    """Durable report state with an explicit memory mode for local tests."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost:5432/tasks_db",
        )
        self._memory = os.getenv("REPORTS_IN_MEMORY") == "1"
        self._reports: dict[str, dict[str, Any]] = {}

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def create(self, topic: str) -> dict[str, Any]:
        report_id = str(uuid.uuid4())
        report = {"id": report_id, "topic": topic, "status": "pending"}
        if self._memory:
            self._reports[report_id] = report
            return report.copy()
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO reports (id, topic, status)
                VALUES (%s, %s, 'pending')
                RETURNING id, topic, status
                """,
                (report_id, topic),
            )
            return dict(cursor.fetchone())

    def get(self, report_id: str) -> dict[str, Any] | None:
        if self._memory:
            report = self._reports.get(report_id)
            if not report:
                return None
            return {
                key: value
                for key, value in report.items()
                if key != "processing" and value is not None
            }
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, topic, status, result, error
                FROM reports
                WHERE id = %s
                """,
                (report_id,),
            )
            report = cursor.fetchone()
            if not report:
                return None
            return {
                key: value
                for key, value in dict(report).items()
                if value is not None
            }

    def complete(self, report_id: str, result: str) -> bool:
        if self._memory:
            report = self._reports.get(report_id)
            if not report or report["status"] != "pending":
                return False
            report.update({"status": "done", "result": result, "processing": False})
            return True
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE reports
                SET status = 'done', result = %s, processing = FALSE, updated_at = NOW()
                WHERE id = %s AND status = 'pending'
                """,
                (result, report_id),
            )
            return cursor.rowcount == 1

    def fail(self, report_id: str, error: str) -> None:
        if self._memory:
            report = self._reports.get(report_id)
            if report:
                report.update({"status": "failed", "error": error, "processing": False})
            return
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE reports
                SET status = 'failed', error = %s, processing = FALSE, updated_at = NOW()
                WHERE id = %s AND status != 'done'
                """,
                (error, report_id),
            )

    def claim(self, report_id: str) -> bool:
        if self._memory:
            report = self._reports.get(report_id)
            if not report or report.get("processing"):
                return False
            report["processing"] = True
            return True
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE reports
                SET processing = TRUE, updated_at = NOW()
                WHERE id = %s AND status = 'pending' AND processing = FALSE
                """,
                (report_id,),
            )
            return cursor.rowcount == 1

    def counts(self) -> dict[str, int]:
        if self._memory:
            counts = {"pending": 0, "done": 0, "failed": 0}
            for report in self._reports.values():
                counts[report["status"]] += 1
            return counts
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, COUNT(*)::int AS count
                FROM reports
                GROUP BY status
                """
            )
            counts = {"pending": 0, "done": 0, "failed": 0}
            for row in cursor.fetchall():
                counts[row["status"]] = row["count"]
            return counts


report_store = ReportStore()
inngest_client = inngest.Inngest(
    app_id="report-api",
    event_key=os.getenv("INNGEST_EVENT_KEY"),
    is_production=os.getenv("INNGEST_PRODUCTION", "false").lower() == "true",
)


async def _build_report(report_id: str, topic: str) -> str:
    if topic.casefold() == "fail":
        raise RuntimeError("The report oven is broken!")
    await asyncio.sleep(0)
    return f"Report for {topic}: background work completed."


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("hello-sleep", timedelta(seconds=5))
    return await ctx.step.run(
        "hello-result",
        lambda: "Hello from the background!",
    )


@inngest_client.create_function(
    fn_id="make-report",
    name="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
    concurrency=[inngest.Concurrency(limit=2, scope="fn")],
)
async def make_report(ctx: inngest.Context) -> dict[str, Any]:
    report_id = str(ctx.event.data["id"])
    topic = str(ctx.event.data["topic"])
    if not report_store.claim(report_id):
        existing = report_store.get(report_id)
        return {
            "id": report_id,
            "status": existing["status"] if existing else "missing",
        }
    try:
        await ctx.step.sleep("do-the-slow-work", timedelta(seconds=8))
        result = await ctx.step.run(
            "build-report",
            _build_report,
            report_id,
            topic,
        )
        report_store.complete(report_id, result)
        return {"id": report_id, "status": "done"}
    except Exception as error:
        report_store.fail(report_id, str(error))
        raise


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(_ctx: inngest.Context) -> dict[str, int]:
    counts = report_store.counts()
    logger.info(
        "report heartbeat pending=%d done=%d failed=%d",
        counts["pending"],
        counts["done"],
        counts["failed"],
    )
    return counts


functions = [say_hello, make_report, heartbeat]
