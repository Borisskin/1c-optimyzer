"""Pydantic схемы для /v1/subscriptions/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: str
    status: str
    starts_at: datetime
    ends_at: datetime
    auto_renew: bool
    early_adopter: bool
    price_locked_kopecks: int


class SubscriptionCurrentResponse(BaseModel):
    """GET /v1/subscriptions/current."""

    subscription: SubscriptionRead


class SubscriptionMutationResponse(BaseModel):
    """POST /v1/subscriptions/cancel | reactivate."""

    subscription: SubscriptionRead
    message: str
