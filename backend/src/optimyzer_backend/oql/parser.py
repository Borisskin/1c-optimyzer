"""Lark parser + AST builder для OptimyzerQL."""

from __future__ import annotations

from importlib import resources
from typing import Any

from lark import Lark, Token, Transformer, UnexpectedCharacters, UnexpectedInput, UnexpectedToken
from lark.exceptions import LarkError

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
    Source,
    StringLit,
    SummarizeOp,
    TakeOp,
    TimerangeOp,
    WhereOp,
)


class OQLParseError(ValueError):
    """Синтаксическая ошибка OQL — с человекочитаемым сообщением."""

    def __init__(self, message: str, line: int | None = None, column: int | None = None):
        super().__init__(message)
        self.line = line
        self.column = column


_KEYWORD_SUGGESTIONS: dict[str, str] = {
    "filter": "where",
    "select": "project",
    "group": "summarize",
    "sort": "order by",
    "top": "take",
    "head": "take",
    "limit": "take",  # подсказка пользователям из SQL-фона
}


def _load_grammar() -> str:
    package = "optimyzer_backend.oql"
    return resources.files(package).joinpath("grammar.lark").read_text(encoding="utf-8")


_PARSER = Lark(_load_grammar(), parser="earley", maybe_placeholders=False, propagate_positions=True)


class _ToAST(Transformer):
    # ---------- Top-level ----------

    def start(self, items):
        return items[0]

    def query(self, items):
        source = items[0]
        pipes = list(items[1:])
        return Query(source=source, pipes=pipes)

    def source(self, items):
        return Source(name=str(items[0]))

    def pipe(self, items):
        return items[0]

    def pipe_op(self, items):
        return items[0]

    # ---------- Pipe operators ----------

    def where_op(self, items):
        return WhereOp(expr=items[0])

    def project_op(self, items):
        return ProjectOp(columns=items[0])

    def order_op(self, items):
        return OrderOp(terms=list(items))

    def order_term(self, items):
        col = str(items[0])
        direction = "asc"
        if len(items) > 1 and items[1] is not None:
            direction = str(items[1])
        return OrderTerm(column=col, direction=direction)

    def summarize_op(self, items):
        aggs = items[0]
        group_by: list[str] = []
        if len(items) > 1 and items[1] is not None:
            group_by = items[1]
        return SummarizeOp(aggregations=aggs, group_by=group_by)

    def timerange_op(self, items):
        # items: [duration]
        duration: DurationLit = items[0]
        unit_to_us = {
            "us": 1,
            "ms": 1_000,
            "s": 1_000_000,
            "m": 60_000_000,
            "h": 3_600_000_000,
            "d": 86_400_000_000,
        }
        us = int(duration.value * unit_to_us[duration.unit])
        return TimerangeOp(duration_us=us)

    def limit_op(self, items):
        return LimitOp(count=int(items[0]))

    def take_op(self, items):
        return TakeOp(count=int(items[0]))

    def render_op(self, items):
        return RenderOp(kind=str(items[0]))

    # ---------- Aggregations ----------

    def agg_list(self, items):
        return list(items)

    def agg_expr(self, items):
        alias = str(items[0])
        func = str(items[1])
        arg = str(items[2])
        return AggExpr(alias=alias, func=func, arg=arg)

    def agg_arg(self, items):
        return str(items[0])

    def col_list(self, items):
        return [str(it) for it in items]

    # ---------- Expressions ----------

    def expr(self, items):
        return items[0]

    def or_expr(self, items):
        operands = [it for it in items if not isinstance(it, Token) or it.type != "OR"]
        if len(operands) == 1:
            return operands[0]
        return LogicalOp(op="or", items=operands)

    def and_expr(self, items):
        operands = [it for it in items if not isinstance(it, Token) or it.type != "AND"]
        if len(operands) == 1:
            return operands[0]
        return LogicalOp(op="and", items=operands)

    def not_expr(self, items):
        # items: [NOT, expr] либо [expr] (через alias bare comparison)
        if len(items) >= 2 and isinstance(items[0], Token) and items[0].type == "NOT":
            return NotOp(inner=items[1])
        return items[0]

    def binary_cmp(self, items):
        return BinaryCmp(left=items[0], op=str(items[1]), right=items[2])

    def in_cmp(self, items):
        # items: [term, IN_KW, value_list]
        left = items[0]
        values = items[2] if len(items) > 2 else items[1]
        return InCmp(left=left, values=values)

    def paren(self, items):
        return items[0]

    def bare_term(self, items):
        return items[0]

    def value_list(self, items):
        return list(items)

    # ---------- Terms / literals ----------

    def string_lit(self, items):
        raw = str(items[0])
        # снимаем кавычки и обрабатываем escape
        text = raw[1:-1]
        text = text.replace("\\\\", "\\").replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")
        return StringLit(value=text)

    def number_lit(self, items):
        return NumberLit(value=float(items[0]))

    def duration_lit(self, items):
        return items[0]  # уже DurationLit из _duration

    def ident(self, items):
        return Ident(name=str(items[0]))

    def duration(self, items):
        return DurationLit(value=float(items[0]), unit=str(items[1]))


