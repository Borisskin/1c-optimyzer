"""Pydantic-модели bsl-LS adapter (Sprint 6).

Соответствуют структуре JSON-output bsl-language-server (JsonReporter формат)
и LSP Diagnostic spec. Используются в RPC слое и в cloud AI orchestration.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    """Нормализованная severity (наш domain). Маппинг с LSP severity и bsl-LS
    severity tag — в parser.py."""

    BLOCKER = "Blocker"
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    INFO = "Info"

    @property
    def order(self) -> int:
        """Чем выше число — тем критичнее. Для max() в DiagnosticGroup."""
        return {
            Severity.BLOCKER: 4,
            Severity.CRITICAL: 3,
            Severity.MAJOR: 2,
            Severity.MINOR: 1,
            Severity.INFO: 0,
        }[self]


class Position(BaseModel):
    """Позиция в файле — 0-based line/character, как в LSP."""

    line: int = Field(ge=0)
    character: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class Range(BaseModel):
    """Диапазон [start, end) — как в LSP."""

    start: Position
    end: Position

    model_config = ConfigDict(frozen=True)

    def overlaps(self, other: "Range") -> bool:
        """True если ranges пересекаются (для дедупликации diagnostics, Q6)."""
        # Если начало одного >= конца другого — не пересекаются.
        if self._pos_geq(self.start, other.end):
            return False
        if self._pos_geq(other.start, self.end):
            return False
        return True

    @staticmethod
    def _pos_geq(a: Position, b: Position) -> bool:
        if a.line != b.line:
            return a.line > b.line
        return a.character >= b.character


class Diagnostic(BaseModel):
    """Один warning от bsl-LS, нормализованный в наш домен."""

    code: str  # "RefOveruse"
    code_description_href: Optional[str] = None  # https://1c-syntax.github.io/.../RefOveruse
    message: str  # "Избавьтесь от \"Ссылка\""
    range: Range
    severity: Severity
    source: str = "bsl-language-server"  # const
    tags: list[str] = Field(default_factory=list)  # SQL, PERFORMANCE, ...
    snippet: Optional[str] = None  # подстрока из SDBL по range (заполняется parser)


class DiagnosticGroup(BaseModel):
    """Группа overlapping diagnostics — дедупликация по Q6.

    Несколько rules могут срабатывать на одно и то же место кода
    (например, RefOveruse + QueryNestedFieldsByDot на одной цепочке).
    Группируем в одну логическую issue с max(severity).
    """

    range: Range
    severity: Severity  # max из всех
    codes: list[str]  # ["RefOveruse", "QueryNestedFieldsByDot"]
    messages: list[str]  # все сообщения, в порядке убывания severity
    snippet: Optional[str] = None
    primary: Diagnostic  # самый critical в группе — backward-compat для UI


class AnalyzeRequest(BaseModel):
    """Запрос на анализ SDBL текста.

    Если configuration_root указан — bsl-LS активирует семантическую валидацию
    (QueryToMissingMetadata и т.п.). Если нет — только синтаксические правила.
    """

    query_sdbl: str
    configuration_root: Optional[str] = None
    enabled_rules: Optional[list[str]] = None  # None = use defaults (см. Q7)
    file_uri: str = "inmemory:///query.bsl"  # фейковый URI для LSP didOpen


class AnalyzeResult(BaseModel):
    """Результат анализа — diagnostics + grouped + metadata."""

    diagnostics: list[Diagnostic]
    grouped: list[DiagnosticGroup]
    parse_success: bool
    analysis_duration_ms: int
    bsl_ls_version: str = "0.29.0"
