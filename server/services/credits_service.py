"""Бизнес-логика для Credits пакетов."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.credits import PACKAGE_CONFIG, Credits, CreditsPackage
from models.user import User


def list_active_packages(db: Session, user: User) -> list[Credits]:
    """Активные пакеты юзера, отсортированные по expires_at (ближайшие к expiry — первыми).

    Тратим всегда из ближайшего к expiry — это минимизирует «прогоревшие» кредиты.
    """
    now = datetime.utcnow()
    stmt = (
        select(Credits)
        .where(
            Credits.user_id == user.id,
            Credits.is_active.is_(True),
            Credits.expires_at > now,
        )
        .order_by(Credits.expires_at.asc())
    )
    rows = db.scalars(stmt).all()
    # Отсеять полностью use'd
    return [r for r in rows if r.operations_remaining > 0]


def list_all_packages(db: Session, user: User) -> list[Credits]:
    """История покупок (без фильтра)."""
    return list(
        db.scalars(
            select(Credits)
            .where(Credits.user_id == user.id)
            .order_by(Credits.purchased_at.desc())
        )
    )


def total_remaining(db: Session, user: User) -> int:
    return sum(p.operations_remaining for p in list_active_packages(db, user))


def consume_credit(db: Session, user: User, amount: int = 1) -> Credits | None:
    """Списать `amount` операций из ближайшего к expiry пакета.

    Returns:
        Credits row из которого списали, или None если нет доступных.
    """
    for pkg in list_active_packages(db, user):
        if pkg.operations_remaining >= amount:
            pkg.operations_used += amount
            if pkg.operations_remaining == 0:
                pkg.is_active = False
            db.commit()
            db.refresh(pkg)
            return pkg
    return None


def grant_package(db: Session, user: User, package: CreditsPackage) -> Credits:
    """Создать новый Credits-ряд (вызывается из webhook YooKassa при успешной оплате)."""
    cfg = PACKAGE_CONFIG[package]
    now = datetime.utcnow()
    row = Credits(
        user_id=user.id,
        package=package,
        operations_total=cfg["operations"],
        operations_used=0,
        purchased_at=now,
        expires_at=now + timedelta(days=cfg["ttl_days"]),
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def deactivate_expired(db: Session) -> int:
    """Cron-task: помечаем expired пакеты is_active=False. Возвращает количество."""
    now = datetime.utcnow()
    rows = db.scalars(
        select(Credits).where(Credits.is_active.is_(True), Credits.expires_at <= now)
    ).all()
    for r in rows:
        r.is_active = False
    db.commit()
    return len(rows)
