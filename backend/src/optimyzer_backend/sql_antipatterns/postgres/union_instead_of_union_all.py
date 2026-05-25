"""PG antipattern #8 — UNION вместо UNION ALL.

Pattern: SELECT ... UNION SELECT ... (без ALL)
Severity: INFO
1С-aware: False

UNION выполняет implicit SORT + UNIQUE дедупликацию. Если данные точно
не пересекаются (разные таблицы, разные фильтры) — это лишняя работа.
Нет способа проверить «уверен ли разработчик» — поэтому только INFO.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def detect_union_instead_of_union_all(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for union in ast.find_all(exp.Union):
        # exp.Union с distinct=True — это UNION (без ALL).
        distinct = union.args.get("distinct")
        if distinct is True or distinct is None:
            # Default для UNION в sqlglot — distinct=True (если не Union All)
            # Проверим что это не UnionAll явно
            findings.append(
                SqlAntipattern(
                    code="union_instead_of_union_all",
                    title="UNION (с SORT+UNIQUE)",
                    description=(
                        "UNION выполняет implicit SORT + UNIQUE для устранения "
                        "дубликатов. Если данные точно не пересекаются (разные "
                        "таблицы или непересекающиеся фильтры) — используйте "
                        "UNION ALL для скорости."
                    ),
                    severity=AntipatternSeverity.INFO,
                    dialect="postgres",
                    snippet="UNION",
                    rationale=(
                        "UNION DISTINCT требует дедупликации через SORT или "
                        "HASH. Это особенно дорого на больших результатах."
                    ),
                    recommendation=(
                        "Если уверены что результаты не пересекаются — замените "
                        "на UNION ALL."
                    ),
                )
            )
            break
    return findings


__all__ = ["detect_union_instead_of_union_all"]
