"""Генерация и валидация license keys в формате OPTM-XXXX-XXXX-XXXX-XXXX."""

from __future__ import annotations

import random
import string
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.license_key import LicenseKey
from models.payment import Payment
from models.user import User

# 4 группы по 4 символа: цифры и заглавные латинские без 0/O/I/1 для читаемости.
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_key() -> str:
    """`OPTM-XXXX-XXXX-XXXX-XXXX`."""
    groups = [
        "".join(random.choices(ALPHABET, k=4)) for _ in range(4)  # noqa: S311 — не cryptosec
    ]
    return "OPTM-" + "-".join(groups)


def issue_key(db: Session, user: User, *, payment: Payment | None = None) -> LicenseKey:
    """Создать новый ключ для юзера (вызывается webhook'ом при успешной оплате Pro)."""
    # 5 попыток на случай collision — практически невозможно при таком алфавите.
    for _ in range(5):
        candidate = generate_key()
        if not db.scalar(select(LicenseKey).where(LicenseKey.key == candidate)):
            break
    else:
        raise RuntimeError("Не удалось сгенерировать уникальный ключ за 5 попыток")

    record = LicenseKey(
        user_id=user.id,
        key=candidate,
        is_used=False,
        issued_for_payment_id=payment.id if payment else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def consume_key(db: Session, key: str, *, device_id: str) -> LicenseKey:
    """Пометить ключ использованным.

    Raises:
        LookupError: ключ не найден или уже использован.
    """
    record = db.scalar(select(LicenseKey).where(LicenseKey.key == key))
    if record is None:
        raise LookupError("License key not found")
    if record.is_used:
        raise LookupError("License key already used")
    record.is_used = True
    record.used_at = datetime.utcnow()
    record.used_by_device_id = device_id
    db.commit()
    db.refresh(record)
    return record


def lookup_key(db: Session, key: str) -> LicenseKey | None:
    return db.scalar(select(LicenseKey).where(LicenseKey.key == key))
