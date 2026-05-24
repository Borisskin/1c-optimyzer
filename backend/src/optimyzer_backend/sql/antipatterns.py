"""T-SQL antipatterns detector через sqlglot AST (Sprint 6 Phase F).

Используется в двух местах:
  1. TopSQL screen — колонка «Антипаттерны» с counts + drill-down
  2. QueryAnalyzer T-SQL view — если есть exemplar T-SQL связанный с SDBL

Каталог детектируемых антипаттернов (10 правил Sprint 6):
  - parse_error            — sqlglot не смог распарсить (явно T-SQL диалект)
  - not_in_with_subquery   — NOT IN с подзапросом (медленно + NULL ловушки)
  - left_join_filtered     — LEFT JOIN с фильтром на правую таблицу в WHERE (= INNER)
  - or_in_where            — OR в WHERE (оптимизатор плохо work)
  - function_on_column     — функция на колонке в predicate (non-SARGable)
  - leading_wildcard_like  — LIKE '%pattern' (не использует индекс)
  - select_star            — SELECT * (избыточные колонки + плохие планы)
  - cross_join             — CROSS JOIN (часто бесполезный картезиан)
  - implicit_convert       — CAST/CONVERT в условии (non-SARGable)
  - large_in_list          — IN (...) с 100+ литералами (медленный план)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import sqlglot
from sqlglot import exp


class AntipatternSeverity(str, Enum):
    BLOCKER = "Blocker"  # парсинг сломан, нет анализа
    CRITICAL = "Critical"  # гарантированная performance проблема
    MAJOR = "Major"  # антипаттерн с большой вероятностью проблем
    MINOR = "Minor"  # стилистическое замечание


@dataclass(frozen=True)
class TSqlAntipattern:
    """Один обнаруженный антипаттерн в T-SQL запросе."""

    code: str  # уникальный код правила
    title: str  # короткое название на русском
    description: str  # развёрнутое объяснение
    severity: AntipatternSeverity
    snippet: Optional[str] = None  # часть SQL с проблемой


# Лимиты — для предотвращения OOM на длинных запросах.
_MAX_SQL_LEN = 100_000  # 100KB
_LARGE_IN_LIST_THRESHOLD = 100


def detect_antipatterns(tsql: str) -> list[TSqlAntipattern]:
    """Анализирует T-SQL запрос и возвращает список найденных антипаттернов.

    Args:
        tsql: исходный T-SQL текст (как пришёл в DBMSSQL.Sql из ТЖ).

    Returns:
        Список TSqlAntipattern. Пустой если запрос чистый.
    """
    if not tsql or len(tsql) > _MAX_SQL_LEN:
        return []

    try:
        ast = sqlglot.parse_one(tsql, dialect="tsql")
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as e:
        return [
            TSqlAntipattern(
                code="parse_error",
                title="Парсер не смог разобрать запрос",
                description=f"sqlglot ParseError: {str(e)[:200]}",
                severity=AntipatternSeverity.BLOCKER,
            )
        ]

    if ast is None:
        return []

    patterns: list[TSqlAntipattern] = []
    patterns.extend(_detect_not_in_with_subquery(ast))
    patterns.extend(_detect_left_join_filtered(ast))
    patterns.extend(_detect_or_in_where(ast))
    patterns.extend(_detect_function_on_column(ast))
    patterns.extend(_detect_leading_wildcard_like(ast))
    patterns.extend(_detect_select_star(ast))
    patterns.extend(_detect_cross_join(ast))
    patterns.extend(_detect_implicit_convert(ast))
    patterns.extend(_detect_large_in_list(ast))
    return patterns


def _safe_sql(node: exp.Expression, limit: int = 200) -> Optional[str]:
    """Безопасно получает SQL ноды, обрезает до limit."""
    try:
        s = node.sql(dialect="tsql")
        return s[:limit] if len(s) > limit else s
    except Exception:  # noqa: BLE001
        return None


# ---- detectors ----


def _detect_not_in_with_subquery(ast: exp.Expression) -> list[TSqlAntipattern]:
    """NOT IN (SELECT ...) — медленно + ловушка с NULL."""
    results: list[TSqlAntipattern] = []
    for not_node in ast.find_all(exp.Not):
        child = not_node.this
        if isinstance(child, exp.In):
            # Подзапрос в IN — обычно Subquery, может быть Select.
            query = child.args.get("query")
            expressions = child.args.get("expressions") or []
            has_subquery = isinstance(query, (exp.Select, exp.Subquery)) or any(
                isinstance(e, (exp.Select, exp.Subquery)) for e in expressions
            )
            if has_subquery:
                results.append(
                    TSqlAntipattern(
                        code="not_in_with_subquery",
                        title="NOT IN с подзапросом",
                        description=(
                            "NOT IN с подзапросом медленный и небезопасен при NULL "
                            "(если подзапрос вернёт NULL, NOT IN вернёт UNKNOWN и "
                            "отфильтрует ВСЕ строки). Используйте NOT EXISTS."
                        ),
                        severity=AntipatternSeverity.MAJOR,
                        snippet=_safe_sql(not_node),
                    )
                )
                break  # один на запрос достаточно
    return results


def _detect_left_join_filtered(ast: exp.Expression) -> list[TSqlAntipattern]:
    """LEFT JOIN с фильтром в WHERE на колонку правой таблицы — становится INNER."""
    results: list[TSqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue
        joins = select.args.get("joins") or []
        for join in joins:
            side = join.args.get("side")
            if side and str(side).upper() == "LEFT":
                # Найдём alias правой таблицы.
                right = join.this
                right_alias = right.alias_or_name if right else None
                if not right_alias:
                    continue
                # Проверяем — есть ли в WHERE column этой таблицы (не в IS NULL).
                where_text = (where.sql(dialect="tsql") if where else "").lower()
                # Грубая heuristic: alias.column есть в WHERE без IS NULL.
                pat = re.compile(
                    rf"\b{re.escape(right_alias.lower())}\.\w+\b(?!\s*is\s*null)"
                )
                if pat.search(where_text) and "is null" not in where_text:
                    results.append(
                        TSqlAntipattern(
                            code="left_join_filtered",
                            title="LEFT JOIN с фильтром в WHERE → INNER",
                            description=(
                                f"LEFT JOIN таблицы '{right_alias}' с фильтром на её "
                                "колонку в WHERE превращает соединение в INNER JOIN "
                                "(NULL-строки отбрасываются). Если вы хотите оставить "
                                "только matched строки — пишите INNER JOIN явно. "
                                "Если хотите все левые + найденные правые — "
                                "перенесите условие в ON или добавьте IS NULL."
                            ),
                            severity=AntipatternSeverity.MAJOR,
                            snippet=right_alias,
                        )
                    )
                    break
    return results


def _detect_or_in_where(ast: exp.Expression) -> list[TSqlAntipattern]:
    """OR в WHERE — оптимизатор плохо использует индексы."""
    results: list[TSqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        where = select.args.get("where")
        if where is None:
            continue
        # Считаем количество OR в expression.
        ors = list(where.find_all(exp.Or))
        if not ors:
            continue
        # Игнорируем если OR внутри CASE или функции (там нормально).
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
                TSqlAntipattern(
                    code="or_in_where",
                    title="OR в условии WHERE",
                    description=(
                        f"WHERE содержит {len(meaningful_ors)} OR-условие(й). "
                        "Оптимизатор SQL Server часто не может использовать индексы "
                        "при OR и переходит на Table Scan. Рассмотрите UNION ALL "
                        "двух отдельных запросов вместо OR."
                    ),
                    severity=AntipatternSeverity.MAJOR,
                    snippet=_safe_sql(where, 150),
                )
            )
            break
    return results


def _detect_function_on_column(ast: exp.Expression) -> list[TSqlAntipattern]:
    """Функция на колонке в predicate (UPPER, LOWER, DATEADD на колонке, ...) — non-SARGable."""
    results: list[TSqlAntipattern] = []
    sargable_blockers = {
        "UPPER",
        "LOWER",
        "SUBSTRING",
        "DATEADD",
        "DATEDIFF",
        "CAST",
        "CONVERT",
        "ISNULL",
        "COALESCE",
        "LEFT",
        "RIGHT",
        "LTRIM",
        "RTRIM",
        "YEAR",
        "MONTH",
        "DAY",
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
            # Проверяем что функция применяется к колонке (через .this или nested).
            has_column = False
            for desc in func.walk():
                # walk возвращает tuples (node, parent, key) или просто node
                node = desc[0] if isinstance(desc, tuple) else desc
                if isinstance(node, exp.Column) and node is not func:
                    has_column = True
                    break
            if has_column:
                results.append(
                    TSqlAntipattern(
                        code="function_on_column",
                        title=f"Функция {func_name}() на колонке в WHERE",
                        description=(
                            f"Использование {func_name}(колонка) в WHERE делает "
                            "условие non-SARGable — индекс по колонке не используется. "
                            "Перепишите без функции на левой стороне сравнения."
                        ),
                        severity=AntipatternSeverity.MAJOR,
                        snippet=_safe_sql(func, 100),
                    )
                )
                return results  # одного достаточно
    return results


def _detect_leading_wildcard_like(ast: exp.Expression) -> list[TSqlAntipattern]:
    """LIKE '%pattern' — не использует индекс."""
    results: list[TSqlAntipattern] = []
    for like in ast.find_all(exp.Like):
        pattern = like.args.get("expression")
        if isinstance(pattern, exp.Literal) and isinstance(pattern.this, str):
            if pattern.this.startswith("%"):
                results.append(
                    TSqlAntipattern(
                        code="leading_wildcard_like",
                        title="LIKE с ведущим % (поиск с начала)",
                        description=(
                            f"LIKE '{pattern.this[:30]}' начинается с %, поэтому "
                            "SQL Server не может использовать обычный b-tree индекс. "
                            "Используйте Full-Text Search или денормализуйте."
                        ),
                        severity=AntipatternSeverity.MAJOR,
                        snippet=f"LIKE '{pattern.this[:50]}'",
                    )
                )
                break
    return results


def _detect_select_star(ast: exp.Expression) -> list[TSqlAntipattern]:
    """SELECT * — избыточные колонки + bookmark lookups."""
    results: list[TSqlAntipattern] = []
    for select in ast.find_all(exp.Select):
        expressions = select.args.get("expressions") or []
        for expr in expressions:
            if isinstance(expr, exp.Star):
                results.append(
                    TSqlAntipattern(
                        code="select_star",
                        title="SELECT * — выбираются все колонки",
                        description=(
                            "SELECT * читает все колонки, что увеличивает I/O и "
                            "часто приводит к bookmark lookups вместо covering index. "
                            "Явно перечислите нужные колонки."
                        ),
                        severity=AntipatternSeverity.MINOR,
                        snippet="SELECT *",
                    )
                )
                return results  # одного достаточно
    return results


def _detect_cross_join(ast: exp.Expression) -> list[TSqlAntipattern]:
    """CROSS JOIN без условия — картезиан."""
    results: list[TSqlAntipattern] = []
    for join in ast.find_all(exp.Join):
        kind = join.args.get("kind")
        side = join.args.get("side")
        if kind and str(kind).upper() == "CROSS":
            results.append(
                TSqlAntipattern(
                    code="cross_join",
                    title="CROSS JOIN (картезианское произведение)",
                    description=(
                        "CROSS JOIN перемножает строки таблиц — если это не "
                        "намеренно (например, для генерации календаря), это "
                        "почти всегда баг. Добавьте условие соединения."
                    ),
                    severity=AntipatternSeverity.CRITICAL,
                    snippet=_safe_sql(join, 100),
                )
            )
            break
        elif side is None and join.args.get("on") is None and kind is None:
            # Implicit cross join (запятая в FROM) — редко, но возможно.
            pass
    return results


def _detect_implicit_convert(ast: exp.Expression) -> list[TSqlAntipattern]:
    """CAST/CONVERT в predicate — non-SARGable."""
    # Покрывается detect_function_on_column, но дублируем явно для clarity.
    return []


def _detect_large_in_list(ast: exp.Expression) -> list[TSqlAntipattern]:
    """IN (...) с большим списком литералов — медленный план."""
    results: list[TSqlAntipattern] = []
    for in_node in ast.find_all(exp.In):
        # Только если внутри литералы (не подзапрос).
        if in_node.args.get("query") is not None:
            continue
        expressions = in_node.args.get("expressions", [])
        if len(expressions) >= _LARGE_IN_LIST_THRESHOLD:
            results.append(
                TSqlAntipattern(
                    code="large_in_list",
                    title=f"IN со списком из {len(expressions)} значений",
                    description=(
                        f"IN с {len(expressions)} литералами создаёт большой план "
                        "запроса и часто приводит к Hash Match. Используйте "
                        "временную таблицу + JOIN, или табличный параметр."
                    ),
                    severity=AntipatternSeverity.MAJOR,
                    snippet=None,
                )
            )
            break
    return results


__all__ = [
    "AntipatternSeverity",
    "TSqlAntipattern",
    "detect_antipatterns",
]
