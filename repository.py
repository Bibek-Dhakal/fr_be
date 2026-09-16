import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import psycopg
from psycopg.rows import dict_row


class TaskRepository(Protocol):
    def list_tasks(self) -> list[dict[str, Any]]: ...

    def get_task(self, task_id: int) -> dict[str, Any] | None: ...

    def create_task(self, title: str) -> dict[str, Any]: ...

    def update_task(
        self, task_id: int, title: str, done: bool
    ) -> dict[str, Any] | None: ...

    def delete_task(self, task_id: int) -> bool: ...


class PostgresTaskRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://tasks_user:tasks_password@localhost:5432/tasks_db",
        )

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def initialize(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_path.read_text(encoding="utf-8"))

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, title, done FROM tasks ORDER BY id")
                return list(cursor.fetchall())

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, title, done FROM tasks WHERE id = %s",
                    (task_id,),
                )
                return cursor.fetchone()

    def create_task(self, title: str) -> dict[str, Any]:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO tasks (title, done)
                    VALUES (%s, FALSE)
                    RETURNING id, title, done
                    """,
                    (title,),
                )
                return cursor.fetchone()

    def update_task(
        self, task_id: int, title: str, done: bool
    ) -> dict[str, Any] | None:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET title = %s, done = %s
                    WHERE id = %s
                    RETURNING id, title, done
                    """,
                    (title, done, task_id),
                )
                return cursor.fetchone()

    def delete_task(self, task_id: int) -> bool:
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                return cursor.rowcount > 0
