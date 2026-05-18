"""RPC методы для SQL Engine (Sprint 2 Phase B).

- execute_sql:  parse + validate + execute, returns rows
- validate_sql: только parse + validate (для debounced typing)
- get_schema:   список таблиц и колонок для autocomplete + docs panel
"""

from __future__ import annotations

from typing import Any

from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.sql import (
    SQLExecutionError,
    SQLExecutor,
    get_schema,
    validate_sql,
)


@rpc("execute_sql")
def execute_sql(archive_id: str, sql: str, max_rows: int = 10000) -> dict[str, Any]:
    """Validate → execute → return rows.

    Ошибки validation возвращаются с phase='validate', execution — с phase='execute'.
    Успех — ok=True + columns/rows/row_count/truncated/executed_ms.
    """
    is_valid, error = validate_sql(sql)
    if not is_valid:
        return {"ok": False, "error": error, "phase": "validate"}

    state = _ARCHIVES.get(archive_id)
    if state is None:
        return {
            "ok": False,
            "error": f"Архив не загружен: {archive_id}",
            "phase": "execute",
        }
    if state.get("status") != "ready":
        return {
            "ok": False,
            "error": f"Архив ещё не готов (status={state.get('status')})",
            "phase": "execute",
        }

    try:
        with SQLExecutor(archive_id) as executor:
            result = executor.execute(sql, max_rows=max_rows)
    except SQLExecutionError as exc:
        return {"ok": False, "error": str(exc), "phase": "execute"}

    return {"ok": True, **result}


@rpc("validate_sql")
def validate_sql_rpc(sql: str) -> dict[str, Any]:
    """Static check для debounced typing в editor (без execute)."""
    is_valid, error = validate_sql(sql)
    return {"ok": is_valid, "error": error}


@rpc("get_schema")
def get_schema_rpc(archive_id: str) -> dict[str, list[dict[str, str]]]:
    """Список таблиц + колонок для autocomplete / docs panel."""
    return get_schema(archive_id)
