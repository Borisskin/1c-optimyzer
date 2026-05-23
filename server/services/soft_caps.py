"""Soft caps — лимиты AI-операций для Free / Pro / Credits.

Это самая важная часть бизнес-логики: правильно решить «можно ли юзеру
выполнить ещё одну AI-операцию».

Правила (см. SALES_SPRINT_PROMT.md Phase 1.5):
- Free: 5 AI/мес → потом denied, можно докупить Credits
- Pro: unlimited до 1000/мес → потом warning, но не denied
- Credits: каждая операция списывает 1 credit, при 0 — denied (если нет Pro)

Приоритет списания при наличии Pro И Credits — сначала Pro квота, потом Credits
(если Pro квота исчерпана — это для будущего, пока Pro = unlimited).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.settings import settings
from models.subscription import SubscriptionPlan
from models.usage import Usage, UsageBilledAgainst
from models.user import User
from services.credits_service import total_remaining as credits_remaining


@dataclass(slots=True, frozen=True)
class UsageDecision:
    """Решение soft cap engine."""

    allowed: bool
    reason: str | None
    billed_against: UsageBilledAgainst | None
    options: list[Literal["upgrade", "buy_credits"]]


def month_start(now: datetime | None = None) -> datetime:
    """Начало текущего месяца (UTC, naive)."""
    n = now or datetime.utcnow()
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def ai_operations_this_month(db: Session, user: User) -> int:
    """Сколько AI-операций юзер уже выполнил в этом месяце."""
    start = month_start()
    stmt = select(func.count(Usage.id)).where(
        Usage.user_id == user.id,
        Usage.timestamp >= start,
        Usage.success.is_(True),
    )
    return int(db.scalar(stmt) or 0)


def free_quota_remaining(db: Session, user: User) -> int:
    used = ai_operations_this_month_billed(db, user, UsageBilledAgainst.FREE_QUOTA)
    return max(settings.free_ai_monthly_limit - used, 0)


def ai_operations_this_month_billed(
    db: Session,
    user: User,
    billed_against: UsageBilledAgainst,
) -> int:
    start = month_start()
    stmt = select(func.count(Usage.id)).where(
        Usage.user_id == user.id,
        Usage.timestamp >= start,
        Usage.billed_against == billed_against,
        Usage.success.is_(True),
    )
    return int(db.scalar(stmt) or 0)


def decide(db: Session, user: User, *, cost: int = 1) -> UsageDecision:
    """Главная функция: можно ли юзеру выполнить операцию?"""
    sub = user.subscription
    is_pro = (
        sub is not None
        and sub.plan == SubscriptionPlan.PRO
        and sub.ends_at > datetime.utcnow()
    )
    if is_pro:
        # Pro: безлимит до soft cap (warning, но allowed остаётся True).
        used = ai_operations_this_month_billed(db, user, UsageBilledAgainst.PRO_QUOTA)
        if used + cost > settings.pro_ai_monthly_soft_cap:
            # Не блокируем — warning будет logged, но allow=True.
            pass
        return UsageDecision(
            allowed=True,
            reason=None,
            billed_against=UsageBilledAgainst.PRO_QUOTA,
            options=[],
        )

    # Не Pro: сначала пробуем Credits.
    if credits_remaining(db, user) >= cost:
        return UsageDecision(
            allowed=True,
            reason=None,
            billed_against=UsageBilledAgainst.CREDITS_BALANCE,
            options=[],
        )

    # Не Pro и Credits нет: пробуем Free квоту.
    if free_quota_remaining(db, user) >= cost:
        return UsageDecision(
            allowed=True,
            reason=None,
            billed_against=UsageBilledAgainst.FREE_QUOTA,
            options=[],
        )

    return UsageDecision(
        allowed=False,
        reason="free_limit_exceeded",
        billed_against=None,
        options=["upgrade", "buy_credits"],
    )
