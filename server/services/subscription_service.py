"""Бизнес-логика подписок."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User


def get_or_create_subscription(db: Session, user: User) -> Subscription:
    """Достаём активную подписку юзера; если по какой-то причине нет — создаём Free."""
    if user.subscription is not None:
        return user.subscription
    now = datetime.utcnow()
    sub = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
        starts_at=now,
        ends_at=now.replace(year=now.year + 100),
        auto_renew=False,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def cancel_subscription(db: Session, user: User) -> Subscription:
    """Выключаем auto_renew — доступ остаётся до ends_at."""
    sub = get_or_create_subscription(db, user)
    if sub.plan == SubscriptionPlan.FREE:
        raise ValueError("Free plan cannot be cancelled (already free)")
    sub.auto_renew = False
    sub.status = SubscriptionStatus.CANCELLED
    db.commit()
    db.refresh(sub)
    return sub


def reactivate_subscription(db: Session, user: User) -> Subscription:
    """Возвращаем auto_renew, если подписка ещё активна."""
    sub = get_or_create_subscription(db, user)
    if sub.plan == SubscriptionPlan.FREE:
        raise ValueError("Free plan cannot be reactivated")
    if sub.ends_at <= datetime.utcnow():
        raise ValueError("Subscription has already expired — нужна новая оплата")
    sub.auto_renew = True
    sub.status = SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(sub)
    return sub
