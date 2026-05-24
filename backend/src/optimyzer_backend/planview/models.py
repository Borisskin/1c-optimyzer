"""Pydantic schemas для PerformanceStudio CLI output (Sprint 7 Phase A).

Соответствуют ResultMapper.cs из PlanViewer.Core (research/PerformanceStudio/
src/PlanViewer.Core/Output/AnalysisResult.cs).

Все поля snake_case (через alias) — соответствуют JsonPropertyName в C#.
extra="allow" — чтобы новые поля в PerformanceStudio релизах не ломали parse.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WarningResult(BaseModel):
    """Одно warning от анализатора PerformanceStudio (или нативное из SQL Server)."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(default="", description="Имя правила: LargeMemoryGrant, KeyLookup, ...")
    severity: str = Field(default="Info", description="Info | Warning | Critical")
    message: str = Field(default="")
    operator: Optional[str] = Field(default=None, description="Имя оператора план-узла")
    node_id: Optional[int] = Field(default=None)
    max_benefit_percent: Optional[float] = Field(default=None)
    actionable_fix: Optional[str] = Field(default=None)
    is_legacy: bool = Field(default=False)


class MissingIndexResult(BaseModel):
    """Рекомендация индекса от SQL Server optimizer (через MissingIndexes в plan XML)."""

    model_config = ConfigDict(extra="allow")

    table: str = Field(default="")
    impact: float = Field(default=0.0, description="Estimated impact 0..100%")
    equality_columns: list[str] = Field(default_factory=list)
    inequality_columns: list[str] = Field(default_factory=list)
    include_columns: list[str] = Field(default_factory=list)
    create_statement: str = Field(default="")


class MemoryGrantResult(BaseModel):
    """Memory grant info — для actual/estimated plans."""

    model_config = ConfigDict(extra="allow")

    requested_kb: int = Field(default=0)
    granted_kb: int = Field(default=0)
    max_used_kb: int = Field(default=0)
    grant_wait_ms: int = Field(default=0)
    feedback_adjusted: Optional[str] = Field(default=None)
    estimated_available_memory_grant_kb: int = Field(default=0)
    desired_kb: int = Field(default=0)
    serial_required_kb: int = Field(default=0)


class QueryTimeResult(BaseModel):
    """Runtime stats (actual plans only)."""

    model_config = ConfigDict(extra="allow")

    cpu_time_ms: int = Field(default=0)
    elapsed_time_ms: int = Field(default=0)
    external_wait_ms: int = Field(default=0)


class OperatorResult(BaseModel):
    """Один узел операторного дерева план."""

    model_config = ConfigDict(extra="allow")

    node_id: int = Field(default=0)
    physical_op: str = Field(default="")
    logical_op: str = Field(default="")
    cost_percent: int = Field(default=0)
    estimated_rows: float = Field(default=0.0)
    estimated_cost: float = Field(default=0.0)
    estimated_io: float = Field(default=0.0)
    estimated_cpu: float = Field(default=0.0)
    object_name: Optional[str] = Field(default=None)
    index_name: Optional[str] = Field(default=None)
    seek_predicates: Optional[str] = Field(default=None)
    predicate: Optional[str] = Field(default=None)
    parallel: bool = Field(default=False)
    actual_rows: Optional[int] = Field(default=None)
    actual_elapsed_ms: Optional[int] = Field(default=None)
    actual_cpu_ms: Optional[int] = Field(default=None)
    warnings: list[WarningResult] = Field(default_factory=list)
    children: list["OperatorResult"] = Field(default_factory=list)


class StatementResult(BaseModel):
    """Один statement из batch (один SQL запрос)."""

    model_config = ConfigDict(extra="allow")

    statement_text: str = Field(default="")
    statement_type: str = Field(default="")
    estimated_cost: float = Field(default=0.0)
    estimated_rows: float = Field(default=0.0)
    optimization_level: Optional[str] = Field(default=None)
    early_abort_reason: Optional[str] = Field(default=None)
    cardinality_estimation_model: int = Field(default=0)
    compile_time_ms: int = Field(default=0)
    compile_memory_kb: int = Field(default=0)
    cached_plan_size_kb: int = Field(default=0)
    degree_of_parallelism: int = Field(default=0)
    non_parallel_reason: Optional[str] = Field(default=None)
    query_hash: Optional[str] = Field(default=None)
    query_plan_hash: Optional[str] = Field(default=None)
    memory_grant: Optional[MemoryGrantResult] = Field(default=None)
    query_time: Optional[QueryTimeResult] = Field(default=None)
    warnings: list[WarningResult] = Field(default_factory=list)
    missing_indexes: list[MissingIndexResult] = Field(default_factory=list)
    operator_tree: Optional[OperatorResult] = Field(default=None)


class PlanAnalysisSummary(BaseModel):
    """Агрегированная сводка по всем statements."""

    model_config = ConfigDict(extra="allow")

    total_statements: int = Field(default=0)
    total_warnings: int = Field(default=0)
    critical_warnings: int = Field(default=0)
    missing_indexes: int = Field(default=0)
    has_actual_stats: bool = Field(default=False)
    max_estimated_cost: float = Field(default=0.0)
    warning_types: list[str] = Field(default_factory=list)


class PlanAnalysisResult(BaseModel):
    """Top-level — соответствует PerformanceStudio AnalysisResult.cs.

    Возвращается из cli.analyze_plan_file и cli.analyze_plan_xml.
    """

    model_config = ConfigDict(extra="allow")

    plan_source: str = Field(default="", description="Имя файла или 'stdin'")
    sql_server_version: Optional[str] = Field(default=None)
    sql_server_build: Optional[str] = Field(default=None)
    statements: list[StatementResult] = Field(default_factory=list)
    summary: PlanAnalysisSummary = Field(default_factory=PlanAnalysisSummary)


# Pydantic v2 forward-references для recursive OperatorResult.children.
OperatorResult.model_rebuild()
