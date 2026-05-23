"""Pre-built investigation views (Sprint 2 Phase D, ADR-016).

Каждая view — отдельная функция, принимает archive_id + optional filters
(time_range, process_role, event_type) и возвращает structured dict. Под
капотом — read-only SQLExecutor → DuckDB. Это базовый строительный блок для
шести экранов в UI (SlowQueries, LocksTimeline, ProcessRoles,
DurationHistogram, ErrorsFeed, ActivityHeatmap) и для cross-filtering из
Phase E.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from optimyzer_backend.sql.executor import SQLExecutionError, SQLExecutor


@dataclass(frozen=True)
class ViewFilters:
    """Общие cross-filter параметры. None = filter не применяется."""

    time_from: str | None = None  # ISO timestamp
    time_to: str | None = None
    process_role: str | None = None
    event_type: str | None = None

    def where_clause(self, extra: list[str] | None = None) -> tuple[str, list[Any]]:
        """Возвращает (WHERE ..., params). Без leading WHERE, чтобы caller
        мог комбинировать со своими условиями.
        """
        conditions: list[str] = list(extra or [])
        params: list[Any] = []
        if self.time_from:
            conditions.append("ts >= ?")
            params.append(self.time_from)
        if self.time_to:
            conditions.append("ts <= ?")
            params.append(self.time_to)
        if self.process_role:
            conditions.append("process_role = ?")
            params.append(self.process_role)
        if self.event_type:
            conditions.append("event_type = ?")
            params.append(self.event_type)
        if not conditions:
            return "", []
        return " AND ".join(conditions), params


def _execute(archive_id: str, sql: str, params: list[Any], max_rows: int = 10_000) -> dict[str, Any]:
    with SQLExecutor(archive_id) as ex:
        return ex.execute(sql, params=params, max_rows=max_rows)


def _count(archive_id: str, sql: str, params: list[Any]) -> int | None:
    """Запрос COUNT(*). Возвращает int или None при ошибке.

    Используется чтобы выдать UI total_rows вместе с limited result —
    "Показано 500 из N". Дополнительный round-trip в DuckDB, но COUNT по
    индексированной колонке быстрый (миллисекунды на наших объёмах).

    SQLExecutor.execute() не возвращает поле "ok" — это добавляется RPC-слоем.
    Поэтому ловим SQLExecutionError здесь и не падаем.
    """
    try:
        result = _execute(archive_id, sql, params, max_rows=1)
    except SQLExecutionError:
        return None
    rows = result.get("rows") or []
    if not rows or not rows[0]:
        return 0
    val = rows[0][0]
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return None


# ---------- D1. Slow Queries ----------


def slow_queries(
    archive_id: str,
    filters: ViewFilters,
    *,
    sort_by: str = "total_duration",
    limit: int = 100,
) -> dict[str, Any]:
    """Топ медленных SQL запросов, агрегированных по sql_text_hash."""
    where, params = filters.where_clause(
        [
            "event_type = 'DBMSSQL'",
            "sql_text_normalized IS NOT NULL",
        ]
    )

    sort_column = {
        "total_duration": "total_duration_ms",
        "avg_duration": "avg_duration_ms",
        "max_duration": "max_duration_ms",
        "count": "calls",
    }.get(sort_by, "total_duration_ms")

    sql = f"""
        SELECT
            sql_text_hash,
            ANY_VALUE(sql_text_normalized) AS query,
            COUNT(*) AS calls,
            SUM(duration_us) / 1000.0 AS total_duration_ms,
            AVG(duration_us) / 1000.0 AS avg_duration_ms,
            MAX(duration_us) / 1000.0 AS max_duration_ms,
            SUM(COALESCE(rows_read, 0)) AS total_rows_read,
            MIN(ts) AS first_seen,
            MAX(ts) AS last_seen,
            STRING_AGG(DISTINCT process_role, ', ') AS process_roles
        FROM events
        {f"WHERE {where}" if where else ""}
        GROUP BY sql_text_hash
        ORDER BY {sort_column} DESC NULLS LAST
        LIMIT ?
    """
    result = _execute(archive_id, sql, params + [limit])
    count_sql = f"""
        SELECT COUNT(DISTINCT sql_text_hash) FROM events
        {f"WHERE {where}" if where else ""}
    """
    result["total_rows"] = _count(archive_id, count_sql, params)
    return result


# ---------- D2. Locks Timeline ----------


def _time_bucket_expr(filters: ViewFilters) -> tuple[str, str]:
    """Выбираем bucket (minute / hour / day) по диапазону времени.

    Эвристика: <2 часов = minute, <2 дней = hour, иначе day.
    Возвращает (sql_expr, label).
    """
    # Без точного знания диапазона делаем consistent выбор на основе фильтров.
    if filters.time_from and filters.time_to:
        # Грубо: если диапазон <2 часов — minute, <2 дней — hour, иначе day.
        # Используем простой парсинг ISO; при ошибке fall-back на hour.
        try:
            from datetime import datetime

            t_from = datetime.fromisoformat(filters.time_from.replace("Z", "+00:00"))
            t_to = datetime.fromisoformat(filters.time_to.replace("Z", "+00:00"))
            delta = (t_to - t_from).total_seconds()
            if delta < 2 * 3600:
                return "date_trunc('minute', ts)", "minute"
            if delta < 2 * 86400:
                return "date_trunc('hour', ts)", "hour"
            return "date_trunc('day', ts)", "day"
        except ValueError:
            return "date_trunc('hour', ts)", "hour"
    return "date_trunc('hour', ts)", "hour"


def locks_timeline(
    archive_id: str,
    filters: ViewFilters,
    *,
    limit: int = 5_000,
) -> dict[str, Any]:
    """Распределение TLOCK / TDEADLOCK по time buckets."""
    bucket_expr, bucket_label = _time_bucket_expr(filters)
    where, params = filters.where_clause(["event_type IN ('TLOCK', 'TDEADLOCK')"])
    sql = f"""
        SELECT
            {bucket_expr} AS bucket,
            SUM(CASE WHEN event_type = 'TLOCK' THEN 1 ELSE 0 END) AS locks,
            SUM(CASE WHEN event_type = 'TDEADLOCK' THEN 1 ELSE 0 END) AS deadlocks
        FROM events
        {f"WHERE {where}" if where else ""}
        GROUP BY bucket
        ORDER BY bucket
        LIMIT ?
    """
    result = _execute(archive_id, sql, params + [limit])
    result["bucket"] = bucket_label
    return result


# ---------- D3. Process Roles ----------


def process_roles(archive_id: str, filters: ViewFilters) -> dict[str, Any]:
    where, params = filters.where_clause(["process_role IS NOT NULL"])
    sql = f"""
        SELECT
            process_role,
            COUNT(*) AS events_count,
            SUM(COALESCE(duration_us, 0)) / 1000.0 AS total_duration_ms,
            COUNT(DISTINCT process_pid) AS unique_processes,
            AVG(COALESCE(duration_us, 0)) / 1000.0 AS avg_duration_ms
        FROM events
        {f"WHERE {where}" if where else ""}
        GROUP BY process_role
        ORDER BY events_count DESC
    """
    return _execute(archive_id, sql, params)


# ---------- D4. Duration Histogram ----------


_DURATION_BUCKETS_US: list[tuple[str, int | None]] = [
    ("< 1 мс", 1_000),
    ("1-10 мс", 10_000),
    ("10-100 мс", 100_000),
    ("100 мс - 1 с", 1_000_000),
    ("1-10 с", 10_000_000),
    ("10-60 с", 60_000_000),
    ("> 60 с", None),
]


def duration_histogram(archive_id: str, filters: ViewFilters) -> dict[str, Any]:
    """Bucketed distribution of durations. Использует CASE expression."""
    where, params = filters.where_clause(["duration_us IS NOT NULL"])

    case_parts: list[str] = []
    prev = 0
    for i, (label, upper) in enumerate(_DURATION_BUCKETS_US):
        if upper is None:
            case_parts.append(f"WHEN duration_us >= {prev} THEN '{label}'")
        else:
            case_parts.append(f"WHEN duration_us >= {prev} AND duration_us < {upper} THEN '{label}'")
            prev = upper
    case_expr = "CASE " + " ".join(case_parts) + " END"

    sql = f"""
        SELECT
            bucket AS label,
            COUNT(*) AS count
        FROM (
            SELECT {case_expr} AS bucket
            FROM events
            {f"WHERE {where}" if where else ""}
        )
        GROUP BY bucket
    """
    raw = _execute(archive_id, sql, params)

    # Преобразуем в фиксированный порядок bucket'ов (для стабильного chart).
    order = {label: i for i, (label, _) in enumerate(_DURATION_BUCKETS_US)}
    rows_by_label = {row[0]: row[1] for row in raw["rows"]}
    ordered_rows: list[list[Any]] = []
    total = sum(rows_by_label.values()) or 1
    for label, _ in _DURATION_BUCKETS_US:
        count = int(rows_by_label.get(label, 0))
        ordered_rows.append([label, count, round(count * 100.0 / total, 2)])
    return {
        "columns": [
            {"name": "label", "type": "VARCHAR"},
            {"name": "count", "type": "BIGINT"},
            {"name": "percent", "type": "DOUBLE"},
        ],
        "rows": ordered_rows,
        "row_count": len(ordered_rows),
        "truncated": False,
        "executed_ms": raw.get("executed_ms", 0.0),
    }


# ---------- D5. Errors Feed ----------


def errors_feed(
    archive_id: str,
    filters: ViewFilters,
    *,
    limit: int = 500,
    event_types: list[str] | None = None,
    context_presence: str | None = None,
) -> dict[str, Any]:
    """Лента всех событий ТЖ, последние сначала.

    `event_types` — multi-select фильтр по типам событий, применяется на
    server-side. Это критично: при LIMIT=10000 редкий тип (например, 1 TLOCK
    в архиве из 100K событий) может полностью выпасть из top-N по `ts DESC`,
    если он расположен в начале архива по времени. Server-side фильтр
    гарантирует, что 1-я TLOCK строка попадёт в результат.

    `context_presence` — фильтр по наличию контекста: "with" (только с
    непустым context), "without" (только без context), None/"any" (без
    фильтра). Тоже server-side по той же причине: при limit=500 первые
    500 событий могут быть SCALL/CALL без контекста (служебные), а
    DBMSSQL с контекстом идут позже по ts DESC — без server-side фильтра
    «есть» вернёт пусто.

    Возвращаемое поле `event_types` (counts по архиву) считается БЕЗ применения
    `event_types`-фильтра — чтобы UI мог переключать выбор без потери видимых
    counts остальных типов.
    """
    base_where, base_params = filters.where_clause()
    rows_where = base_where
    rows_params = list(base_params)
    if event_types:
        placeholders = ",".join("?" for _ in event_types)
        clause = f"event_type IN ({placeholders})"
        rows_where = f"{base_where} AND {clause}" if base_where else clause
        rows_params.extend(event_types)
    if context_presence == "with":
        # TRIM(context) — чтобы строки " " или "\n" не засчитывались как
        # «есть». Frontend ContextFilter использует ту же семантику.
        clause = "context IS NOT NULL AND TRIM(context) <> ''"
        rows_where = f"{rows_where} AND {clause}" if rows_where else clause
    elif context_presence == "without":
        # OR ниже по приоритету чем AND — скобки обязательны если выше
        # уже есть AND-условия (event_type IN (...)).
        clause = "(context IS NULL OR TRIM(context) = '')"
        rows_where = f"{rows_where} AND {clause}" if rows_where else clause

    sql = f"""
        SELECT
            ts,
            event_type,
            process_role,
            process_pid,
            context,
            duration_us / 1000.0 AS duration_ms,
            extra,
            source_file,
            source_line_start
        FROM events
        {f"WHERE {rows_where}" if rows_where else ""}
        ORDER BY ts DESC
        LIMIT ?
    """
    result = _execute(archive_id, sql, rows_params + [limit])
    count_sql = f"""
        SELECT COUNT(*) FROM events
        {f"WHERE {rows_where}" if rows_where else ""}
    """
    result["total_rows"] = _count(archive_id, count_sql, rows_params)

    types_sql = f"""
        SELECT event_type, COUNT(*) AS n FROM events
        {f"WHERE {base_where}" if base_where else ""}
        GROUP BY event_type
        ORDER BY n DESC
    """
    try:
        types_raw = _execute(archive_id, types_sql, base_params, max_rows=200)
        result["event_types"] = [
            [str(row[0]) if row[0] is not None else "", int(row[1] or 0)]
            for row in (types_raw.get("rows") or [])
            if row[0] is not None
        ]
    except SQLExecutionError:
        result["event_types"] = []
    return result


# ---------- Sprint 3 / Phase B — Top Business Operations ----------


def top_business_operations(
    archive_id: str,
    filters: ViewFilters,
    *,
    sort_by: str = "total_duration_ms",
    limit: int = 100,
) -> dict[str, Any]:
    """Аггрегация событий по `context_normalized` (Phase A normalization).

    Возвращает топ бизнес-операций (то, что пишет 1С в Context: документ,
    отчёт, обработка) с breakdown:
        - calls — сколько раз операция вызвана
        - total_duration_ms / avg / max — distribution time
        - sql_duration_ms — сколько времени операция провела в DBMSSQL events
          (если в архиве были DBMSSQL events с этим context)
        - lock_events / exception_events — для drill-down индикаторов
        - unique_sessions / process_roles — для понимания scope
    """
    where, params = filters.where_clause(
        ["context_normalized IS NOT NULL", "context_normalized <> ''"]
    )

    sort_column = {
        "total_duration_ms": "total_duration_ms",
        "avg_duration_ms": "avg_duration_ms",
        "max_duration_ms": "max_duration_ms",
        "calls": "calls",
        "sql_duration_ms": "sql_duration_ms",
        "lock_events": "lock_events",
        "exception_events": "exception_events",
    }.get(sort_by, "total_duration_ms")

    sql = f"""
        SELECT
            context_normalized AS operation,
            COUNT(*) AS calls,
            SUM(COALESCE(duration_us, 0)) / 1000.0 AS total_duration_ms,
            AVG(COALESCE(duration_us, 0)) / 1000.0 AS avg_duration_ms,
            MAX(COALESCE(duration_us, 0)) / 1000.0 AS max_duration_ms,
            SUM(CASE WHEN event_type = 'DBMSSQL' THEN COALESCE(duration_us, 0) ELSE 0 END) / 1000.0 AS sql_duration_ms,
            SUM(CASE WHEN event_type IN ('TLOCK', 'TDEADLOCK') THEN 1 ELSE 0 END) AS lock_events,
            SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exception_events,
            COUNT(DISTINCT session_id) AS unique_sessions,
            STRING_AGG(DISTINCT process_role, ', ') AS process_roles,
            MIN(ts) AS first_seen,
            MAX(ts) AS last_seen
        FROM events
        {f"WHERE {where}" if where else ""}
        GROUP BY context_normalized
        ORDER BY {sort_column} DESC NULLS LAST
        LIMIT ?
    """
    result = _execute(archive_id, sql, params + [limit])
    count_sql = f"""
        SELECT COUNT(DISTINCT context_normalized) FROM events
        {f"WHERE {where}" if where else ""}
    """
    result["total_rows"] = _count(archive_id, count_sql, params)
    return result


# ---------- D6. Activity Heatmap ----------


def activity_heatmap(
    archive_id: str,
    filters: ViewFilters,
    *,
    metric: str = "count",
) -> dict[str, Any]:
    """7x24 grid: day_of_week × hour_of_day → metric."""
    where, params = filters.where_clause()

    metric_expr = {
        "count": "COUNT(*)",
        "total_duration_ms": "SUM(COALESCE(duration_us, 0)) / 1000.0",
        "peak_duration_ms": "MAX(COALESCE(duration_us, 0)) / 1000.0",
        "error_count": "SUM(CASE WHEN event_type IN ('EXCP', 'TDEADLOCK') THEN 1 ELSE 0 END)",
    }.get(metric, "COUNT(*)")

    # DuckDB extract(dow FROM ts) — 0=Sunday..6=Saturday по умолчанию.
    # Перенумеруем в Monday=0 для UI labels.
    sql = f"""
        SELECT
            CAST(((CAST(extract(dow FROM ts) AS INT) + 6) % 7) AS INT) AS y,
            CAST(extract(hour FROM ts) AS INT) AS x,
            {metric_expr} AS value
        FROM events
        {f"WHERE {where}" if where else ""}
        GROUP BY y, x
        ORDER BY y, x
    """
    return _execute(archive_id, sql, params)
