"""RPC methods для multi-archive comparison (Sprint 2 Phase G)."""

from __future__ import annotations

from typing import Any

from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.sql.comparison import compare_slow_queries, compare_summary
from optimyzer_backend.sql.executor import SQLExecutionError


def _both_ready(archive_id_a: str, archive_id_b: str) -> dict[str, Any] | None:
    for label, aid in [("baseline", archive_id_a), ("compared", archive_id_b)]:
        state = _ARCHIVES.get(aid)
        if state is None:
            return {"ok": False, "error": f"Архив {label} не загружен: {aid}"}
        if state.get("status") != "ready":
            return {"ok": False, "error": f"Архив {label} ещё не готов (status={state.get('status')})"}
    return None


@rpc("compare_summary")
def compare_summary_rpc(archive_id_a: str, archive_id_b: str) -> dict[str, Any]:
    err = _both_ready(archive_id_a, archive_id_b)
    if err:
        return err
    try:
        return {"ok": True, **compare_summary(archive_id_a, archive_id_b)}
    except SQLExecutionError as exc:
        return {"ok": False, "error": str(exc)}


@rpc("compare_slow_queries")
def compare_slow_queries_rpc(
    archive_id_a: str,
    archive_id_b: str,
    limit: int = 50,
) -> dict[str, Any]:
    err = _both_ready(archive_id_a, archive_id_b)
    if err:
        return err
    try:
        return {
            "ok": True,
            **compare_slow_queries(archive_id_a, archive_id_b, limit=limit),
        }
    except SQLExecutionError as exc:
        return {"ok": False, "error": str(exc)}
