"""PG antipattern #11 — Implicit cast между несовместимыми типами.

Pattern: WHERE int_col = '123' (string vs int)
Severity: WARNING
1С-aware: True (mchar/mvarchar cast'ы — normal)

PG делает implicit cast, который ломает индекс. Heuristic: проверяем
сравнение Column = Literal где Column числовая, а Literal строка
(или наоборот). Для 1С specific типов — пропускаем.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)
from optimyzer_backend.sql_antipatterns.postgres._helpers import safe_sql


def _looks_like_int_column(col_name: str) -> bool:
    """Heuristic: колонка похожа на числовую по имени?

    Очень грубо: id, _id, count, num, version, version_no, ...
    """
    name = col_name.lower()
    return (
        name == "id"
        or name.endswith("_id")
        or name.endswith("id")
        or "count" in name
        or "num" in name
        or "version" in name
        or "_no" in name
    )


def _is_numeric_literal_string(literal: exp.Literal) -> bool:
    """Литерал — строка которая выглядит как число?"""
    if not literal.args.get("is_string"):
        return False
    val = literal.this
    if not isinstance(val, str):
        return False
    val = val.strip()
    try:
        int(val)
        return True
    except (ValueError, TypeError):
        try:
            float(val)
            return True
        except (ValueError, TypeError):
            return False


def detect_implicit_type_cast(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []

    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue

        for eq in where.find_all(exp.EQ):
            left = eq.this
            right = eq.expression
            # Ищем Column = Literal паттерн в любом порядке
            col, lit = None, None
            if isinstance(left, exp.Column) and isinstance(right, exp.Literal):
                col, lit = left, right
            elif isinstance(right, exp.Column) and isinstance(left, exp.Literal):
                col, lit = right, left
            if col is None or lit is None:
                continue

            col_name = col.name or ""
            # Heuristic: похожая на числовую колонка vs строковый литерал с числом
            if _looks_like_int_column(col_name) and _is_numeric_literal_string(lit):
                # 1С-aware: если колонка похожа на _Fld\d+ — это, скорее всего, 1С
                # и явный cast там уже подразумевается тестами. Скипаем.
                if is_1c_context and col_name.lower().startswith("_fld"):
                    continue
                findings.append(
                    SqlAntipattern(
                        code="implicit_type_cast",
                        title=f"Implicit cast: {col_name} = '{lit.this}'",
                        description=(
                            f"Колонка `{col_name}` похожа на числовую, а литерал "
                            f"`'{lit.this}'` — строковый. PostgreSQL применит "
                            "implicit cast, что может сломать использование индекса."
                        ),
                        severity=AntipatternSeverity.WARNING,
                        dialect="postgres",
                        snippet=safe_sql(eq, 100),
                        rationale=(
                            "Implicit cast меняет sargability и может вызвать "
                            "Seq Scan вместо Index Scan."
                        ),
                        recommendation=(
                            f"Если `{col_name}` действительно integer — "
                            f"передавайте число: `{col_name} = {lit.this}` (без кавычек). "
                            "Если string — приведите типы явно."
                        ),
                    )
                )
                return findings
    return findings


__all__ = ["detect_implicit_type_cast"]
