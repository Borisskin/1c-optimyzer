"""Device flow для активации desktop приложения через cabinet.

См. models/desktop_session.py — описание flow.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.settings import settings
from models.desktop_session import DesktopSession, DesktopSessionStatus
from models.user import User
from services import device_service
from services.auth_service import mask_ip, utc_naive_now
from services.jwt_service import create_device_token

SESSION_TTL_MINUTES = 10


class DeviceLimitReached(Exception):
    """Подкласс — для возврата 409 с активными устройствами."""

    def __init__(self, active_count: int, limit: int) -> None:
        super().__init__(f"Device limit reached: {active_count}/{limit}")
        self.active_count = active_count
        self.limit = limit


def init_session(
    db: Session,
    *,
    fingerprint: str,
    device_name: str,
    platform: str,
    app_version: str,
) -> DesktopSession:
    """Desktop вызывает на старте «Войти через Yandex» — создаём pending сессию."""
    now = utc_naive_now()
    session = DesktopSession(
        fingerprint=fingerprint,
        device_name=device_name,
        platform=platform,
        app_version=app_version,
        status=DesktopSessionStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(minutes=SESSION_TTL_MINUTES),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def confirm_session(
    db: Session,
    session_id: str,
    user: User,
    *,
    ip: str | None = None,
) -> DesktopSession:
    """Cabinet вызывает после login юзера — связываем session с user'ом и создаём Device.

    Raises:
        LookupError: если сессия не найдена / истекла / уже использована
        DeviceLimitReached: если у юзера уже max устройств
    """
    session = db.get(DesktopSession, session_id)
    if session is None:
        raise LookupError("desktop session not found")
    if session.expires_at <= utc_naive_now():
        session.status = DesktopSessionStatus.EXPIRED
        db.commit()
        raise LookupError("desktop session expired")
    if session.status != DesktopSessionStatus.PENDING:
        # Уже confirmed/claimed/cancelled — нечего делать.
        return session

    # Создаём или обновляем Device.
    active = device_service.list_active(db, user)
    has_this_fp = any(d.fingerprint == session.fingerprint for d in active)
    if not has_this_fp and len(active) >= device_service.get_device_limit(user):
        raise DeviceLimitReached(len(active), device_service.get_device_limit(user))

    ip_masked = mask_ip(ip)
    device, _ = device_service.register_or_update_device(
        db,
        user,
        fingerprint=session.fingerprint,
        name=session.device_name,
        platform=session.platform,
        app_version=session.app_version,
        ip_masked=ip_masked,
    )

    token = create_device_token(user_id=user.id, device_id=device.id)

    session.user_id = user.id
    session.device_id = device.id
    session.issued_access_token = token
    session.status = DesktopSessionStatus.CONFIRMED
    session.confirmed_at = utc_naive_now()
    db.commit()
    db.refresh(session)
    return session


def poll_session(db: Session, session_id: str) -> DesktopSession | None:
    """Desktop polling'ом проверяет статус. Если confirmed — отдаёт токен и
    помечает claimed (чтобы не отдать дважды)."""
    session = db.get(DesktopSession, session_id)
    if session is None:
        return None
    if session.expires_at <= utc_naive_now() and session.status == DesktopSessionStatus.PENDING:
        session.status = DesktopSessionStatus.EXPIRED
        db.commit()
        return session
    return session


def claim_session(db: Session, session_id: str) -> DesktopSession | None:
    """Пометить session как claimed после того как desktop забрал token."""
    session = db.get(DesktopSession, session_id)
    if session and session.status == DesktopSessionStatus.CONFIRMED:
        session.status = DesktopSessionStatus.CLAIMED
        session.claimed_at = utc_naive_now()
        db.commit()
        db.refresh(session)
    return session


def cleanup_expired(db: Session) -> int:
    """Помечает истёкшие сессии. Возвращает количество. Запускается из cron."""
    now = utc_naive_now()
    rows = db.scalars(
        select(DesktopSession).where(
            DesktopSession.status == DesktopSessionStatus.PENDING,
            DesktopSession.expires_at <= now,
        )
    ).all()
    for s in rows:
        s.status = DesktopSessionStatus.EXPIRED
    db.commit()
    return len(rows)
