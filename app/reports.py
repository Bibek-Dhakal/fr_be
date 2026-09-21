import asyncio
import json
import logging
import os
import sqlite3
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
                VALUES (%s, %s, 'pending') RETURNING id, topic, status
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
                SET status     = 'done',
                    result     = %s,
                    processing = FALSE,
                    updated_at = NOW()
                WHERE id = %s
                  AND status = 'pending'
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
                SET status     = 'failed',
                    error      = %s,
                    processing = FALSE,
                    updated_at = NOW()
                WHERE id = %s
                  AND status != 'done'
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
                SET processing = TRUE,
                    updated_at = NOW()
                WHERE id = %s
                  AND status = 'pending'
                  AND processing = FALSE
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
                SELECT status, COUNT(*) ::int AS count
                FROM reports
                GROUP BY status
                """
            )
            counts = {"pending": 0, "done": 0, "failed": 0}
            for row in cursor.fetchall():
                counts[row["status"]] = row["count"]
            return counts


report_store = ReportStore()

# Ensure event_key is never an empty string, which causes URL resolution issues locally
event_key = os.getenv("INNGEST_EVENT_KEY")
if not event_key:
    event_key = "local"

inngest_client = inngest.Inngest(
    app_id="report-api",
    event_key=event_key,
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


@inngest_client.create_function(
    fn_id="generate-pdf-report",
    name="generate-pdf-report",
    trigger=inngest.TriggerEvent(event="pdf/requested"),
)
async def generate_pdf_report(ctx: inngest.Context) -> dict[str, Any]:
    report_id = str(ctx.event.data["id"])

    async def _do_render() -> str:
        from app.pdf_generator import get_report_data, render_pdf
        data = get_report_data()
        path = f"reports/{report_id}.pdf"
        await render_pdf(data, path)
        return path

    file_path = await ctx.step.run("render-pdf", _do_render)

    def _update_db() -> None:
        with sqlite3.connect("report.db") as conn:
            conn.execute(
                "UPDATE pdf_reports SET status = 'done', file = ? WHERE id = ?",
                (file_path, report_id)
            )

    await ctx.step.run("update-db", _update_db)
    return {"id": report_id, "status": "done"}


@inngest_client.create_function(
    fn_id="execute-workflow",
    name="Execute AI Workflow",
    trigger=inngest.TriggerEvent(event="workflow/requested"),
)
async def execute_workflow(ctx: inngest.Context) -> dict[str, Any]:
    wf_id = str(ctx.event.data["id"])
    nodes = ctx.event.data.get("nodes", [])
    edges = ctx.event.data.get("edges", [])
    user_input = ctx.event.data.get("input", "")

    node_map = {str(n["id"]): n for n in nodes}
    has_incoming = {str(e["target"]) for e in edges}
    start_nodes = [n for n in nodes if str(n["id"]) not in has_incoming]

    def get_db():
        return sqlite3.connect("report.db")

    if not start_nodes:
        def err_db():
            with get_db() as conn:
                conn.execute("UPDATE workflows SET status='failed' WHERE id=?", (wf_id,))

        await ctx.step.run("fail-no-start", err_db)
        return {"error": "No start node"}

    current_node_id = str(start_nodes[0]["id"])
    logs = []

    step_count = 0
    while current_node_id and step_count < 20:
        node = node_map.get(current_node_id)
        if not node:
            break

        def update_running_db():
            with get_db() as conn:
                conn.execute(
                    "UPDATE workflows SET status='running', current_node=?, logs=? WHERE id=?",
                    (current_node_id, json.dumps(logs), wf_id)
                )

        await ctx.step.run(f"state-{step_count}", update_running_db)

        prompt = node.get("data", {}).get("prompt", "")

        def run_llm():
            from openai import OpenAI
            import os
            client = OpenAI(
                base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                api_key=os.environ.get("LLM_API_KEY", "dummy"),
                max_retries=0
            )
            if os.getenv("LLM_ENABLED", "true").lower() == "false" or os.getenv("LLM_STUB") == "1":
                return "YES"
            res = client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-3.5-turbo"),
                messages=[
                    {"role": "system", "content": "You are a decision node. Output ONLY the word 'YES' or 'NO'."},
                    {"role": "user", "content": f"Criteria: {prompt}\n\nInput: {user_input}"}
                ],
                temperature=0
            )
            ans = res.choices[0].message.content.strip().upper()
            return "YES" if "YES" in ans else "NO"

        decision = await ctx.step.run(f"llm-{step_count}", run_llm)
        logs.append({"node": current_node_id, "decision": decision})

        next_edges = [e for e in edges if
                      str(e["source"]) == current_node_id and (e.get("sourceHandle") or "").lower() == decision.lower()]
        if next_edges:
            current_node_id = str(next_edges[0]["target"])
        else:
            current_node_id = None

        step_count += 1

    def finish_db():
        with get_db() as conn:
            conn.execute(
                "UPDATE workflows SET status='done', current_node=NULL, logs=? WHERE id=?",
                (json.dumps(logs), wf_id)
            )

    await ctx.step.run("finish", finish_db)
    return {"status": "done", "logs": logs}


functions = [say_hello, make_report, heartbeat, generate_pdf_report, execute_workflow]
