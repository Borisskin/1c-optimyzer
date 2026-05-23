"""Multi-archive comparison (Sprint 2 Phase G, ADR-018).

Сравнивает два архива по высокоуровневым метрикам (compare_summary) и по
агрегатам топ-медленных запросов (compare_slow_queries). Backend держит две
независимые SQLExecutor connections в read-only mode — никакого
cross-database JOIN, просто два сравнительных запроса и diff на Python-уровне.
"""

from __future__ import annotations

from typing import Any

from optimyzer_backend.sql.executor import SQLExecutor


def _summary_one(executor: SQLExecutor) -> dict[str, float]:
    """Вычисляем компактный набор метрик для одного архива."""
    sql = """
        SELECT
            COUNT(*) AS events_count,
            COALESCE(SUM(duration_us), 0) / 1000.0 AS total_duration_ms,
            COALESCE(AVG(duration_us), 0) / 1000.0 AS avg_duration_ms,
            SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exceptions,
            SUM(CASE WHEN event_type = 'TDEADLOCK' THEN 1 ELSE 0 END) AS deadlocks,
            SUM(CASE WHEN event_type = 'TLOCK' THEN 1 ELSE 0 END) AS locks
        FROM events
    """
    result = executor.execute(sql)
    row = result["rows"][0] if result["rows"] else [0, 0.0, 0.0, 0, 0, 0]
    cols = [c["name"] for c in result["columns"]]
    return {cols[i]: row[i] for i in range(len(cols))}


def _delta_percent(a: float, b: float) -> float | None:
    if a == 0:
        return None
    return round((b - a) * 100.0 / a, 2)


def compare_summary(archive_id_a: str, archive_id_b: str) -> dict[str, Any]:
    """High-level diff between two archives (events, total duration, errors, ...)."""
    with SQLExecutor(archive_id_a) as ex_a:
        sa = _summary_one(ex_a)
    with SQLExecutor(archive_id_b) as ex_b:
        sb = _summary_one(ex_b)

    metrics: list[dict[str, Any]] = []
    for key, label in [
        ("events_count", "События"),
        ("total_duration_ms", "Σ длительность, мс"),
        ("avg_duration_ms", "Средняя длительность, мс"),
        ("exceptions", "Исключения"),
        ("deadlocks", "Дедлоки"),
        ("locks", "Блокировки"),
    ]:
        a_val = float(sa.get(key, 0) or 0)
        b_val = float(sb.get(key, 0) or 0)
        metrics.append(
            {
                "key": key,
                "label": label,
                "a": a_val,
                "b": b_val,
                "delta": b_val - a_val,
                "delta_percent": _delta_percent(a_val, b_val),
            }
        )
    return {"metrics": metrics}


def compare_slow_queries(
    archive_id_a: str,
    archive_id_b: str,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Diff топ-N медленных queries by sql_text_hash."""
    # query = exemplar самого медленного реального вызова, не нормализованная
    # форма со «?» (см. fix от 23.05.2026).
    sql = f"""
        SELECT
            sql_text_hash,
            ARG_MAX(COALESCE(sql_text, sql_text_normalized), duration_us) AS query,
            COUNT(*) AS calls,
            SUM(duration_us) / 1000.0 AS total_ms,
            AVG(duration_us) / 1000.0 AS avg_ms
        FROM events
        WHERE event_type = 'DBMSSQL'
          AND sql_text_hash IS NOT NULL
        GROUP BY sql_text_hash
        ORDER BY total_ms DESC NULLS LAST
        LIMIT {int(limit)}
    """
    with SQLExecutor(archive_id_a) as ex_a:
        a_rows = ex_a.execute(sql)["rows"]
    with SQLExecutor(archive_id_b) as ex_b:
        b_rows = ex_b.execute(sql)["rows"]

    def index_rows(rows: list[list[Any]]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for r in rows:
            sql_hash = str(r[0]) if r[0] is not None else None
            if not sql_hash:
                continue
            out[sql_hash] = {
                "sql_text_hash": sql_hash,
                "query": r[1],
                "calls": int(r[2] or 0),
                "total_ms": float(r[3] or 0),
                "avg_ms": float(r[4] or 0),
            }
        return out

    a_idx = index_rows(a_rows)
    b_idx = index_rows(b_rows)
    common = set(a_idx) & set(b_idx)
    only_a = set(a_idx) - set(b_idx)
    only_b = set(b_idx) - set(a_idx)

    in_both: list[dict[str, Any]] = []
    regressed: list[dict[str, Any]] = []
    improved: list[dict[str, Any]] = []
    for h in common:
        a = a_idx[h]
        b = b_idx[h]
        delta_pct = _delta_percent(a["avg_ms"], b["avg_ms"]) or 0.0
        row = {
            "sql_text_hash": h,
            "query": b["query"],
            "a_avg_ms": a["avg_ms"],
            "b_avg_ms": b["avg_ms"],
            "a_calls": a["calls"],
            "b_calls": b["calls"],
            "delta_percent": delta_pct,
        }
        in_both.append(row)
        if delta_pct >= 50:
            regressed.append(row)
        elif delta_pct <= -30:
            improved.append(row)

    in_both.sort(key=lambda r: r["delta_percent"], reverse=True)
    regressed.sort(key=lambda r: r["delta_percent"], reverse=True)
    improved.sort(key=lambda r: r["delta_percent"])

    return {
        "in_both": in_both,
        "only_a": [a_idx[h] for h in sorted(only_a, key=lambda h: -a_idx[h]["total_ms"])][:50],
        "only_b": [b_idx[h] for h in sorted(only_b, key=lambda h: -b_idx[h]["total_ms"])][:50],
        "regressed": regressed,
        "improved": improved,
    }
