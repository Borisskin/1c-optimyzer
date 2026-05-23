"""Auth use-cases — поверх моделей и Yandex client.

Логика «как из Yandex callback'а получить юзера в БД» живёт здесь, а не в
роутерах. Роутер просто вызывает функцию из этого модуля.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.refresh_token import RefreshToken
from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User
from services.jwt_service import create_refresh_token, hash_token
from services.yandex_oauth import YandexProfile


def utc_naive_now() -> datetime:
    """Naive UTC datetime — единственный способ хранения времени в БД.

    SQLite не помнит timezone, PostgreSQL — помнит. Чтобы код работал
    одинаково в обоих — все sources и compare'ы в UTC naive.
    """
    return datetime.utcnow()


def get_or_create_user_from_yandex(
    db: Session,
    profile: YandexProfile,
) -> User:
    """Создать новую запись юзера или обновить существующую."""
    user = db.scalar(select(User).where(User.yandex_id == profile.yandex_id))
    now = utc_naive_now()
    if user is None:
        user = User(
            yandex_id=profile.yandex_id,
            email=profile.email,
            display_name=profile.display_name,
            avatar_url=profile.avatar_url,
            last_login_at=now,
            is_active=True,
        )
        db.add(user)
        db.flush()
        _create_default_free_subscription(db, user)
    else:
        user.email = profile.email
        if profile.display_name:
            user.display_name = profile.display_name
        if profile.avatar_url:
            user.avatar_url = profile.avatar_url
        user.last_login_at = now
    db.commit()
    db.refresh(user)
    return user


def issue_refresh_token(
    db: Session,
    user: User,
    *,
    user_agent: str | None = None,
    ip_masked: str | None = None,
) -> str:
    """Создать новый refresh token и сохранить хеш в БД. Возвращает plaintext."""
    plain, token_hash, expires_at = create_refresh_token(user_id=user.id)
    record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=utc_naive_now(),
        user_agent=user_agent[:500] if user_agent else None,
        ip_address_masked=ip_masked,
    )
    db.add(record)
    db.commit()
    return plain


def rotate_refresh_token(db: Session, presented_plain: str) -> tuple[User, str]:
    """Валидировать старый refresh, отозвать его, выпустить новый.

    Returns:
        (user, new_plaintext_refresh_token)
    Raises:
        ValueError: если токен не найден / истёк / уже отозван
    """
    presented_hash = hash_token(presented_plain)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == presented_hash))
    if record is None:
        raise ValueError("Refresh token not recognised")
    if record.revoked_at is not None:
        raise ValueError("Refresh token already revoked")
    if record.expires_at <= utc_naive_now():
        raise ValueError("Refresh token expired")
    record.revoked_at = utc_naive_now()
    user = record.user
    new_plain = issue_refresh_token(
        db,
        user,
        user_agent=record.user_agent,
        ip_masked=record.ip_address_masked,
    )
    return user, new_plain


def revoke_refresh_token(db: Session, presented_plain: str) -> None:
    """Logout: помечаем refresh как revoked."""
    presented_hash = hash_token(presented_plain)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == presented_hash))
    if record and record.revoked_at is None:
        record.revoked_at = utc_naive_now()
        db.commit()


def mask_ip(ip: str | None) -> str | None:
    """`192.168.10.42` -> `192.168.×××.42` — для логов и истории refresh tokens.

    Не-IPv4 строки возвращаются как None (не пытаемся «маскировать» что попало).
    """
    if not ip:
        return None
    parts = ip.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return f"{parts[0]}.{parts[1]}.×××.{parts[3]}"
    return None


def _create_default_free_subscription(db: Session, user: User) -> None:
    """Каждому новому юзеру — Free подписка без срока действия (фактически)."""
    now = utc_naive_now()
    sub = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
        starts_at=now,
        # Free — формально не истекает; ставим далеко в будущее.
        ends_at=now.replace(year=now.year + 100),
        auto_renew=False,
        early_adopter=False,
        price_locked_kopecks=0,
    )
    db.add(sub)
