"""AST классы для OptimyzerQL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

# ---------- Литералы и идентификаторы ----------


@dataclass
class StringLit:
    value: str


@dataclass
class NumberLit:
    value: float


@dataclass
class DurationLit:
    value: float
    unit: Literal["us", "ms", "s", "m", "h", "d"]


@dataclass
class Ident:
    name: str


Term = Union[StringLit, NumberLit, DurationLit, Ident]


# ---------- Условные выражения ----------


@dataclass
class BinaryCmp:
    left: "Expr"
    op: str  # ==, !=, <=, >=, <, >, startswith, endswith, contains, matches
    right: "Expr"


@dataclass
class InCmp:
    left: "Expr"
    values: list["Expr"]


@dataclass
class LogicalOp:
    op: Literal["and", "or"]
    items: list["Expr"]


@dataclass
class NotOp:
    inner: "Expr"


Expr = Union[BinaryCmp, InCmp, LogicalOp, NotOp, Term]


# ---------- Pipe-операторы ----------


@dataclass
class WhereOp:
    expr: Expr


@dataclass
class ProjectOp:
    columns: list[str]


@dataclass
class OrderTerm:
    column: str
    direction: Literal["asc", "desc"] = "asc"


@dataclass
class OrderOp:
    terms: list[OrderTerm]


@dataclass
class AggExpr:
    alias: str
    func: Literal["sum", "avg", "min", "max", "count", "countd"]
    arg: str  # column or "*"


@dataclass
class SummarizeOp:
    aggregations: list[AggExpr]
    group_by: list[str] = field(default_factory=list)


@dataclass
class TimerangeOp:
    """``timerange last <duration>``"""

    duration_us: int


@dataclass
class LimitOp:
    count: int


@dataclass
class TakeOp:
    count: int


@dataclass
class RenderOp:
    kind: Literal["table", "bar", "line", "histogram", "timeline", "scatter"]


PipeOp = Union[
    WhereOp,
    ProjectOp,
    OrderOp,
    SummarizeOp,
    TimerangeOp,
    LimitOp,
    TakeOp,
    RenderOp,
]


# ---------- Top-level ----------


@dataclass
class Source:
    name: str


@dataclass
class Query:
    source: Source
    pipes: list[PipeOp] = field(default_factory=list)
