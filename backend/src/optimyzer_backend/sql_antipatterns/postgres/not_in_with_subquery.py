"""PG antipattern #5 — NOT IN с подзапросом.

Pattern: WHERE col NOT IN (SELECT ...)
Severity: WARNING
1С-aware: False

PG не оптимизирует NOT IN с подзапросом так же хорошо как NOT EXISTS,
плюс NULL handling issues (если subquery вернёт NULL — NOT IN отфильтрует
все строки).
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)
from optimyzer_backend.sql_antipatterns.postgres._helpers import safe_sql


def detect_not_in_with_subquery_pg(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for not_node in ast.find_all(exp.Not):
        child = not_node.this
        if not isinstance(child, exp.In):
            continue
        query = child.args.get("query")
        expressions = child.args.get("expressions") or []
        has_subquery = isinstance(query, (exp.Select, exp.Subquery)) or any(
            isinstance(e, (exp.Select, exp.Subquery)) for e in expressions
        )
        if not has_subquery:
            continue

        findings.append(
            SqlAntipattern(
                code="not_in_with_subquery_pg",
                title="NOT IN с подзапросом (NULL-trap + slow)",
                description=(
                    "NOT IN с подзапросом в PostgreSQL: (1) если подзапрос вернёт "
                    "NULL, NOT IN вернёт UNKNOWN и отфильтрует ВСЕ строки; "
                    "(2) оптимизатор не выполняет anti-join так эффективно как "
                    "для NOT EXISTS. Перепишите на NOT EXISTS."
                ),
                severity=AntipatternSeverity.WARNING,
                dialect="postgres",
                snippet=safe_sql(not_node, 150),
                rationale=(
                    "NOT EXISTS работает через anti-join, который оптимизатор "
                    "PG умеет хорошо. NOT IN с подзапросом — нет."
                ),
                recommendation=(
                    "Перепишите: вместо `WHERE x NOT IN (SELECT y FROM t)` "
                    "используйте `WHERE NOT EXISTS (SELECT 1 FROM t WHERE t.y = x)`."
                ),
            )
        )
        break
    return findings


__all__ = ["detect_not_in_with_subquery_pg"]
