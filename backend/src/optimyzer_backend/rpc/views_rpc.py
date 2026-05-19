"""RPC методы для pre-built investigation views (Sprint 2 Phase D)."""

from __future__ import annotations

from typing import Any

from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.sql.executor import SQLExecutionError
from optimyzer_backend.sql.anatomy import get_operation_anatomy, get_session_anatomy
from optimyzer_backend.sql.deadlock_anatomy import get_deadlock_anatomy, list_deadlocks
from optimyzer_backend.sql.views import (
    ViewFilters,
    activity_heatmap,
    duration_histogram,
    errors_feed,
    locks_timeline,
    process_roles,
    slow_queries,
    top_business_operations,
)


def _filters_from_params(p: dict[str, Any] | None) -> ViewFilters:
    p = p or {}
    return ViewFilters(
        time_from=p.get("time_from"),
        time_to=p.get("time_to"),
        process_role=p.get("process_role"),
        event_type=p.get("event_type"),
    )


def _check_archive_ready(archive_id: str) -> dict[str, Any] | None:
    state = _ARCHIVES.get(archive_id)
    if state is None:
        return {"ok": False, "error": f"Архив не загружен: {archive_id}", "phase": "execute"}
    if state.get("status") != "ready":
        return {
            "ok": False,
            "error": f"Архив ещё не готов (status={state.get('status')})",
            "phase": "execute",
        }
    return None


def _wrap(archive_id: str, runner) -> dict[str, Any]:
    err = _check_archive_ready(archive_id)
    if err:
        return err
    try:
        result = runner()
    except SQLExecutionError as exc:
        return {"ok": False, "error": str(exc), "phase": "execute"}
    return {"ok": True, **result}


@rpc("view_slow_queries")
def view_slow_queries(
    archive_id: str,
    filters: dict[str, Any] | None = None,
    sort_by: str = "total_duration",
    limit: int = 100,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: slow_queries(
            archive_id, _filters_from_params(filters), sort_by=sort_by, limit=limit
        ),
    )


@rpc("view_locks_timeline")
def view_locks_timeline(
    archive_id: str,
    filters: dict[str, Any] | None = None,
    limit: int = 5000,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: locks_timeline(archive_id, _filters_from_params(filters), limit=limit),
    )


@rpc("view_process_roles")
def view_process_roles(
    archive_id: str,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _wrap(
        archive_id, lambda: process_roles(archive_id, _filters_from_params(filters))
    )


@rpc("view_duration_histogram")
def view_duration_histogram(
    archive_id: str,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: duration_histogram(archive_id, _filters_from_params(filters)),
    )


@rpc("view_errors_feed")
def view_errors_feed(
    archive_id: str,
    filters: dict[str, Any] | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: errors_feed(archive_id, _filters_from_params(filters), limit=limit),
    )


@rpc("view_activity_heatmap")
def view_activity_heatmap(
    archive_id: str,
    filters: dict[str, Any] | None = None,
    metric: str = "count",
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: activity_heatmap(archive_id, _filters_from_params(filters), metric=metric),
    )


@rpc("view_top_business_operations")
def view_top_business_operations(
    archive_id: str,
    filters: dict[str, Any] | None = None,
    sort_by: str = "total_duration_ms",
    limit: int = 100,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: top_business_operations(
            archive_id, _filters_from_params(filters), sort_by=sort_by, limit=limit
        ),
    )


@rpc("view_operation_anatomy")
def view_operation_anatomy(
    archive_id: str,
    operation: str,
    timeline_limit: int = 50,
    top_sql_limit: int = 20,
    exception_limit: int = 30,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: get_operation_anatomy(
            archive_id,
            operation,
            timeline_limit=timeline_limit,
            top_sql_limit=top_sql_limit,
            exception_limit=exception_limit,
        ),
    )


@rpc("view_session_anatomy")
def view_session_anatomy(
    archive_id: str,
    session_id: int,
    timeline_limit: int = 200,
    top_sql_limit: int = 20,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: get_session_anatomy(
            archive_id,
            session_id,
            timeline_limit=timeline_limit,
            top_sql_limit=top_sql_limit,
        ),
    )


@rpc("view_list_deadlocks")
def view_list_deadlocks(archive_id: str, limit: int = 200) -> dict[str, Any]:
    return _wrap(archive_id, lambda: list_deadlocks(archive_id, limit=limit))


@rpc("view_deadlock_anatomy")
def view_deadlock_anatomy(
    archive_id: str,
    event_id: int,
    window_seconds: int = 30,
) -> dict[str, Any]:
    return _wrap(
        archive_id,
        lambda: get_deadlock_anatomy(
            archive_id, event_id, window_seconds=window_seconds
        ),
    )
