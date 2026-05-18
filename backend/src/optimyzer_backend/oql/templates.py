"""Встроенные OQL-шаблоны (Sprint 1)."""

from __future__ import annotations

TEMPLATES: list[dict[str, str]] = [
    {
        "id": "first_100",
        "label": "Первые 100 событий",
        "description": "Самые ранние события в архиве по времени",
        "category": "basic",
        "query": "events\n| order by ts asc\n| take 100",
    },
    {
        "id": "longest_100",
        "label": "Самые долгие 100 событий",
        "description": "События с максимальным duration_us",
        "category": "basic",
        "query": "events\n| order by duration_us desc\n| take 100",
    },
    {
        "id": "deadlocks_recent",
        "label": "Дедлоки за последние 24 часа",
        "description": "TDEADLOCK события за последние 24 часа",
        "category": "issues",
        "query": "events\n| where event_type == \"TDEADLOCK\"\n| timerange last 24h\n| order by ts desc",
    },
    {
        "id": "slow_sql",
        "label": "Медленные SQL-запросы",
        "description": "DBMSSQL события длительностью больше 1 секунды",
        "category": "queries",
        "query": (
            "events\n"
            "| where event_type == \"DBMSSQL\" and duration_ms > 1000ms\n"
            "| project ts, duration_ms, sql_text_normalized, rows_read\n"
            "| order by duration_ms desc\n"
            "| take 100"
        ),
    },
    {
        "id": "events_by_type",
        "label": "Распределение по типам событий",
        "description": "Сколько событий каждого типа в архиве",
        "category": "stats",
        "query": "events\n| summarize cnt = count(*) by event_type\n| order by cnt desc",
    },
    {
        "id": "events_by_role",
        "label": "Распределение по ролям процессов",
        "description": "rphost / rmngr / ragent / 1cv8c / 1cv8s / 1cv8",
        "category": "stats",
        "query": (
            "events\n"
            "| summarize cnt = count(*) by process_role\n"
            "| order by cnt desc\n"
            "| render bar"
        ),
    },
    {
        "id": "rphost_only",
        "label": "События только rphost",
        "description": "Фильтрация по process_role = rphost",
        "category": "filters",
        "query": (
            "events\n"
            "| where role == \"rphost\"\n"
            "| order by ts desc\n"
            "| take 100"
        ),
    },
    {
        "id": "lock_conflicts",
        "label": "Конфликты блокировок",
        "description": "TLOCK события, отсортированные по длительности",
        "category": "issues",
        "query": (
            "events\n"
            "| where event_type == \"TLOCK\"\n"
            "| order by duration_ms desc\n"
            "| take 100"
        ),
    },
]
