"""Pre-built SQL templates (Sprint 2 Phase F).

Каждый template — это готовый SELECT-запрос против events table, который
1С-эксперт может вызвать через UI dropdown в SQL Console. Категории
сгруппированы по типичным investigation сценариям:
performance / locks / errors / memory / stats.
"""

from __future__ import annotations

from typing import Any

TEMPLATES: list[dict[str, Any]] = [
    # ---------- Performance ----------
    {
        "id": "top_slow_sql",
        "category": "performance",
        "label": "Топ 100 медленных SQL запросов",
        "description": "DBMSSQL events сгруппированы по sql_text_hash, query = exemplar самого медленного вызова с реальными значениями.",
        "sql": """SELECT
    ARG_MAX(COALESCE(sql_text, sql_text_normalized), duration_us) AS query,
    COUNT(*) AS calls,
    SUM(duration_us) / 1000.0 AS total_ms,
    AVG(duration_us) / 1000.0 AS avg_ms,
    MAX(duration_us) / 1000.0 AS max_ms
FROM events
WHERE event_type = 'DBMSSQL'
  AND sql_text_hash IS NOT NULL
GROUP BY sql_text_hash
ORDER BY total_ms DESC NULLS LAST
LIMIT 100;""",
    },
    {
        "id": "long_server_calls",
        "category": "performance",
        "label": "Длинные server calls (> 10 секунд)",
        "description": "CALL и SCALL события с duration > 10s — потенциальные blocking operations.",
        "sql": """SELECT
    ts,
    process_role,
    context,
    duration_us / 1000.0 AS duration_ms
FROM events
WHERE event_type IN ('CALL', 'SCALL')
  AND duration_us > 10000000
ORDER BY duration_us DESC
LIMIT 100;""",
    },
    {
        "id": "top_contexts_slow",
        "category": "performance",
        "label": "Самые медленные 1С-контексты",
        "description": "Группировка по context (модули/процедуры 1С).",
        "sql": """SELECT
    context,
    COUNT(*) AS calls,
    SUM(duration_us) / 1000.0 AS total_ms,
    AVG(duration_us) / 1000.0 AS avg_ms
FROM events
WHERE context IS NOT NULL
GROUP BY context
ORDER BY total_ms DESC NULLS LAST
LIMIT 50;""",
    },
    # ---------- Locks ----------
    {
        "id": "deadlocks_by_hour",
        "category": "locks",
        "label": "Дедлоки по часам",
        "description": "Распределение TDEADLOCK по часовым бакетам.",
        "sql": """SELECT
    date_trunc('hour', ts) AS hour,
    COUNT(*) AS deadlocks
FROM events
WHERE event_type = 'TDEADLOCK'
GROUP BY hour
ORDER BY hour;""",
    },
    {
        "id": "locks_top_resources",
        "category": "locks",
        "label": "Топ заблокированных ресурсов",
        "description": "TLOCK events с разбивкой по Regions из extra JSON.",
        "sql": """SELECT
    json_extract(extra, '$.Regions') AS resource,
    COUNT(*) AS lock_events
FROM events
WHERE event_type = 'TLOCK'
GROUP BY resource
ORDER BY lock_events DESC NULLS LAST
LIMIT 50;""",
    },
    {
        "id": "lock_wait_sessions",
        "category": "locks",
        "label": "Сеансы, ждавшие блокировки",
        "description": "TLOCK events с WaitConnections.",
        "sql": """SELECT
    ts,
    session_id,
    user_name,
    json_extract(extra, '$.WaitConnections') AS wait_for
FROM events
WHERE event_type = 'TLOCK'
  AND json_extract(extra, '$.WaitConnections') IS NOT NULL
ORDER BY ts DESC
LIMIT 100;""",
    },
    # ---------- Errors ----------
    {
        "id": "exceptions_feed",
        "category": "errors",
        "label": "Поток исключений (EXCP)",
        "description": "Последние 200 EXCP events с Exception и Descr полями.",
        "sql": """SELECT
    ts,
    process_role,
    context,
    json_extract(extra, '$.Exception') AS exception,
    json_extract(extra, '$.Descr') AS description
FROM events
WHERE event_type = 'EXCP'
ORDER BY ts DESC
LIMIT 200;""",
    },
    {
        "id": "errors_by_type",
        "category": "errors",
        "label": "Ошибки по типам Exception",
        "description": "Группировка EXCP по json_extract(extra, '$.Exception').",
        "sql": """SELECT
    json_extract(extra, '$.Exception') AS exception_type,
    COUNT(*) AS cnt
FROM events
WHERE event_type = 'EXCP'
GROUP BY exception_type
ORDER BY cnt DESC NULLS LAST
LIMIT 50;""",
    },
    # ---------- Memory ----------
    {
        "id": "memory_heavy_events",
        "category": "memory",
        "label": "Тяжёлые события по памяти",
        "description": "События с MemoryPeak из extra JSON, отсортированные по убыванию.",
        "sql": """SELECT
    ts,
    event_type,
    process_role,
    context,
    json_extract(extra, '$.Memory') AS memory,
    json_extract(extra, '$.MemoryPeak') AS memory_peak
FROM events
WHERE json_extract(extra, '$.MemoryPeak') IS NOT NULL
ORDER BY CAST(json_extract(extra, '$.MemoryPeak') AS BIGINT) DESC NULLS LAST
LIMIT 100;""",
    },
    # ---------- Stats ----------
    {
        "id": "events_by_role_and_type",
        "category": "stats",
        "label": "Распределение событий по ролям и типам",
        "description": "Cross-tab process_role × event_type.",
        "sql": """SELECT
    process_role,
    event_type,
    COUNT(*) AS cnt
FROM events
GROUP BY process_role, event_type
ORDER BY process_role, cnt DESC;""",
    },
    {
        "id": "activity_by_hour",
        "category": "stats",
        "label": "Активность по часам суток",
        "description": "Group by EXTRACT(hour FROM ts) — 24 строки.",
        "sql": """SELECT
    EXTRACT(hour FROM ts) AS hour_of_day,
    COUNT(*) AS events,
    SUM(duration_us) / 1000.0 AS total_ms,
    SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exceptions
FROM events
GROUP BY hour_of_day
ORDER BY hour_of_day;""",
    },
    {
        "id": "sessions_overview",
        "category": "stats",
        "label": "Обзор сеансов пользователей",
        "description": "Per-session aggregation с min/max ts и uniq contexts.",
        "sql": """SELECT
    session_id,
    user_name,
    COUNT(*) AS events,
    SUM(duration_us) / 1000.0 AS total_ms,
    MIN(ts) AS first_event,
    MAX(ts) AS last_event,
    COUNT(DISTINCT context) AS unique_contexts
FROM events
WHERE session_id IS NOT NULL
GROUP BY session_id, user_name
ORDER BY total_ms DESC NULLS LAST
LIMIT 100;""",
    },
    {
        "id": "events_count_overview",
        "category": "stats",
        "label": "Сводка количества событий",
        "description": "Total events + breakdown by top event_types.",
        "sql": """SELECT
    event_type,
    COUNT(*) AS cnt,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percent
FROM events
GROUP BY event_type
ORDER BY cnt DESC;""",
    },
]
