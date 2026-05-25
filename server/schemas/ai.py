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
    """POST /v1/ai/explain_plan — вход.

    Sprint 8 Phase B: добавлено поле engine для выбора AI prompt
    (mssql terminology vs postgres terminology + 1С-specific knowledge).
    """

    model_config = ConfigDict(extra="forbid")

    sql_text: str = Field(min_length=1, max_length=50000)
    # Содержимое плана: SHOWPLAN_XML (от SSMS .sqlplan/paste), SHOWPLAN_TEXT
    # (от 1С MSSQL planSQLText), EXPLAIN ANALYZE TEXT (от 1С PG planSQLText),
    # или EXPLAIN FORMAT JSON (от pgAdmin / re-EXPLAIN Sprint 8 Phase B.4/B.5).
    # plan_format говорит как интерпретировать. Поле названо plan_xml исторически
    # (Phase A/B/C), переименование сломало бы Sprint 6/7 clients.
    plan_xml: str = Field(min_length=1, max_length=500000)
    plan_format: Literal["xml", "text", "json"] = Field(
        default="xml",
        description="xml = SSMS .sqlplan (MSSQL); text = SHOWPLAN_TEXT (MSSQL) или EXPLAIN ANALYZE (PG); json = EXPLAIN FORMAT JSON (PG).",
    )
    engine: Literal["mssql", "postgres"] = Field(
        default="mssql",
        description="Движок СУБД источника плана. Сервер выбирает соответствующий AI prompt: MSSQL терминология (Clustered Index Seek, Hash Match...) или PG (Seq Scan, Memoize...) + 1С-specific знание. Default 'mssql' для backward-compat с Sprint 7 clients.",
    )
    planview_warnings: list[dict] = Field(default_factory=list, max_length=200)
    missing_indexes: list[dict] = Field(default_factory=list, max_length=50)
    plan_summary: Optional[dict] = Field(
        default=None,
        description="Summary block от PerformanceStudio (только для MSSQL xml формата — для text/PG не заполняется).",
    )
    configuration_context: Optional[ConfigurationContext] = None
    related_tj_summary: Optional[str] = Field(default=None, max_length=5000)
    # Sprint 8 Phase C — antipatterns от sql_antipatterns engine (sqlglot).
    # Передаются для дополнения AI explanation контекстом — AI не повторяет
    # их в hotspots, но учитывает в recommendations и расширяет конкретикой плана.
    detected_antipatterns: list[dict] = Field(
        default_factory=list,
        max_length=30,
        description=(
            "Уже обнаруженные локально антипаттерны (sqlglot). Передаются AI "
            "для контекста. Формат: {code, title, severity, description, "
            "rationale, recommendation}."
        ),
    )


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


# ---------------- Sprint 10: TJ Config Builder AI ----------------


class EventConfig(BaseModel):
    """Настройка одного ТЖ события."""

    enabled: bool
    threshold_cs: Optional[int] = Field(
        default=None,
        ge=0,
        description="Порог в centiseconds (1 cs = 10 ms). None = нет фильтра по длительности.",
    )


class LogcfgEvents(BaseModel):
    """Набор событий ТЖ — все поля Optional (включать только нужные)."""

    CALL: Optional[EventConfig] = None
    SCALL: Optional[EventConfig] = None
    SDBL: Optional[EventConfig] = None
    DBMSSQL: Optional[EventConfig] = None
    DBPOSTGRS: Optional[EventConfig] = None
    TDEADLOCK: Optional[EventConfig] = None
    TLOCK: Optional[EventConfig] = None
    EXCP: Optional[EventConfig] = None
    EXCPCNTX: Optional[EventConfig] = None
    ADMIN: Optional[EventConfig] = None
    MEM: Optional[EventConfig] = None
    ATTN: Optional[EventConfig] = None
    TTIMEOUT: Optional[EventConfig] = None


class LogcfgConfig(BaseModel):
    """Структурированная конфигурация logcfg.xml (не raw XML)."""

    events: LogcfgEvents = Field(default_factory=LogcfgEvents)
    capture_plans: bool = Field(
        default=False,
        description="Добавить <plansql/> и property plansqltext — увеличивает объём в 3-4×.",
    )
    log_directory: str = Field(
        default="C:\\1C-TechLog",
        max_length=500,
        description="Путь к папке для хранения логов ТЖ.",
    )
    history_hours: int = Field(
        default=72,
        ge=1,
        le=720,
        description="Период хранения логов в часах (атрибут history в logcfg.xml).",
    )


class EventRationale(BaseModel):
    """Обоснование включения одного события от AI."""

    event: str = Field(max_length=32)
    threshold: str = Field(max_length=100, description='Человеческое описание порога, например "10 cs (100 мс)".')
    why: str = Field(max_length=500)


class LogcfgGenerateRequest(BaseModel):
    """POST /v1/ai/generate_logcfg — вход."""

    model_config = ConfigDict(extra="forbid")

    problem_description: str = Field(
        min_length=10,
        max_length=2000,
        description="Свободное описание проблемы производительности.",
    )
    platform_version: Optional[str] = Field(
        default=None,
        max_length=20,
        description='Версия платформы 1С, например "8.3.24". Если не указана — AI использует актуальную.',
    )
    dbms: Optional[Literal["mssql", "postgres", "both", "unknown"]] = Field(
        default="unknown",
        description="СУБД. AI включит соответствующие события (DBMSSQL / DBPOSTGRS).",
    )


class LogcfgGenerateResponse(BaseModel):
    """POST /v1/ai/generate_logcfg — выход."""

    config: LogcfgConfig
    explanation: str = Field(description="Краткое объяснение почему такая настройка подходит.")
    events_rationale: list[EventRationale] = Field(
        default_factory=list,
        max_length=15,
        description="Обоснование по каждому включённому событию.",
    )
    estimated_use_duration: str = Field(
        default="30-60 минут",
        description="Рекомендуемое время сбора логов с активной нагрузкой.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Предупреждения (например, о большом объёме).",
    )
    model_used: str
    duration_ms: int
