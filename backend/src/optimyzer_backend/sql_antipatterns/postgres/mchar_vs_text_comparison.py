"""PG antipattern #15 — 1С-specific: mchar/mvarchar vs text сравнение.

Pattern: WHERE col::mchar = $1::text | col::mvarchar = $1 (без cast обеих сторон)
Severity: WARNING
1С-aware: True (специфично для 1С)

В 1С PG build есть кастомные типы mchar/mvarchar/fulleq. Сравнение между
mchar и text может не использовать индекс — нужны явные cast'ы обеих сторон
в один тип.
"""

from __future__ import annotations

import re

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)

# Regex для обнаружения mchar/mvarchar/fulleq cast'ов в SQL тексте.
# Поддерживаем оба синтаксиса: PG-shorthand `col::mchar` И SQL-standard `CAST(col AS mchar)`.
_MCHAR_CAST = re.compile(
    r"(?:::|\bAS\s+)(mchar|mvarchar|fulleq)\b", re.IGNORECASE
)
_TEXT_CAST = re.compile(
    r"(?:::|\bAS\s+)(text|varchar)\b", re.IGNORECASE
)


def detect_mchar_vs_text_comparison(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """Активен ТОЛЬКО в 1С-context (mchar/mvarchar — расширение 1С PG)."""
    if not is_1c_context:
        return []

    findings: list[SqlAntipattern] = []

    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue

        for eq in where.find_all(exp.EQ):
            try:
                left_sql = eq.this.sql(dialect="postgres") if eq.this else ""
                right_sql = eq.expression.sql(dialect="postgres") if eq.expression else ""
            except Exception:  # noqa: BLE001
                continue

            left_is_mchar = bool(_MCHAR_CAST.search(left_sql))
            right_is_mchar = bool(_MCHAR_CAST.search(right_sql))
            left_is_text = bool(_TEXT_CAST.search(left_sql))
            right_is_text = bool(_TEXT_CAST.search(right_sql))

            mixed = (left_is_mchar and right_is_text) or (right_is_mchar and left_is_text)
            if not mixed:
                continue

            findings.append(
                SqlAntipattern(
                    code="mchar_vs_text_comparison",
                    title="Mixed mchar / text сравнение в WHERE",
                    description=(
                        "В WHERE сравниваются значения с явными cast'ами в разные "
                        "семейства типов (mchar/mvarchar vs text/varchar). "
                        "PostgreSQL может потерять способность использовать индекс "
                        "по mchar колонке."
                    ),
                    severity=AntipatternSeverity.WARNING,
                    dialect="postgres",
                    is_1c_context_only=True,
                    snippet=f"{left_sql[:60]} = {right_sql[:60]}",
                    rationale=(
                        "1С PG build определяет custom типы mchar/mvarchar/fulleq. "
                        "Сравнение mchar с text требует implicit cast одной стороны, "
                        "что обычно ломает использование индекса по mchar колонке."
                    ),
                    recommendation=(
                        "Приведите ОБЕ стороны к одному типу: либо `LHS::mvarchar = "
                        "RHS::mvarchar`, либо `LHS::text = RHS::text` (если параметр "
                        "уже text и колонка text)."
                    ),
                )
            )
            return findings
    return findings


__all__ = ["detect_mchar_vs_text_comparison"]
