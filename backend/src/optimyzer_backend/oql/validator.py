"""Validator — проверки AST до компиляции в SQL."""

from __future__ import annotations

from .ast import (
    AggExpr,
    BinaryCmp,
    InCmp,
    LogicalOp,
    NotOp,
    OrderOp,
    ProjectOp,
    Query,
    RenderOp,
    StringLit,
    SummarizeOp,
    TimerangeOp,
    WhereOp,
)
from .compiler import ALLOWED_COLUMNS, COLUMN_ALIASES, resolve_column


class OQLValidationError(ValueError):
    pass


ALLOWED_SOURCES = {"events"}


def validate(query: Query, active_archive_id: str | None = None) -> list[str]:
    """Возвращает список ошибок (или пустой список, если запрос валиден).

    Не бросает — собирает все ошибки сразу, чтобы UI показал список.
    Учитывает aliases от предыдущих SummarizeOp (после summarize columns
    становятся group_by + aliases агрегаций).
    """
    errors: list[str] = []

    if query.source.name not in ALLOWED_SOURCES:
        errors.append(
            f"Источник «{query.source.name}» недоступен в Module 1. "
            f"Доступен только «events». Источники «metrics», «deadlocks», "
            f"«code_graph», «configurations» появятся в следующих модулях."
        )

    # Текущий scope доступных колонок. Меняется после SummarizeOp.
    scope: set[str] = set(ALLOWED_COLUMNS) | set(COLUMN_ALIASES)

    for op in query.pipes:
        if isinstance(op, WhereOp):
            _collect_unknown_columns_in_expr(op.expr, errors, scope)
        elif isinstance(op, ProjectOp):
            for c in op.columns:
                if c not in scope:
                    errors.append(_unknown_column_msg(c))
        elif isinstance(op, OrderOp):
            for term in op.terms:
                if term.column not in scope:
                    errors.append(_unknown_column_msg(term.column))
        elif isinstance(op, SummarizeOp):
            for agg in op.aggregations:
                if agg.arg != "*" and agg.arg not in scope:
                    errors.append(_unknown_column_msg(agg.arg))
            for c in op.group_by:
                if c not in scope:
                    errors.append(_unknown_column_msg(c))
            # После summarize — scope = group_by columns + aggregation aliases
            new_scope: set[str] = set(op.group_by)
            for agg in op.aggregations:
                new_scope.add(agg.alias)
            scope = new_scope
        elif isinstance(op, RenderOp):
            pass
        elif isinstance(op, TimerangeOp):
            if op.duration_us < 0:
                errors.append("timerange must use positive duration")
        # WhereOp / TakeOp / LimitOp — проверки в expr-collector выше

    return errors


def _is_known_column(name: str) -> bool:
    return name in ALLOWED_COLUMNS or name in COLUMN_ALIASES


def _unknown_column_msg(name: str) -> str:
    return (
        f"Неизвестный столбец «{name}». Доступны: "
        + ", ".join(sorted(ALLOWED_COLUMNS))
        + "."
    )


def _collect_unknown_columns_in_expr(expr, errors: list[str], scope: set[str] | None = None) -> None:
    if scope is None:
        scope = set(ALLOWED_COLUMNS) | set(COLUMN_ALIASES)
    if isinstance(expr, BinaryCmp):
        _collect_unknown_columns_in_expr(expr.left, errors, scope)
        _collect_unknown_columns_in_expr(expr.right, errors, scope)
    elif isinstance(expr, InCmp):
        _collect_unknown_columns_in_expr(expr.left, errors, scope)
        for v in expr.values:
            _collect_unknown_columns_in_expr(v, errors, scope)
    elif isinstance(expr, LogicalOp):
        for item in expr.items:
            _collect_unknown_columns_in_expr(item, errors, scope)
    elif isinstance(expr, NotOp):
        _collect_unknown_columns_in_expr(expr.inner, errors, scope)
    elif hasattr(expr, "name"):
        if expr.name not in scope:
            errors.append(_unknown_column_msg(expr.name))
