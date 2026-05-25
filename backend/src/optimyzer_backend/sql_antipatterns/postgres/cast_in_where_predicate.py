"""PG antipattern #7 — Function/CAST на колонке в WHERE.

Pattern: WHERE LOWER(col) = '...' | col::text = '...' | EXTRACT(YEAR FROM col) = ...
Severity: WARNING
1С-aware: True (mchar/mvarchar cast'ы для 1С — normal)

Index seek невозможен без expression index. 1С регулярно кастует
mchar/mvarchar — это специально и не antipattern.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)
from optimyzer_backend.sql_antipatterns.postgres._helpers import safe_sql

_SARGABLE_BLOCKERS = {
    "UPPER", "LOWER", "SUBSTRING", "TO_CHAR", "TO_DATE", "EXTRACT",
    "DATE_TRUNC", "AGE", "LENGTH", "TRIM", "LTRIM", "RTRIM",
    "CAST", "COALESCE", "NULLIF",
}

# 1С-allowed cast types — эти не считаем antipattern в 1С-context.
_1C_ALLOWED_CAST_TYPES = {"mchar", "mvarchar", "fulleq"}


def _cast_is_1c_specific(cast_node: exp.Cast) -> bool:
    """Проверяет — это cast в 1С-specific тип (mchar/mvarchar/fulleq)?"""
    type_node = cast_node.args.get("to")
    if type_node is None:
        return False
    try:
        type_sql = type_node.sql(dialect="postgres").lower().strip()
    except Exception:  # noqa: BLE001
        return False
    # type_sql может быть "mchar", "mvarchar(50)", "::mchar", "AS mchar", etc.
    # Также проверяем через .this атрибут
    if hasattr(type_node, "this"):
        this_str = str(type_node.this).lower()
        if any(t in this_str for t in _1C_ALLOWED_CAST_TYPES):
            return True
    return any(t in type_sql for t in _1C_ALLOWED_CAST_TYPES)


def detect_cast_in_where_predicate(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue

        # Проверим явные CAST'ы
        for cast in where.find_all(exp.Cast):
            # 1С-aware: пропускаем mchar/mvarchar в 1С context
            if is_1c_context and _cast_is_1c_specific(cast):
                continue
            # Проверяем что CAST применяется к колонке (не к параметру/литералу)
            inner = cast.this
            if isinstance(inner, exp.Column):
                findings.append(
                    SqlAntipattern(
                        code="cast_in_where_predicate",
                        title="CAST на колонке в WHERE",
                        description=(
                            "CAST на колонке в WHERE делает условие non-SARGable — "
                            "обычный индекс не используется, нужен expression index."
                        ),
                        severity=AntipatternSeverity.WARNING,
                        dialect="postgres",
                        snippet=safe_sql(cast, 100),
                        rationale=(
                            "Optimizer не может использовать индекс по col если ищется "
                            "по результату cast(col). Нужен индекс по выражению."
                        ),
                        recommendation=(
                            "Либо кастовать литерал/параметр (не колонку), либо создать "
                            "expression index: `CREATE INDEX ... ON tbl (cast(col AS type));`"
                        ),
                    )
                )
                return findings

        # Проверим функции из SARGABLE_BLOCKERS на колонках
        for func in where.find_all(exp.Func):
            # 1С-aware: пропускаем CAST в mchar/mvarchar (это нормально для 1С)
            if is_1c_context and isinstance(func, exp.Cast) and _cast_is_1c_specific(func):
                continue
            try:
                func_name = func.sql_name().upper()
            except Exception:  # noqa: BLE001
                func_name = type(func).__name__.upper()
            if func_name not in _SARGABLE_BLOCKERS:
                continue
            has_column = False
            for desc in func.walk():
                node = desc[0] if isinstance(desc, tuple) else desc
                if isinstance(node, exp.Column) and node is not func:
                    has_column = True
                    break
            if has_column:
                findings.append(
                    SqlAntipattern(
                        code="cast_in_where_predicate",
                        title=f"Функция {func_name}() на колонке в WHERE",
                        description=(
                            f"Использование {func_name}(колонка) в WHERE — условие "
                            "non-SARGable, индекс по колонке не используется."
                        ),
                        severity=AntipatternSeverity.WARNING,
                        dialect="postgres",
                        snippet=safe_sql(func, 100),
                        rationale=(
                            "PG не сводит f(col) к индексу по col. Нужен expression "
                            "index по f(col) либо переписать без функции."
                        ),
                        recommendation=(
                            f"Создайте expression index: "
                            f"`CREATE INDEX ... ON tbl ({func_name.lower()}(col));` "
                            "либо перепишите условие без функции."
                        ),
                    )
                )
                return findings
    return findings


__all__ = ["detect_cast_in_where_predicate"]
