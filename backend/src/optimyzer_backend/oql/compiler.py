"""AST → DuckDB SQL компилятор (parameterized SQL)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ast import (
    AggExpr,
    BinaryCmp,
    DurationLit,
    Ident,
    InCmp,
    LimitOp,
    LogicalOp,
    NotOp,
    NumberLit,
    OrderOp,
    OrderTerm,
    ProjectOp,
    Query,
    RenderOp,
    StringLit,
    SummarizeOp,
    TakeOp,
    TimerangeOp,
    WhereOp,
)


class OQLCompileError(ValueError):
    pass


# Canonical column names + aliases в schema events (Sprint 1, ADR-014).
ALLOWED_COLUMNS: set[str] = {
    "id",
    "archive_id",
    "ts",
    "duration_us",
    "event_type",
    "level",
    "session_id",
    "user_name",
    "context",
    "process",
    "process_role",
    "process_pid",
    "sql_text",
    "sql_text_normalized",
    "sql_text_hash",
    "rows_read",
    "rows_modified",
    "source_file",
    "source_line_start",
}

COLUMN_ALIASES: dict[str, str] = {
    "duration_ms": "duration_us",
    "duration": "duration_us",
    "sid": "session_id",
    "sql": "sql_text",
    "sql_normalized": "sql_text_normalized",
    "role": "process_role",
    "pid": "process_pid",
    "user": "user_name",
}


def resolve_column(name: str) -> str:
    if name in COLUMN_ALIASES:
        return COLUMN_ALIASES[name]
    if name in ALLOWED_COLUMNS:
        return name
    raise OQLCompileError(
        f"Неизвестный столбец «{name}». Доступны: "
        + ", ".join(sorted(ALLOWED_COLUMNS))
    )


# Маппинг user-facing op → SQL.
_BINARY_SQL: dict[str, str] = {
    "==": "=",
    "!=": "<>",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
}

_DURATION_UNIT_TO_US: dict[str, int] = {
    "us": 1,
    "ms": 1_000,
    "s": 1_000_000,
    "m": 60_000_000,
    "h": 3_600_000_000,
    "d": 86_400_000_000,
}


class SQLCompiler:
    """Компилирует Query → (sql_text, params_list).

    Sprint 1 ограничения:
    - Source whitelist: только "events".
    - Все literal values — параметризованы (защита от injection даже для owner).
    - Column whitelist через resolve_column().
    - duration coercion: `Duration > 1000ms` → `duration_us > 1000000`.
    """

    def __init__(self, active_archive_id: str):
        self.active_archive_id = active_archive_id
        # Хранятся для clarity при ошибках; пока не используются.
        self._render_hint: str | None = None

    def compile(self, query: Query) -> tuple[str, list[Any]]:
        if query.source.name != "events":
            raise OQLCompileError(
                f"Источник «{query.source.name}» недоступен в Module 1. "
                f"Доступен только «events»."
            )

        select_cols: list[str] = ["*"]
        where_parts: list[str] = ["archive_id = ?"]
        params: list[Any] = [self.active_archive_id]
        order_parts: list[str] = []
        group_by: list[str] = []
        agg_clauses: list[tuple[str, str]] = []  # (alias_sql, expression_sql)
        limit_n: int | None = None
        # Aliases агрегаций добавляются в scope для последующих ORDER BY/WHERE.
        summarize_aliases: set[str] = set()

        for op in query.pipes:
            if isinstance(op, WhereOp):
                where_clause, where_params = self._compile_expr(op.expr)
                where_parts.append(where_clause)
                params.extend(where_params)
            elif isinstance(op, ProjectOp):
                if op.columns:
                    select_cols = [self._resolve_col(c, summarize_aliases) for c in op.columns]
            elif isinstance(op, OrderOp):
                order_parts = [
                    f"{self._resolve_col(t.column, summarize_aliases)} {t.direction.upper()}"
                    for t in op.terms
                ]
            elif isinstance(op, SummarizeOp):
                select_cols, agg_clauses, group_by = self._compile_summarize(op)
                summarize_aliases = {agg.alias for agg in op.aggregations}
            elif isinstance(op, TimerangeOp):
                # ts >= now() - duration_us microseconds — DuckDB: `now() - INTERVAL '<us>' MICROSECONDS`
                where_parts.append(
                    "ts >= (CURRENT_TIMESTAMP - INTERVAL (CAST(? AS BIGINT)) MICROSECOND)"
                )
                params.append(op.duration_us)
            elif isinstance(op, LimitOp):
                limit_n = op.count
            elif isinstance(op, TakeOp):
                limit_n = op.count
            elif isinstance(op, RenderOp):
                self._render_hint = op.kind

        # SQL assembly
        select_sql = ", ".join(select_cols)
        if agg_clauses:
            # Override select для агрегаций
            select_parts = [f"{expr} AS {alias}" for alias, expr in agg_clauses]
            if group_by:
                gb_cols = [resolve_column(c) for c in group_by]
                select_parts = [resolve_column(c) for c in group_by] + select_parts
                select_sql = ", ".join(select_parts)
            else:
                select_sql = ", ".join(select_parts)

        sql = f"SELECT {select_sql} FROM events"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        if group_by:
            sql += " GROUP BY " + ", ".join(resolve_column(c) for c in group_by)
        if order_parts:
            sql += " ORDER BY " + ", ".join(order_parts)
        if limit_n is not None:
            sql += " LIMIT ?"
            params.append(limit_n)

        return sql, params

    def render_hint(self) -> str | None:
        return self._render_hint

    # ---------- helpers ----------

    @staticmethod
    def _resolve_col(name: str, summarize_aliases: set[str]) -> str:
        """Резолвит column name либо ловит ссылку на summarize alias.

        Aliases — output names агрегаций (например, `n = count(*)`), они
        валидны в последующих ORDER BY/WHERE/PROJECT. Возвращаются как is —
        SQL identifier check выполняется через `_sanitize_alias()`.
        """
        if name in summarize_aliases:
            # alias уже прошёл sanitize в _compile_summarize
            return name
        return resolve_column(name)

    def _compile_summarize(
        self, op: SummarizeOp
    ) -> tuple[list[str], list[tuple[str, str]], list[str]]:
        clauses: list[tuple[str, str]] = []
        for agg in op.aggregations:
            if agg.arg == "*":
                if agg.func != "count":
                    raise OQLCompileError(
                        f"Аргумент * допустим только для count, не {agg.func}"
                    )
                expr = "COUNT(*)"
            elif agg.func == "countd":
                col = resolve_column(agg.arg)
                expr = f"COUNT(DISTINCT {col})"
            else:
                col = resolve_column(agg.arg)
                func_sql = _AGG_FUNC_SQL[agg.func]
                expr = f"{func_sql}({col})"
            clauses.append((self._sanitize_alias(agg.alias), expr))
        return [], clauses, list(op.group_by)

    @staticmethod
    def _sanitize_alias(alias: str) -> str:
        # Алиасы в OQL — identifier-like; разрешаем буквы, цифры, _.
        if not alias.replace("_", "").isalnum():
            raise OQLCompileError(f"Невалидный alias агрегации: «{alias}»")
        return alias

    def _compile_expr(self, expr: Any) -> tuple[str, list[Any]]:
        if isinstance(expr, BinaryCmp):
            return self._compile_binary(expr)
        if isinstance(expr, InCmp):
            return self._compile_in(expr)
        if isinstance(expr, LogicalOp):
            parts: list[str] = []
            params: list[Any] = []
            for item in expr.items:
                clause, ps = self._compile_expr(item)
                parts.append(f"({clause})")
                params.extend(ps)
            joiner = " AND " if expr.op == "and" else " OR "
            return joiner.join(parts), params
        if isinstance(expr, NotOp):
            inner, ps = self._compile_expr(expr.inner)
            return f"NOT ({inner})", ps
        # Голый term/ident в WHERE — редко, но возможно: where context (truthy check)
        return self._compile_term_truthy(expr)

    def _compile_term_truthy(self, term: Any) -> tuple[str, list[Any]]:
        if isinstance(term, Ident):
            col = resolve_column(term.name)
            return f"{col} IS NOT NULL", []
        # numeric/string literal — приводим к literal в SQL (rare; in/where rare case)
        sql, params = self._term_to_sql(term)
        return f"({sql}) IS NOT NULL", params

    def _compile_binary(self, expr: BinaryCmp) -> tuple[str, list[Any]]:
        left_sql, left_params, left_kind = self._term_with_kind(expr.left)
        right_sql, right_params, right_kind = self._term_with_kind(expr.right)
        op = expr.op

        # Duration coercion: column duration_us сравнивается с DurationLit → конвертируем в us.
        if isinstance(expr.right, DurationLit) and left_kind == "ident":
            # left = duration_us, right = duration in us (всё уже в right_params после term_to_sql)
            pass
        if isinstance(expr.left, DurationLit) and right_kind == "ident":
            pass

        if op in _BINARY_SQL:
            sql = f"{left_sql} {_BINARY_SQL[op]} {right_sql}"
            return sql, left_params + right_params

        if op == "startswith":
            return (
                f"{left_sql} LIKE ? || '%'",
                left_params + right_params,
            )
        if op == "endswith":
            return (
                f"{left_sql} LIKE '%' || ?",
                left_params + right_params,
            )
        if op == "contains":
            return (
                f"{left_sql} LIKE '%' || ? || '%'",
                left_params + right_params,
            )
        if op == "matches":
            return (
                f"regexp_matches({left_sql}, ?)",
                left_params + right_params,
            )

        raise OQLCompileError(f"Неизвестный оператор сравнения: «{op}»")

    def _compile_in(self, expr: InCmp) -> tuple[str, list[Any]]:
        left_sql, left_params, _ = self._term_with_kind(expr.left)
        value_sqls: list[str] = []
        value_params: list[Any] = []
        for v in expr.values:
            sql, params = self._term_to_sql(v)
            value_sqls.append(sql)
            value_params.extend(params)
        return f"{left_sql} IN ({', '.join(value_sqls)})", left_params + value_params

    def _term_with_kind(self, term: Any) -> tuple[str, list[Any], str]:
        """Возвращает (sql, params, kind) где kind ∈ {'ident','literal'}."""
        if isinstance(term, Ident):
            col = resolve_column(term.name)
            return col, [], "ident"
        sql, params = self._term_to_sql(term)
        return sql, params, "literal"

    def _term_to_sql(self, term: Any) -> tuple[str, list[Any]]:
        if isinstance(term, StringLit):
            return "?", [term.value]
        if isinstance(term, NumberLit):
            return "?", [term.value if not float(term.value).is_integer() else int(term.value)]
        if isinstance(term, DurationLit):
            us = int(term.value * _DURATION_UNIT_TO_US[term.unit])
            return "?", [us]
        if isinstance(term, Ident):
            col = resolve_column(term.name)
            return col, []
        raise OQLCompileError(f"Неподдерживаемый терм: {type(term).__name__}")


_AGG_FUNC_SQL = {
    "sum": "SUM",
    "avg": "AVG",
    "min": "MIN",
    "max": "MAX",
    "count": "COUNT",
    # countd обрабатывается отдельной ветвью в _compile_summarize.
}
