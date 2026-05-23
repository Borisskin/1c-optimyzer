"""License keys: один персональный ключ на юзера (OPTM-XXXX-XXXX-XXXX-XXXX).

Семантика:
- Ключ привязан к user_id навсегда (до regenerate)
- Переиспользуемый — юзер может активировать на нескольких устройствах
  (до device_limit, который зависит от тарифа: Free=1, Pro=5)
- Free / Pro статус определяется текущей подпиской — НЕ полем в ключе
- При regenerate — старый помечается is_used=True (используем как is_revoked)
  и больше не валиден, выдаётся новый

Поле LicenseKey.is_used сохраняем (миграция была бы), но семантика
изменилась с «использован 1 раз» на «отозван (после regenerate)».
"""

from __future__ import annotations

import random
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
    """Создать новый ключ (raw create — не проверяет существующие).

    Обычно вызывайте `get_or_create_active_key` или `regenerate_key` вместо этого.
    Прямой `issue_key` используется только webhook'ом оплаты для legacy совместимости.
    """
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


def get_active_key(db: Session, user: User) -> LicenseKey | None:
    """Найти текущий активный (не отозванный) ключ юзера."""
    return db.scalar(
        select(LicenseKey)
        .where(LicenseKey.user_id == user.id)
        .where(LicenseKey.is_used.is_(False))
    )


def get_or_create_active_key(db: Session, user: User) -> LicenseKey:
    """Если у юзера уже есть активный ключ — вернуть его, иначе создать новый."""
    existing = get_active_key(db, user)
    if existing:
        return existing
    return issue_key(db, user)


def regenerate_key(db: Session, user: User) -> LicenseKey:
    """Отозвать текущий ключ (если был) и выпустить новый."""
    current = get_active_key(db, user)
    if current:
        current.is_used = True
        current.used_at = datetime.utcnow()
        db.commit()
    return issue_key(db, user)


def lookup_key(db: Session, key: str) -> LicenseKey | None:
    """Найти ключ по строке. Не проверяет is_used — это делает caller."""
    return db.scalar(select(LicenseKey).where(LicenseKey.key == key.strip().upper()))
