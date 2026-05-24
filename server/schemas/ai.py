"""Pydantic схемы для /v1/ai/* (Sprint 6 Phase D)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["Blocker", "Critical", "Major", "Minor", "Info"]


class DiagnosticInput(BaseModel):
    """Один LSP-style diagnostic от bsl-LS, нормализованный для AI prompt."""

    code: str = Field(max_length=128)
    message: str = Field(max_length=2000)
    severity: Severity
    range_start_line: int = Field(ge=0)
    range_start_char: int = Field(ge=0)
    range_end_line: int = Field(ge=0)
    range_end_char: int = Field(ge=0)
    snippet: str = Field(default="", max_length=2000)


class ConfigurationContext(BaseModel):
    """Дополнительный контекст из подключённой конфы 1С для AI prompt."""

    mdo_types_used: list[str] = Field(default_factory=list, max_length=50)
    tabular_sections_used: list[str] = Field(default_factory=list, max_length=50)
    registers_used: list[str] = Field(default_factory=list, max_length=50)


class ExplainRequest(BaseModel):
    """POST /v1/ai/explain — вход."""

    model_config = ConfigDict(extra="forbid")

    query_sdbl: str = Field(min_length=1, max_length=50000)
    diagnostics: list[DiagnosticInput] = Field(default_factory=list, max_length=100)
    configuration_context: Optional[ConfigurationContext] = None
    related_tj_summary: Optional[str] = Field(default=None, max_length=5000)


class IssueExplanation(BaseModel):
    """Одна логическая проблема в запросе (UI card)."""

    title: str = Field(max_length=200)
    severity: Severity
    what: str = Field(max_length=2000)  # «Что произошло»
    why: str = Field(max_length=2000)  # «Почему это плохо»
    what_to_do: str = Field(max_length=2000)  # «Что делать»
    linked_diagnostic_codes: list[str] = Field(default_factory=list, max_length=10)


class SuggestedRewrite(BaseModel):
    """AI-предложенная переписанная версия запроса."""

    available: bool = False
    sdbl: Optional[str] = Field(default=None, max_length=50000)
    reasoning: Optional[str] = Field(default=None, max_length=2000)


class ExplainResponse(BaseModel):
    """POST /v1/ai/explain — выход."""

    explanation_summary: str
    issues: list[IssueExplanation]
    suggested_rewrite: SuggestedRewrite
    model_used: str  # для telemetry / debugging
    duration_ms: int
