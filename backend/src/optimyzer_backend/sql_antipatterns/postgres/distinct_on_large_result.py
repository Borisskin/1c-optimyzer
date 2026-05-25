"""PG antipattern #10 — DISTINCT для устранения дубликатов от JOIN.

Pattern: SELECT DISTINCT ... FROM a JOIN b ...
Severity: INFO (часто валидно, но иногда — heuristic)
1С-aware: False

Если разработчик использует DISTINCT чтобы убрать дубликаты возникшие
от 1:N JOIN — обычно лучше EXISTS или агрегация.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def detect_distinct_on_large_result(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        distinct = select.args.get("distinct")
        if distinct is None or not isinstance(distinct, exp.Distinct):
            continue
        # Только при наличии JOIN'ов
        joins = select.args.get("joins") or []
        if not joins:
            continue

        findings.append(
            SqlAntipattern(
                code="distinct_on_large_result",
                title="DISTINCT в запросе с JOIN",
                description=(
                    "DISTINCT в SELECT с JOIN часто скрывает дубликаты от 1:N "
                    "соединения. PostgreSQL делает HashAggregate или SORT+UNIQUE "
                    "поверх всего результата. Часто лучше EXISTS или GROUP BY."
                ),
                severity=AntipatternSeverity.INFO,
                dialect="postgres",
                snippet="SELECT DISTINCT ... JOIN ...",
                rationale=(
                    "DISTINCT — дополнительная фаза. Если дубликаты от JOIN, "
                    "EXISTS или агрегация работают быстрее."
                ),
                recommendation=(
                    "Если нужна только проверка существования — `WHERE EXISTS (...)`. "
                    "Если нужны агрегаты — `GROUP BY` с MAX/MIN/SUM."
                ),
            )
        )
        break
    return findings


__all__ = ["detect_distinct_on_large_result"]
