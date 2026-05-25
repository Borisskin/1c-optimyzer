"""PG antipattern #9 — Correlated subquery в SELECT list.

Pattern: SELECT col, (SELECT ... FROM other WHERE other.fk = main.id) FROM main
Severity: WARNING
1С-aware: False

N+1 problem на больших результатах. Лучше LATERAL JOIN или агрегация.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)
from optimyzer_backend.sql_antipatterns.postgres._helpers import safe_sql


def _is_correlated(subq: exp.Expression, outer_aliases: set[str]) -> bool:
    """Subquery считается correlated если ссылается на outer alias."""
    if not outer_aliases:
        return False
    for col in subq.find_all(exp.Column):
        table = col.table
        if table and table.lower() in outer_aliases:
            return True
    return False


def detect_subquery_in_select_list(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        # Соберём aliases внешних таблиц
        outer_aliases: set[str] = set()
        from_clause = select.args.get("from_") or select.args.get("from")
        if from_clause is not None:
            for tbl in from_clause.find_all(exp.Table):
                alias = tbl.alias_or_name
                if alias:
                    outer_aliases.add(alias.lower())

        expressions = select.args.get("expressions") or []
        for expr in expressions:
            # Подзапрос в SELECT list оборачивается в Subquery или прямо exp.Select
            subqs: list[exp.Expression] = []
            if isinstance(expr, exp.Subquery):
                subqs.append(expr)
            if isinstance(expr, exp.Select):
                subqs.append(expr)
            # Также ищем nested subqueries (например внутри функции/выражения)
            for sq in expr.find_all(exp.Subquery):
                if sq not in subqs:
                    subqs.append(sq)
            for subq in subqs:
                inner = subq.this if isinstance(subq, exp.Subquery) else subq
                if not isinstance(inner, exp.Select):
                    continue
                if _is_correlated(inner, outer_aliases):
                    findings.append(
                        SqlAntipattern(
                            code="subquery_in_select_list",
                            title="Correlated subquery в SELECT list",
                            description=(
                                "Подзапрос в списке колонок ссылается на внешнюю "
                                "таблицу — выполняется для каждой строки результата "
                                "(N+1). Перепишите через LATERAL JOIN или агрегацию."
                            ),
                            severity=AntipatternSeverity.WARNING,
                            dialect="postgres",
                            snippet=safe_sql(subq, 150),
                            rationale=(
                                "Correlated subquery выполняется per-row, что "
                                "линейно растёт с размером outer query."
                            ),
                            recommendation=(
                                "Используйте `LEFT JOIN LATERAL (subquery) ON TRUE` "
                                "либо агрегацию через `GROUP BY`."
                            ),
                        )
                    )
                    return findings
    return findings


__all__ = ["detect_subquery_in_select_list"]
