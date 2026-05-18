"""Schema introspection — список таблиц/колонок для autocomplete и docs panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from optimyzer_backend.storage.duckdb_store import default_db_dir


def get_schema(archive_id: str, db_path: Path | None = None) -> dict[str, list[dict[str, str]]]:
    """Returns {table_name: [{name, type}, ...], ...} для main schema.

    Использует read-only connection. Если БД не существует — возвращает пустой
    словарь (UI должен показать "загрузите архив").
    """
    path = db_path or (default_db_dir() / f"{archive_id}.duckdb")
    if not path.exists():
        return {}

    conn = duckdb.connect(str(path), read_only=True)
    try:
        tables = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()

        result: dict[str, list[dict[str, str]]] = {}
        for (table_name,) in tables:
            columns = conn.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'main' AND table_name = ?
                ORDER BY ordinal_position
                """,
                [table_name],
            ).fetchall()
            result[table_name] = [
                {"name": name, "type": dtype} for name, dtype in columns
            ]
        return result
    finally:
        conn.close()
