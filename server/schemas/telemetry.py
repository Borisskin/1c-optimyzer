"""Pydantic схемы для /v1/telemetry/* и /v1/admin/telemetry/*."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EventCategory = Literal["tech", "behavior", "conversion"]


class TelemetryEventIn(BaseModel):
    """Один event от desktop."""

    device_fingerprint: str = Field(min_length=8, max_length=128)
    app_version: str = Field(max_length=32)
    platform: str = Field(max_length=16)
    category: EventCategory
    event_type: str = Field(max_length=64)
    payload: dict = Field(default_factory=dict)
    timestamp: datetime


class TelemetryBatchRequest(BaseModel):
    """POST /v1/telemetry/batch."""

    events: list[TelemetryEventIn] = Field(min_length=1, max_length=500)


class TelemetryBatchResponse(BaseModel):
    accepted: int


# --- Admin summary ---


class TelemetrySummaryRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    count: int


class TelemetrySummary(BaseModel):
    """GET /v1/admin/telemetry/summary."""

    period_days: int
    total_events: int
    unique_devices: int
    by_category: list[TelemetrySummaryRow]
    by_event_type: list[TelemetrySummaryRow]
    by_app_version: list[TelemetrySummaryRow]
    by_platform: list[TelemetrySummaryRow]
