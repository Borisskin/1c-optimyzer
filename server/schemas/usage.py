"""Pydantic схемы для /v1/usage/*."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.usage import UsageBilledAgainst, UsageOperationType


class UsageTrackRequest(BaseModel):
    """POST /v1/usage/track."""

    operation_type: UsageOperationType
    archive_hash: str | None = None
    cost_credits: int = Field(default=1, ge=1, le=10)
    success: bool = True
    ai_tokens_input: int | None = None
    ai_tokens_output: int | None = None
    ai_cost_usd: float | None = None


class UsageTrackResponse(BaseModel):
    usage_id: str
    billed_against: UsageBilledAgainst


class UsageCheckResponse(BaseModel):
    """GET /v1/usage/check — desktop спрашивает «можно ли AI запустить?»"""

    allowed: bool
    reason: str | None = Field(
        default=None,
        description="free_limit_exceeded | credits_depleted | not_authenticated",
    )
    billed_against: UsageBilledAgainst | None = None
    options: list[Literal["upgrade", "buy_credits"]] = []
    free_quota_remaining: int | None = None
    credits_remaining: int | None = None
    pro_active: bool = False


class UsageSummaryResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    ai_operations_count: int
    ai_operations_by_type: dict[str, int]
    devices_seen_count: int
    free_quota_used: int
    free_quota_limit: int
    credits_used_this_period: int


class UsageRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation_type: str
    timestamp: datetime
    cost_credits: int
    billed_against: str
    success: bool