_TRANSFORMER = _ToAST()


def parse_oql(query: str) -> Query:
    """Разбирает текст OQL → AST.

    На ошибки бросает OQLParseError с человекочитаемым сообщением.
    Включает suggestion типа «возможно, имелось в виду 'where'» для популярных
    keyword-опечаток.
    """
    if not query.strip():
        raise OQLParseError("Пустой запрос — введите OQL-выражение, например: events | take 10")

    try:
        tree = _PARSER.parse(query)
    except UnexpectedToken as e:
        msg = _format_unexpected(query, e, kind="token")
        raise OQLParseError(msg, line=getattr(e, "line", None), column=getattr(e, "column", None)) from e
    except UnexpectedCharacters as e:
        msg = _format_unexpected(query, e, kind="char")
        raise OQLParseError(msg, line=getattr(e, "line", None), column=getattr(e, "column", None)) from e
    except UnexpectedInput as e:
        raise OQLParseError(f"Ошибка разбора: {e}") from e
    except LarkError as e:
        raise OQLParseError(f"Ошибка разбора: {e}") from e

    return _TRANSFORMER.transform(tree)


_WORD_BREAK = " \t\n\r,|(){}=<>!\"'+\\;"


def _format_unexpected(query: str, exc: Any, kind: str) -> str:
    token = getattr(exc, "token", None)
    found = ""
    if token is not None:
        found = str(token).strip()
    else:
        pos = getattr(exc, "pos_in_stream", None)
        if pos is not None and isinstance(pos, int) and 0 <= pos < len(query):
            end = pos
            while end < len(query) and query[end] not in _WORD_BREAK:
                end += 1
            found = query[pos:end] or query[pos : pos + 8]

    # Если token — это пробел или EOF, лучше показать предыдущий identifier
    found = found.strip()

    line = getattr(exc, "line", None)
    column = getattr(exc, "column", None)

    suggestion = ""
    if found:
        low = found.lower().strip("\"'")
        # Также проверяем первое слово, если found захватил несколько токенов
        first_word = low.split()[0] if low else ""
        for candidate in (low, first_word):
            if candidate in _KEYWORD_SUGGESTIONS:
                suggestion = f". Возможно, имелось в виду «{_KEYWORD_SUGGESTIONS[candidate]}»?"
                break

    pos_str = ""
    if line is not None and column is not None:
        pos_str = f" в строке {line}, позиция {column}"

    if not found:
        return f"Неожиданный конец запроса{pos_str}{suggestion}"
    return f"Неожиданный токен «{found}»{pos_str}{suggestion}"
