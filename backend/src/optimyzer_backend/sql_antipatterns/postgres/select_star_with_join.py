"""PG antipattern #12 — SELECT * с JOIN.

Pattern: SELECT * FROM a JOIN b ...
Severity: INFO
1С-aware: True (1С НЕ использует SELECT *, эта проблема не для 1С)

Лишние колонки, network bandwidth, defeats index-only scan.
В 1С context — детектор отключается (1С генерирует только явные SELECT col1, col2,...).
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def detect_select_star_with_join(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    # 1С-aware: в 1С context SELECT * не бывает — детектор полностью молчит
    if is_1c_context:
        return []

    findings: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        joins = select.args.get("joins") or []
        if not joins:
            continue
        expressions = select.args.get("expressions") or []
        has_star = any(isinstance(e, exp.Star) for e in expressions)
        if has_star:
            findings.append(
                SqlAntipattern(
                    code="select_star_with_join",
                    title="SELECT * в запросе с JOIN",
                    description=(
                        "SELECT * с JOIN читает все колонки всех таблиц, что "
                        "увеличивает I/O и сетевой трафик, и обычно ломает "
                        "index-only scan."
                    ),
                    severity=AntipatternSeverity.INFO,
                    dialect="postgres",
                    snippet="SELECT * ... JOIN ...",
                    rationale=(
                        "Лишние колонки — больше I/O, страдают covering-index "
                        "стратегии."
                    ),
                    recommendation=(
                        "Явно перечислите только нужные колонки таблиц."
                    ),
                )
            )
            return findings
    return findings


__all__ = ["detect_select_star_with_join"]
