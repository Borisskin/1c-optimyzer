"""PG antipattern #1 — OFFSET без LIMIT.

Pattern: SELECT ... OFFSET N (без LIMIT)
Severity: WARNING
1С-aware: False (общий PG антипаттерн)

PostgreSQL сканирует и пропускает все строки до offset позиции, что
делает запрос линейно медленнее с ростом offset.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)
from optimyzer_backend.sql_antipatterns.postgres._helpers import safe_sql


def detect_offset_without_limit(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        offset = select.args.get("offset")
        limit = select.args.get("limit")
        if offset is not None and limit is None:
            findings.append(
                SqlAntipattern(
                    code="offset_without_limit",
                    title="OFFSET без LIMIT",
                    description=(
                        "OFFSET без LIMIT — PostgreSQL сканирует все строки до "
                        "offset позиции, отбрасывая их. Запрос неоправданно "
                        "затратный и обычно говорит о баге в pagination."
                    ),
                    severity=AntipatternSeverity.WARNING,
                    dialect="postgres",
                    snippet=safe_sql(offset, 80),
                    rationale=(
                        "OFFSET в PostgreSQL требует сканирования и пропуска всех "
                        "строк до достижения offset. Чем дальше пейджинг — тем "
                        "медленнее. Без LIMIT смысл OFFSET сомнителен."
                    ),
                    recommendation=(
                        "Добавьте LIMIT N либо используйте keyset pagination: "
                        "`WHERE id > $last_id ORDER BY id LIMIT N` вместо OFFSET."
                    ),
                )
            )
            break  # одного на запрос достаточно
    return findings


__all__ = ["detect_offset_without_limit"]
