"""T-SQL antipatterns detectors (перенесено из sql/antipatterns.py).

9 правил Sprint 6, адаптированы под новый SqlAntipattern model:
  - not_in_with_subquery   — NOT IN с подзапросом (медленно + NULL ловушки)
  - left_join_filtered     — LEFT JOIN с фильтром на правую таблицу в WHERE
  - or_in_where            — OR в WHERE (оптимизатор плохо работает)
  - function_on_column     — функция на колонке в predicate (non-SARGable)
  - leading_wildcard_like  — LIKE '%pattern' (не использует индекс)
  - select_star            — SELECT * (избыточные колонки)
  - cross_join             — CROSS JOIN (картезианское произведение)
  - implicit_convert       — placeholder (покрывается function_on_column)
  - large_in_list          — IN (...) с 100+ литералами

Detector signature: detect_xxx(ast, is_1c_context=False) -> list[SqlAntipattern]
"""

from __future__ import annotations

import re
from typing import Optional

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)

_LARGE_IN_LIST_THRESHOLD = 100


def _safe_sql(node: exp.Expression, limit: int = 200) -> Optional[str]:
    try:
        s = node.sql(dialect="tsql")
        return s[:limit] if len(s) > limit else s
    except Exception:  # noqa: BLE001
        return None


# ---- detectors ----


