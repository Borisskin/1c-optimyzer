"""SQL Executor (ADR-019, Phase B).

Открывает read-only DuckDB connection per query, выполняет SELECT, возвращает
результат с column metadata. Внутри — timeout + row limit; truncation честно
сообщается клиенту через ``truncated=True``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import duckdb

from optimyzer_backend.storage.duckdb_store import default_db_dir


class SQLExecutionError(RuntimeError):
    """Ошибка выполнения SQL (timeout, syntax error от DuckDB, etc.)."""


class SQLExecutor:
    """One-shot executor: открывает read-only connection, выполняет, закрывает.

    Stateless относительно archive — повторное использование с разным
    ``archive_id`` создаст новый connection.
    """

    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_MAX_ROWS = 10_000

    def __init__(
        self,
        archive_id: str,
        db_path: Path | None = None,
        read_only: bool = True,
    ) -> None:
        self.archive_id = archive_id
        self.db_path = db_path or (default_db_dir() / f"{archive_id}.duckdb")
        self.read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            if not self.db_path.exists():
                raise SQLExecutionError(
                    f"База архива не найдена: {self.db_path.name}. Архив был удалён?"
                )
            try:
                self._conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
            except duckdb.Error as exc:
                raise SQLExecutionError(f"Не удалось открыть БД: {exc}") from exc
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SQLExecutor":
        self._connect()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def execute(
        self,
        sql: str,
        params: list[Any] | None = None,
        timeout_s: int | None = None,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        """Run query, return serialized result.

        Returns: {columns: [{name,type}...], rows: [[...]], row_count, truncated,
                  executed_ms}
        """
        timeout_s = timeout_s or self.DEFAULT_TIMEOUT_SECONDS
        max_rows = max_rows or self.DEFAULT_MAX_ROWS
        params = params or []

        conn = self._connect()

        # DuckDB поддерживает per-query timeout через `statement_timeout` setting.
        # На некоторых версиях DuckDB этот pragma может отсутствовать — игнорим.
        try:
            conn.execute(f"SET statement_timeout = '{int(timeout_s * 1000)}ms'")
        except duckdb.Error:
            pass

        started = time.monotonic()
        try:
            cur = conn.execute(sql, params)
        except duckdb.Error as exc:
            raise SQLExecutionError(f"Ошибка выполнения SQL: {exc}") from exc

        # fetchmany(max_rows + 1) чтобы детектить truncation.
        try:
            rows = cur.fetchmany(max_rows + 1)
        except duckdb.Error as exc:
            raise SQLExecutionError(f"Ошибка чтения результата: {exc}") from exc

        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]

        columns = [(d[0], str(d[1])) for d in (cur.description or [])]
        serialized_rows = [[_serialize_cell(v) for v in row] for row in rows]

        elapsed_ms = (time.monotonic() - started) * 1000.0

        return {
            "columns": [{"name": n, "type": t} for n, t in columns],
            "rows": serialized_rows,
            "row_count": len(serialized_rows),
            "truncated": truncated,
            "executed_ms": round(elapsed_ms, 1),
        }


def _serialize_cell(v: Any) -> Any:
    """JSON-safe cell representation."""
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (str, int, float, bool, list, dict)):
        return v
    return str(v)
