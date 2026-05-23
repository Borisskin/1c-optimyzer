"""/v1/dashboard/summary — единый endpoint для Overview страницы cabinet'а.

Чтобы избежать N+1 запросов с фронта — одним вызовом отдаём всё нужное
для главной.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db import get_db
from api.deps import get_current_user
from models.user import User
from schemas.auth import UserPublic
from schemas.subscriptions import SubscriptionRead
from services import credits_service, device_service, subscription_service, usage_service

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


class DashboardSummary(BaseModel):
    user: UserPublic
    subscription: SubscriptionRead
    credits_remaining: int
    devices_active: int
    devices_limit: int
    ai_operations_this_month: int
    ai_operations_free_remaining: int
    pro_active: bool
    server_time: datetime


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummary:
    sub = subscription_service.get_or_create_subscription(db, user)
    summary = usage_service.summary_for_user(db, user)
    return DashboardSummary(
        user=UserPublic.model_validate(user),
        subscription=SubscriptionRead.model_validate(sub),
        credits_remaining=credits_service.total_remaining(db, user),
        devices_active=len(device_service.list_active(db, user)),
        devices_limit=device_service.get_device_limit(user),
        ai_operations_this_month=summary["ai_operations_count"],
        ai_operations_free_remaining=summary["free_quota_limit"] - summary["free_quota_used"],
        pro_active=sub.is_pro_active,
        server_time=datetime.utcnow(),
    )
