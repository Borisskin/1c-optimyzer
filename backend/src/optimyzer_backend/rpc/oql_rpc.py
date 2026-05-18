"""RPC методы execute_oql_query / validate_oql_query (Sprint 1)."""

from __future__ import annotations

import time
from typing import Any

from optimyzer_backend.oql import (
    OQLCompileError,
    OQLParseError,
    SQLCompiler,
    parse_oql,
    validate,
)
from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.storage.duckdb_store import DuckDBStore


@rpc("execute_oql_query")
def execute_oql_query(archive_id: str, query: str) -> dict[str, Any]:
    """Parse → validate → compile → execute. Возвращает rows + metadata."""
    try:
        ast = parse_oql(query)
    except OQLParseError as e:
        return {"ok": False, "error": str(e), "phase": "parse"}

    errors = validate(ast, active_archive_id=archive_id)
    if errors:
        return {"ok": False, "error": "; ".join(errors), "phase": "validate"}

    try:
        compiler = SQLCompiler(active_archive_id=archive_id)
        sql, params = compiler.compile(ast)
    except OQLCompileError as e:
        return {"ok": False, "error": str(e), "phase": "compile"}

    state = _ARCHIVES.get(archive_id)
    if state is None:
        return {"ok": False, "error": f"Архив не загружен: {archive_id}", "phase": "execute"}
    if state.get("status") != "ready":
        return {
            "ok": False,
            "error": f"Архив ещё не готов (status={state.get('status')})",
            "phase": "execute",
        }

    store: DuckDBStore = state["store"]
    started = time.monotonic()
    try:
        cur = store.open().execute(sql, params)
        rows = cur.fetchall()
        columns = [(d[0], str(d[1])) for d in cur.description]
    except Exception as e:
        return {"ok": False, "error": f"Ошибка выполнения: {e}", "phase": "execute"}

    elapsed_ms = (time.monotonic() - started) * 1000

    serialized_rows: list[list[Any]] = []
    for r in rows:
        serialized_rows.append([_serialize_cell(v) for v in r])

    return {
        "ok": True,
        "columns": [{"name": n, "type": t} for n, t in columns],
        "rows": serialized_rows,
        "row_count": len(serialized_rows),
        "executed_ms": round(elapsed_ms, 1),
        "render": compiler.render_hint(),
        "sql_compiled": sql,
    }


@rpc("validate_oql_query")
def validate_oql_query(query: str, archive_id: str | None = None) -> dict[str, Any]:
    """Static check для debounced typing в editor (без выполнения)."""
    try:
        ast = parse_oql(query)
    except OQLParseError as e:
        err: dict[str, Any] = {"message": str(e), "phase": "parse"}
        if e.line is not None:
            err["line"] = e.line
        if e.column is not None:
            err["column"] = e.column
        return {"ok": False, "errors": [err]}

    errors = validate(ast, active_archive_id=archive_id)
    if errors:
        return {
            "ok": False,
            "errors": [{"message": m, "phase": "validate"} for m in errors],
        }
    return {"ok": True}


def _serialize_cell(v: Any) -> Any:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (str, int, float, bool, list, dict)):
        return v
    return str(v)