def detect_not_in_with_subquery(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """NOT IN (SELECT ...) — медленно + ловушка с NULL."""
    results: list[SqlAntipattern] = []
    for not_node in ast.find_all(exp.Not):
        child = not_node.this
        if isinstance(child, exp.In):
            query = child.args.get("query")
            expressions = child.args.get("expressions") or []
            has_subquery = isinstance(query, (exp.Select, exp.Subquery)) or any(
                isinstance(e, (exp.Select, exp.Subquery)) for e in expressions
            )
            if has_subquery:
                results.append(
                    SqlAntipattern(
                        code="not_in_with_subquery",
                        title="NOT IN с подзапросом",
                        description=(
                            "NOT IN с подзапросом медленный и небезопасен при NULL "
                            "(если подзапрос вернёт NULL, NOT IN вернёт UNKNOWN и "
                            "отфильтрует ВСЕ строки). Используйте NOT EXISTS."
                        ),
                        severity=AntipatternSeverity.MAJOR,
                        dialect="mssql",
                        snippet=_safe_sql(not_node),
                        rationale="NULL-семантика трёхзначной логики делает NOT IN опасным.",
                        recommendation="Перепишите на NOT EXISTS — оптимизатор лучше планирует и NULL-safe.",
                    )
                )
                break
    return results


def detect_left_join_filtered(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """LEFT JOIN с фильтром в WHERE на колонку правой таблицы — становится INNER."""
    results: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue
        joins = select.args.get("joins") or []
        for join in joins:
            side = join.args.get("side")
            if side and str(side).upper() == "LEFT":
                right = join.this
                right_alias = right.alias_or_name if right else None
                if not right_alias:
                    continue
                where_text = (where.sql(dialect="tsql") if where else "").lower()
                pat = re.compile(
                    rf"\b{re.escape(right_alias.lower())}\.\w+\b(?!\s*is\s*null)"
                )
                if pat.search(where_text) and "is null" not in where_text:
                    results.append(
                        SqlAntipattern(
                            code="left_join_filtered",
                            title="LEFT JOIN с фильтром в WHERE → INNER",
                            description=(
                                f"LEFT JOIN таблицы '{right_alias}' с фильтром на её "
                                "колонку в WHERE превращает соединение в INNER JOIN "
                                "(NULL-строки отбрасываются). Если хотите только matched "
                                "строки — пишите INNER JOIN явно. Если хотите все "
                                "левые + найденные правые — перенесите условие в ON."
                            ),
                            severity=AntipatternSeverity.MAJOR,
                            dialect="mssql",
                            snippet=right_alias,
                            rationale="Семантика LEFT JOIN ломается фильтром на правую таблицу.",
                            recommendation="Перенесите условие в ON, либо смените на INNER JOIN.",
                        )
                    )
                    break
    return results


def detect_or_in_where(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """OR в WHERE — оптимизатор плохо использует индексы."""
    results: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue
        ors = list(where.find_all(exp.Or))
        if not ors:
            continue
        meaningful_ors = [
            o
            for o in ors
            if not any(
                isinstance(p, (exp.Case, exp.Func))
                for p in [o.parent, o.parent.parent if o.parent else None]
                if p
            )
        ]
        if meaningful_ors:
            results.append(
                SqlAntipattern(
                    code="or_in_where",
                    title="OR в условии WHERE",
                    description=(
                        f"WHERE содержит {len(meaningful_ors)} OR-условие(й). "
                        "Оптимизатор SQL Server часто не использует индексы при OR "
                        "и переходит на Table Scan. Рассмотрите UNION ALL вместо OR."
                    ),
                    severity=AntipatternSeverity.MAJOR,
                    dialect="mssql",
                    snippet=_safe_sql(where, 150),
                    rationale="OR блокирует index seek в большинстве сценариев MSSQL.",
                    recommendation="Разделите условия на UNION ALL — каждое получит свой план.",
                )
            )
            break
    return results


def detect_function_on_column(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """Функция на колонке в predicate — non-SARGable."""
    results: list[SqlAntipattern] = []
    sargable_blockers = {
        "UPPER", "LOWER", "SUBSTRING", "DATEADD", "DATEDIFF", "CAST",
        "CONVERT", "ISNULL", "COALESCE", "LEFT", "RIGHT", "LTRIM",
        "RTRIM", "YEAR", "MONTH", "DAY",
    }
    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue
        for func in where.find_all(exp.Func):
            try:
                func_name = func.sql_name().upper()
            except Exception:  # noqa: BLE001
                func_name = type(func).__name__.upper()
            if func_name not in sargable_blockers:
                continue
            has_column = False
            for desc in func.walk():
                node = desc[0] if isinstance(desc, tuple) else desc
                if isinstance(node, exp.Column) and node is not func:
                    has_column = True
                    break
            if has_column:
                results.append(
                    SqlAntipattern(
                        code="function_on_column",
                        title=f"Функция {func_name}() на колонке в WHERE",
                        description=(
                            f"Использование {func_name}(колонка) в WHERE делает условие "
                            "non-SARGable — индекс по колонке не используется. Перепишите "
                            "без функции на левой стороне сравнения."
                        ),
                        severity=AntipatternSeverity.MAJOR,
                        dialect="mssql",
                        snippet=_safe_sql(func, 100),
                        rationale="Optimizer не может использовать индекс если колонка обёрнута в функцию.",
                        recommendation="Перепишите так чтобы функция применялась к константе, не колонке.",
                    )
                )
                return results
    return results


def detect_leading_wildcard_like(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """LIKE '%pattern' — не использует b-tree индекс."""
    results: list[SqlAntipattern] = []
    for like in ast.find_all(exp.Like):
        pattern = like.args.get("expression")
        if isinstance(pattern, exp.Literal) and isinstance(pattern.this, str):
            if pattern.this.startswith("%"):
                results.append(
                    SqlAntipattern(
                        code="leading_wildcard_like",
                        title="LIKE с ведущим % (поиск с начала)",
                        description=(
                            f"LIKE '{pattern.this[:30]}' начинается с %, поэтому "
                            "SQL Server не может использовать обычный b-tree индекс. "
                            "Используйте Full-Text Search или денормализуйте."
                        ),
                        severity=AntipatternSeverity.MAJOR,
                        dialect="mssql",
                        snippet=f"LIKE '{pattern.this[:50]}'",
                        rationale="B-tree индекс требует префикс, leading % требует Scan.",
                        recommendation="Full-Text Search, либо хранение reversed string + b-tree.",
                    )
                )
                break
    return results


def detect_select_star(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """SELECT * — избыточные колонки + bookmark lookups."""
    results: list[SqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        expressions = select.args.get("expressions") or []
        for expr in expressions:
            if isinstance(expr, exp.Star):
                results.append(
                    SqlAntipattern(
                        code="select_star",
                        title="SELECT * — выбираются все колонки",
                        description=(
                            "SELECT * читает все колонки, что увеличивает I/O и часто "
                            "приводит к bookmark lookups вместо covering index. Явно "
                            "перечислите нужные колонки."
                        ),
                        severity=AntipatternSeverity.MINOR,
                        dialect="mssql",
                        snippet="SELECT *",
                        rationale="Избыточное чтение колонок ломает covering-index стратегии.",
                        recommendation="Явно перечислите только нужные колонки.",
                    )
                )
                return results
    return results


def detect_cross_join(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """CROSS JOIN без условия — картезиан."""
    results: list[SqlAntipattern] = []
    for join in ast.find_all(exp.Join):
        kind = join.args.get("kind")
        if kind and str(kind).upper() == "CROSS":
            results.append(
                SqlAntipattern(
                    code="cross_join",
                    title="CROSS JOIN (картезианское произведение)",
                    description=(
                        "CROSS JOIN перемножает строки таблиц — если не намеренно, "
                        "это почти всегда баг. Добавьте условие соединения."
                    ),
                    severity=AntipatternSeverity.CRITICAL,
                    dialect="mssql",
                    snippet=_safe_sql(join, 100),
                    rationale="Декартово произведение растёт экспоненциально.",
                    recommendation="Добавьте JOIN ... ON или замените на INNER JOIN.",
                )
            )
            break
    return results


def detect_implicit_convert(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """CAST/CONVERT в predicate — non-SARGable. Покрывается detect_function_on_column."""
    return []


def detect_large_in_list(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    """IN (...) с большим списком литералов — медленный план."""
    results: list[SqlAntipattern] = []
    for in_node in ast.find_all(exp.In):
        if in_node.args.get("query") is not None:
            continue
        expressions = in_node.args.get("expressions", [])
        if len(expressions) >= _LARGE_IN_LIST_THRESHOLD:
            results.append(
                SqlAntipattern(
                    code="large_in_list",
                    title=f"IN со списком из {len(expressions)} значений",
                    description=(
                        f"IN с {len(expressions)} литералами создаёт большой план "
                        "запроса и часто приводит к Hash Match. Используйте временную "
                        "таблицу + JOIN, или табличный параметр."
                    ),
                    severity=AntipatternSeverity.MAJOR,
                    dialect="mssql",
                    snippet=None,
                    rationale="Длинный IN превращается в OR-цепочку, optimizer теряется.",
                    recommendation="Поместите значения во временную таблицу и JOIN.",
                )
            )
            break
    return results


TSQL_DETECTORS = [
    detect_not_in_with_subquery,
    detect_left_join_filtered,
    detect_or_in_where,
    detect_function_on_column,
    detect_leading_wildcard_like,
    detect_select_star,
    detect_cross_join,
    detect_implicit_convert,
    detect_large_in_list,
]


__all__ = [
    "TSQL_DETECTORS",
    "detect_cross_join",
    "detect_function_on_column",
    "detect_implicit_convert",
    "detect_large_in_list",
    "detect_leading_wildcard_like",
    "detect_left_join_filtered",
    "detect_not_in_with_subquery",
    "detect_or_in_where",
    "detect_select_star",
]
