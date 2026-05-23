"""Lookup-by-email — desktop flow без OAuth.

Юзер в desktop вводит email → server находит/создаёт user → отдаёт device JWT
и информацию о подписке. Без верификации email (по решению Сергея).

Если email не существует — создаётся Free user. Если существует — берётся
существующий (с привязанной подпиской из cabinet OAuth, если была).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User
from services import device_service
from services.auth_service import utc_naive_now


class DeviceLimitReached(Exception):
    def __init__(self, active_count: int, limit: int) -> None:
        super().__init__(f"Device limit reached: {active_count}/{limit}")
        self.active_count = active_count
        self.limit = limit


def get_or_create_user_by_email(db: Session, email: str) -> User:
    """Найти юзера по email или создать Free."""
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized))
    now = utc_naive_now()
    if user is None:
        user = User(
            yandex_id=None,  # email-only, без OAuth
            email=normalized,
            display_name=normalized.split("@")[0],
            avatar_url=None,
            last_login_at=now,
            is_active=True,
        )
        db.add(user)
        db.flush()
        _create_free_subscription(db, user)
    else:
        user.last_login_at = now
    db.commit()
    db.refresh(user)
    return user


def attach_device_to_user(
    db: Session,
    user: User,
    *,
    fingerprint: str,
    device_name: str,
    platform: str,
    app_version: str,
    ip_masked: str | None = None,
):
    """Создать или обновить Device под этим email-user'ом."""
    existing = next(
        (d for d in device_service.list_active(db, user) if d.fingerprint == fingerprint),
        None,
    )
    if existing is None:
        active = device_service.list_active(db, user)
        if len(active) >= device_service.get_device_limit(user):
            raise DeviceLimitReached(len(active), device_service.get_device_limit(user))
    device, _ = device_service.register_or_update_device(
        db,
        user,
        fingerprint=fingerprint,
        name=device_name,
        platform=platform,
        app_version=app_version,
        ip_masked=ip_masked,
    )
    return device


def _create_free_subscription(db: Session, user: User) -> None:
    now = utc_naive_now()
    sub = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
        starts_at=now,
        ends_at=now + timedelta(days=365 * 100),
        auto_renew=False,
        early_adopter=False,
        price_locked_kopecks=0,
    )
    db.add(sub)
