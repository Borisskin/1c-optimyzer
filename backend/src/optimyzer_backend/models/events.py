"""Event-модель: распарсенное ТЖ-событие."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventRecord(BaseModel):
    """Одно распарсенное событие ТЖ."""

    model_config = ConfigDict(extra="allow")

    archive_id: str
    ts: datetime
    duration_us: int | None = None
    event_type: str
    level: int | None = None

    session_id: int | None = None
    user_name: str | None = None
    context: str | None = None
    process: str | None = None
    process_pid: int | None = None

    sql_text: str | None = None
    sql_text_normalized: str | None = None
    sql_text_hash: str | None = None
    rows_read: int | None = None
    rows_modified: int | None = None

    extra: dict[str, Any] = Field(default_factory=dict)

    source_file: str | None = None
    source_line_start: int | None = None


class ColumnSpec(BaseModel):
    name: str
    type: str


class QueryResult(BaseModel):
    columns: list[ColumnSpec]
    rows: list[list[Any]]
    total_count: int
    truncated: bool = False
    executed_in_ms: float | None = None
