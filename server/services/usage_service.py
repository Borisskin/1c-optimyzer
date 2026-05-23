"""Запись/аналитика AI-операций."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.device import Device
from models.usage import Usage, UsageBilledAgainst, UsageOperationType
from models.user import User
from services import credits_service
from services.soft_caps import (
    ai_operations_this_month,
    ai_operations_this_month_billed,
    decide,
    free_quota_remaining,
    month_start,
)

if TYPE_CHECKING:
    pass


class UsageDeniedError(Exception):
    """Soft cap не разрешил операцию."""


def track(
    db: Session,
    user: User,
    *,
    device: Device | None,
    operation_type: UsageOperationType,
    archive_hash: str | None,
    cost: int = 1,
    success: bool = True,
    ai_tokens_input: int | None = None,
    ai_tokens_output: int | None = None,
    ai_cost_usd: float | None = None,
) -> Usage:
    """Зарегистрировать факт выполнения AI-операции.

    Если операция была успешна — списываем Credits/Free квоту.
    Если success=False — записываем для аналитики (failed), но не списываем.
    """
    decision = decide(db, user, cost=cost)
    if not decision.allowed:
        raise UsageDeniedError(decision.reason or "denied")

    billed_against = decision.billed_against
    assert billed_against is not None  # guard for type checker

    # Списание Credits — атомарно с записью.
    if success and billed_against == UsageBilledAgainst.CREDITS_BALANCE:
        consumed = credits_service.consume_credit(db, user, amount=cost)
        if consumed is None:
            # Race condition (другая запись съела credits между decide и track).
            raise UsageDeniedError("credits_depleted")

    record = Usage(
        user_id=user.id,
        device_id=device.id if device else None,
        operation_type=operation_type,
        archive_hash=archive_hash,
        timestamp=datetime.utcnow(),
        cost_credits=cost,
        billed_against=billed_against,
        success=success,
        ai_tokens_input=ai_tokens_input,
        ai_tokens_output=ai_tokens_output,
        ai_cost_usd=ai_cost_usd,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def summary_for_user(db: Session, user: User) -> dict:
    """Сводка за текущий месяц для cabinet."""
    start = month_start()
    end = datetime.utcnow()

    op_count = ai_operations_this_month(db, user)

    by_type_rows = db.execute(
        select(Usage.operation_type, func.count(Usage.id))
        .where(
            Usage.user_id == user.id,
            Usage.timestamp >= start,
            Usage.success.is_(True),
        )
        .group_by(Usage.operation_type)
    ).all()
    by_type: Counter[str] = Counter()
    for ot, cnt in by_type_rows:
        by_type[ot.value if hasattr(ot, "value") else str(ot)] = int(cnt)

    devices_seen = db.scalar(
        select(func.count(func.distinct(Usage.device_id))).where(
            Usage.user_id == user.id,
            Usage.timestamp >= start,
            Usage.device_id.is_not(None),
        )
    )

    free_used = ai_operations_this_month_billed(db, user, UsageBilledAgainst.FREE_QUOTA)
    credits_used = ai_operations_this_month_billed(db, user, UsageBilledAgainst.CREDITS_BALANCE)

    return {
        "period_start": start,
        "period_end": end,
        "ai_operations_count": op_count,
        "ai_operations_by_type": dict(by_type),
        "devices_seen_count": int(devices_seen or 0),
        "free_quota_used": free_used,
        "free_quota_limit": free_quota_remaining(db, user) + free_used,
        "credits_used_this_period": credits_used,
    }
