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


# ---------------- Sprint 7: Plan Analyzer AI ----------------

PlanSeverity = Literal["Info", "Warning", "Critical"]
"""
PerformanceStudio severity scheme — отдельная от bsl-LS (Blocker|Critical|
Major|Minor|Info). Каждый экран использует номенклатуру своего домена
(ADR-040 Sprint 7).
"""


class PlanExplainRequest(BaseModel):
    """POST /v1/ai/explain_plan — вход."""

    model_config = ConfigDict(extra="forbid")

    sql_text: str = Field(min_length=1, max_length=50000)
    plan_xml: str = Field(min_length=1, max_length=500000)
    planview_warnings: list[dict] = Field(default_factory=list, max_length=200)
    missing_indexes: list[dict] = Field(default_factory=list, max_length=50)
    plan_summary: Optional[dict] = Field(
        default=None,
        description="Summary block от PerformanceStudio (total_warnings, max_estimated_cost, warning_types)",
    )
    configuration_context: Optional[ConfigurationContext] = None
    related_tj_summary: Optional[str] = Field(default=None, max_length=5000)


class PlanHotspot(BaseModel):
    """Один проблемный оператор в плане (для UI card)."""

    operator_node_id: Optional[int] = Field(default=None)
    operator_type: str = Field(max_length=120)
    severity: PlanSeverity
    what: str = Field(max_length=2000)  # «Что происходит»
    why: str = Field(max_length=2000)  # «Почему это плохо»
    what_to_do: str = Field(max_length=2000)  # «Что делать»


class PlanRecommendation(BaseModel):
    """Actionable рекомендация (rewrite, index, config, stats)."""

    category: Literal["index", "query_rewrite", "config", "stats"]
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    impact_estimate: Literal["Critical", "High", "Medium", "Low"]


class PlanSuggestedIndex(BaseModel):
    """AI-приоритизированный CREATE INDEX с обоснованием.

    Может приходить либо от PerformanceStudio (через missing_indexes), либо
    предложенный AI как дополнение (например, для текстового плана из ТЖ).
    """

    table: str = Field(max_length=200)
    columns: list[str] = Field(default_factory=list, max_length=20)
    include: list[str] = Field(default_factory=list, max_length=20)
    rationale: str = Field(default="", max_length=2000)
    impact_estimate: Literal["Critical", "High", "Medium", "Low"] = "Medium"


class PlanExplainResponse(BaseModel):
    """POST /v1/ai/explain_plan — выход."""

    summary: str = Field(description="1-2 предложения сводки")
    overall_severity: PlanSeverity = Field(description="Max severity across hotspots")
    hotspots: list[PlanHotspot] = Field(default_factory=list, max_length=20)
    recommendations: list[PlanRecommendation] = Field(default_factory=list, max_length=10)
    suggested_indexes: list[PlanSuggestedIndex] = Field(default_factory=list, max_length=10)
    model_used: str
    duration_ms: int
    plan_truncated: bool = Field(
        default=False,
        description="True если plan XML был обрезан до AI_PLAN_MAX_CHARS (для больших планов)",
    )
