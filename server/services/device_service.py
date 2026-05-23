"""Бизнес-логика для devices."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.settings import settings
from models.device import Device, DevicePlatform
from models.subscription import SubscriptionPlan
from models.user import User


def list_active(db: Session, user: User) -> list[Device]:
    return list(
        db.scalars(
            select(Device)
            .where(Device.user_id == user.id, Device.is_active.is_(True))
            .order_by(Device.last_seen_at.desc())
        )
    )


def get_device_limit(user: User) -> int:
    """Сколько устройств можно активировать одновременно."""
    sub = user.subscription
    if sub and sub.plan == SubscriptionPlan.PRO:
        return settings.device_limit_pro
    return settings.device_limit_free


def deactivate(db: Session, user: User, device_id: str) -> Device:
    """Деактивировать устройство юзера."""
    dev = db.get(Device, device_id)
    if dev is None or dev.user_id != user.id:
        raise LookupError("Device not found")
    dev.is_active = False
    db.commit()
    db.refresh(dev)
    return dev


def register_or_update_device(
    db: Session,
    user: User,
    *,
    fingerprint: str,
    name: str,
    platform: DevicePlatform,
    app_version: str,
    ip_masked: str | None = None,
) -> tuple[Device, bool]:
    """Создать новое или обновить существующее устройство.

    Returns (device, created_bool).
    Может бросить ValueError если превышен лимит устройств.
    """
    existing = db.scalar(
        select(Device).where(
            Device.user_id == user.id,
            Device.fingerprint == fingerprint,
        )
    )
    now = datetime.utcnow()
    if existing is not None:
        existing.name = name
        existing.platform = platform
        existing.app_version = app_version
        existing.last_seen_at = now
        existing.last_ip_masked = ip_masked
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing, False

    active_count = len(list_active(db, user))
    limit = get_device_limit(user)
    if active_count >= limit:
        raise ValueError(
            f"Device limit reached: {active_count}/{limit}. "
            "Деактивируйте старое устройство перед активацией нового."
        )

    device = Device(
        user_id=user.id,
        fingerprint=fingerprint,
        name=name,
        platform=platform,
        app_version=app_version,
        activated_at=now,
        last_seen_at=now,
        last_ip_masked=ip_masked,
        is_active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device, True


def heartbeat(db: Session, device: Device, *, app_version: str | None = None) -> Device:
    """Обновить last_seen_at."""
    device.last_seen_at = datetime.utcnow()
    if app_version:
        device.app_version = app_version
    db.commit()
    db.refresh(device)
    return device
