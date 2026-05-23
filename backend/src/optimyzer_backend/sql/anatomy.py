"""Sprint 3 Phase C — Operation / Session anatomy views.

Anatomy view = drill-down по одной бизнес-операции или одной сессии.
Возвращает structured dict с несколькими «срезами»:
  - header summary (executions count, success rate, avg/max/min)
  - timeline последних N executions / events
  - breakdown по event_type (где время уходит — SQL / locks / exceptions)
  - top SQL queries внутри операции (если есть DBMSSQL events)
  - связанные exceptions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from optimyzer_backend.sql.executor import SQLExecutor

# В 1С Tech Journal EXCPCNTX и Context имеют поле Duration равное длительности
# *родительского контекста* (от начала операции до момента события), а не
# длительности самого события. Если их SUM/AVG/MAX суммировать вместе со
# SCALL/CALL/DBMSSQL/EXCP — получается многократный double-count (для архива
# с 75 EXCPCNTX × 3.7 ч avg на одну операцию это даёт Σ=290 ч при
# wall-clock 5 ч). Эти типы исключаются из агрегатов по длительности; в
# total_events и в breakdown по event_type они остаются (это не баг, а
# реальные события). См. ADR об этом в Sprint-6.
_NON_CUMULATIVE_DURATION_EXPR = (
    "CASE WHEN event_type NOT IN ('EXCPCNTX', 'Context') "
    "THEN COALESCE(duration_us, 0) END"
)


def _execute(archive_id: str, sql: str, params: list[Any], max_rows: int = 10_000) -> dict[str, Any]:
    with SQLExecutor(archive_id) as ex:
        return ex.execute(sql, params=params, max_rows=max_rows)


@dataclass
class OperationAnatomy:
    """Aggregate-friendly DTO для UI."""

    summary: dict[str, Any]
    timeline_columns: list[dict[str, str]]
    timeline_rows: list[list[Any]]
    breakdown: list[dict[str, Any]]
    top_sql_columns: list[dict[str, str]]
    top_sql_rows: list[list[Any]]
    related_exceptions_columns: list[dict[str, str]]
    related_exceptions_rows: list[list[Any]]


def get_operation_anatomy(
    archive_id: str,
    operation: str,
    *,
    timeline_limit: int = 50,
    top_sql_limit: int = 20,
    exception_limit: int = 30,
) -> dict[str, Any]:
    """Анатомия одной бизнес-операции по `context_normalized`.

    operation — нормализованный context (см. Phase A normalize_context).
    """
    # Summary
    summary_sql = f"""
        SELECT
            COUNT(*) AS total_events,
            SUM({_NON_CUMULATIVE_DURATION_EXPR}) / 1000.0 AS total_duration_ms,
            AVG({_NON_CUMULATIVE_DURATION_EXPR}) / 1000.0 AS avg_duration_ms,
            MAX({_NON_CUMULATIVE_DURATION_EXPR}) / 1000.0 AS max_duration_ms,
            MIN(NULLIF({_NON_CUMULATIVE_DURATION_EXPR}, 0)) / 1000.0 AS min_duration_ms,
            COUNT(DISTINCT session_id) AS unique_sessions,
            COUNT(DISTINCT process_pid) AS unique_processes,
            STRING_AGG(DISTINCT process_role, ', ') AS process_roles,
            SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exception_count,
            SUM(CASE WHEN event_type IN ('TLOCK', 'TDEADLOCK') THEN 1 ELSE 0 END) AS lock_count,
            SUM(CASE WHEN event_type = 'DBMSSQL' THEN 1 ELSE 0 END) AS sql_count,
            MIN(ts) AS first_seen,
            MAX(ts) AS last_seen,
            -- wall_clock_ms = реальная разница (last - first) в календарном
            -- времени. Отличается от total_duration_ms тем, что не учитывает
            -- параллельность сессий (это просто диапазон). Полезно как
            -- sanity check для пользователя.
            (EXTRACT(EPOCH FROM MAX(ts)) - EXTRACT(EPOCH FROM MIN(ts))) * 1000.0
                AS wall_clock_ms
        FROM events
        WHERE context_normalized = ?
    """
    summary_result = _execute(archive_id, summary_sql, [operation])
    summary: dict[str, Any] = {"operation": operation, "found": False}
    if summary_result.get("rows"):
        row = summary_result["rows"][0]
        cols = [c["name"] for c in summary_result["columns"]]
        summary = dict(zip(cols, row))
        summary["operation"] = operation
        summary["found"] = (summary.get("total_events") or 0) > 0

    # Timeline — последние N events этой операции (любых типов)
    timeline_sql = """
        SELECT
            id,
            ts,
            event_type,
            session_id,
            process_role,
            process_pid,
            duration_us / 1000.0 AS duration_ms,
            sql_text_normalized,
            context
        FROM events
        WHERE context_normalized = ?
        ORDER BY ts DESC
        LIMIT ?
    """
    timeline = _execute(archive_id, timeline_sql, [operation, timeline_limit])

    # Breakdown — по event_type внутри операции
    breakdown_sql = """
        SELECT
            event_type,
            COUNT(*) AS events,
            SUM(COALESCE(duration_us, 0)) / 1000.0 AS total_duration_ms,
            AVG(COALESCE(duration_us, 0)) / 1000.0 AS avg_duration_ms
        FROM events
        WHERE context_normalized = ?
        GROUP BY event_type
        ORDER BY total_duration_ms DESC NULLS LAST, events DESC
    """
    breakdown_result = _execute(archive_id, breakdown_sql, [operation])
    breakdown: list[dict[str, Any]] = []
    if breakdown_result.get("rows"):
        cols = [c["name"] for c in breakdown_result["columns"]]
        for row in breakdown_result["rows"]:
            breakdown.append(dict(zip(cols, row)))

    # Top SQL inside operation (только если DBMSSQL events были)
    top_sql_sql = """
        SELECT
            sql_text_hash,
            ANY_VALUE(sql_text_normalized) AS query,
            COUNT(*) AS calls,
            SUM(COALESCE(duration_us, 0)) / 1000.0 AS total_duration_ms,
            AVG(COALESCE(duration_us, 0)) / 1000.0 AS avg_duration_ms,
            MAX(COALESCE(duration_us, 0)) / 1000.0 AS max_duration_ms,
            SUM(COALESCE(rows_read, 0)) AS total_rows
        FROM events
        WHERE context_normalized = ?
          AND event_type = 'DBMSSQL'
          AND sql_text_normalized IS NOT NULL
        GROUP BY sql_text_hash
        ORDER BY total_duration_ms DESC NULLS LAST
        LIMIT ?
    """
    top_sql = _execute(archive_id, top_sql_sql, [operation, top_sql_limit])

    # Related exceptions
    exc_sql = """
        SELECT
            ts,
            session_id,
            process_role,
            duration_us / 1000.0 AS duration_ms,
            extra
        FROM events
        WHERE context_normalized = ?
          AND event_type = 'EXCP'
        ORDER BY ts DESC
        LIMIT ?
    """
    exc = _execute(archive_id, exc_sql, [operation, exception_limit])

    return {
        "summary": summary,
        "timeline": {
            "columns": timeline["columns"],
            "rows": timeline["rows"],
            "row_count": timeline["row_count"],
        },
        "breakdown": breakdown,
        "top_sql": {
            "columns": top_sql["columns"],
            "rows": top_sql["rows"],
            "row_count": top_sql["row_count"],
        },
        "related_exceptions": {
            "columns": exc["columns"],
            "rows": exc["rows"],
            "row_count": exc["row_count"],
        },
    }


def get_session_anatomy(
    archive_id: str,
    session_id: int,
    *,
    timeline_limit: int = 200,
    top_sql_limit: int = 20,
) -> dict[str, Any]:
    """Анатомия одной сессии — все её events в порядке + breakdown."""
    # Header summary
    summary_sql = f"""
        SELECT
            COUNT(*) AS total_events,
            STRING_AGG(DISTINCT user_name, ', ') AS users,
            STRING_AGG(DISTINCT process_role, ', ') AS process_roles,
            STRING_AGG(DISTINCT CAST(process_pid AS VARCHAR), ', ') AS process_pids,
            COUNT(DISTINCT context_normalized) AS distinct_operations,
            SUM({_NON_CUMULATIVE_DURATION_EXPR}) / 1000.0 AS total_duration_ms,
            SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exception_count,
            SUM(CASE WHEN event_type IN ('TLOCK', 'TDEADLOCK') THEN 1 ELSE 0 END) AS lock_count,
            SUM(CASE WHEN event_type = 'DBMSSQL' THEN 1 ELSE 0 END) AS sql_count,
            MIN(ts) AS first_seen,
            MAX(ts) AS last_seen,
            (EXTRACT(EPOCH FROM MAX(ts)) - EXTRACT(EPOCH FROM MIN(ts))) * 1000.0
                AS wall_clock_ms
        FROM events
        WHERE session_id = ?
    """
    summary_result = _execute(archive_id, summary_sql, [session_id])
    summary: dict[str, Any] = {"session_id": session_id, "found": False}
    if summary_result.get("rows"):
        row = summary_result["rows"][0]
        cols = [c["name"] for c in summary_result["columns"]]
        summary = dict(zip(cols, row))
        summary["session_id"] = session_id
        summary["found"] = (summary.get("total_events") or 0) > 0

    # Timeline
    timeline_sql = """
        SELECT
            id,
            ts,
            event_type,
            duration_us / 1000.0 AS duration_ms,
            context_normalized,
            sql_text_normalized
        FROM events
        WHERE session_id = ?
        ORDER BY ts
        LIMIT ?
    """
    timeline = _execute(archive_id, timeline_sql, [session_id, timeline_limit])

    # Breakdown by event_type
    breakdown_sql = """
        SELECT
            event_type,
            COUNT(*) AS events,
            SUM(COALESCE(duration_us, 0)) / 1000.0 AS total_duration_ms
        FROM events
        WHERE session_id = ?
        GROUP BY event_type
        ORDER BY total_duration_ms DESC NULLS LAST, events DESC
    """
    breakdown_result = _execute(archive_id, breakdown_sql, [session_id])
    breakdown: list[dict[str, Any]] = []
    if breakdown_result.get("rows"):
        cols = [c["name"] for c in breakdown_result["columns"]]
        for row in breakdown_result["rows"]:
            breakdown.append(dict(zip(cols, row)))

    # Top SQL within session
    top_sql_sql = """
        SELECT
            sql_text_hash,
            ANY_VALUE(sql_text_normalized) AS query,
            COUNT(*) AS calls,
            SUM(COALESCE(duration_us, 0)) / 1000.0 AS total_duration_ms,
            MAX(COALESCE(duration_us, 0)) / 1000.0 AS max_duration_ms
        FROM events
        WHERE session_id = ?
          AND event_type = 'DBMSSQL'
          AND sql_text_normalized IS NOT NULL
        GROUP BY sql_text_hash
        ORDER BY total_duration_ms DESC NULLS LAST
        LIMIT ?
    """
    top_sql = _execute(archive_id, top_sql_sql, [session_id, top_sql_limit])

    return {
        "summary": summary,
        "timeline": {
            "columns": timeline["columns"],
            "rows": timeline["rows"],
            "row_count": timeline["row_count"],
        },
        "breakdown": breakdown,
        "top_sql": {
            "columns": top_sql["columns"],
            "rows": top_sql["rows"],
            "row_count": top_sql["row_count"],
        },
    }
