"""Sprint 11 Phase E — Загрузка operation aggregates из DuckDB архива.

Запрашивает per-operation метрики (p50, p95, count) для regression analysis.
"""

from __future__ import annotations

from optimyzer_backend.regression.operation_matcher import OperationData
from optimyzer_backend.sql.executor import SQLExecutor

# DuckDB query — агрегируем по context_normalized + берём exemplar контекста
# через ARG_MAX (самый медленный пример как репрезентативный).
_QUERY_OPERATIONS = """
SELECT
    context_normalized AS operation_name,
    ARG_MAX(COALESCE(context, ''), duration_us) AS context_exemplar,
    COUNT(*) AS samples_count,
    QUANTILE_CONT(duration_us, 0.5)  AS p50_us,
    QUANTILE_CONT(duration_us, 0.95) AS p95_us
FROM events
WHERE context_normalized IS NOT NULL
  AND context_normalized <> ''
  AND duration_us IS NOT NULL
  AND duration_us > 0
GROUP BY context_normalized
"""


def load_operations(archive_id: str) -> list[OperationData]:
    """Загружает все operations из архива с их p50/p95/count.

    Returns:
        Список OperationData (не отфильтрованный, фильтрацию делает classifier
        через threshold + min_samples).
    """
    with SQLExecutor(archive_id) as ex:
        result = ex.execute(_QUERY_OPERATIONS)

    operations: list[OperationData] = []
    for row in result["rows"]:
        name = str(row[0]) if row[0] is not None else ""
        context = str(row[1]) if row[1] is not None else ""
        count = int(row[2] or 0)
        p50_us = float(row[3] or 0)
        p95_us = float(row[4] or 0)
        if not name or count == 0:
            continue
        operations.append(
            OperationData(
                name=name,
                context=context,
                samples_count=count,
                p50_duration_ms=p50_us / 1000.0,
                p95_duration_ms=p95_us / 1000.0,
            )
        )
    return operations
