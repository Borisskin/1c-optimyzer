"""Helper functions для тестов — создать юзера, выписать ему access token и т.п."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User
from services.auth_service import get_or_create_user_from_yandex
from services.jwt_service import create_access_token, create_device_token
from services.yandex_oauth import YandexProfile


def make_user(db: Session, **profile_overrides) -> User:
    """Создать юзера через стандартный auth_service path (с Free подпиской)."""
    base = dict(
        yandex_id=profile_overrides.pop("yandex_id", "ya-1"),
        email=profile_overrides.pop("email", "user@yandex.ru"),
        display_name=profile_overrides.pop("display_name", "Test User"),
        avatar_url=profile_overrides.pop("avatar_url", None),
    )
    profile = YandexProfile(**base)
    return get_or_create_user_from_yandex(db, profile)


def upgrade_to_pro(db: Session, user: User, *, days: int = 30) -> None:
    """Перевести юзера на Pro для тестов."""
    sub = user.subscription
    assert sub is not None, "User must already have a Free sub (auto-created on first login)"
    sub.plan = SubscriptionPlan.PRO
    sub.status = SubscriptionStatus.ACTIVE
    sub.starts_at = datetime.utcnow()
    sub.ends_at = datetime.utcnow() + timedelta(days=days)
    sub.auto_renew = True
    sub.price_locked_kopecks = 299000
    db.commit()
    db.refresh(sub)


def access_cookies_for(user: User) -> dict[str, str]:
    """Готовый dict cookies для TestClient (access_token cookie)."""
    return {"access_token": create_access_token(user_id=user.id)}


def device_token_for(user: User, device_id: str) -> str:
    return create_device_token(user_id=user.id, device_id=device_id)
