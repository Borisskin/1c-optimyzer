"""YooKassa клиент — wrapper над `yookassa` SDK.

Гарантирует:
- Configuration выставлена один раз (shop_id + secret_key)
- Все запросы идут с idempotency_key
- Чеки 54-ФЗ формируются автоматически
- Webhook signature verification (если YooKassa включит подпись)

Sandbox: shop_id и secret_key — те же endpoints, разные креды.
Документация: https://yookassa.ru/developers/api
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from yookassa import Configuration, Payment as YooPayment

from api.settings import settings


def configure() -> None:
    """Вызывается один раз на старте приложения."""
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        # В dev/test без креденшелов — оставляем неконфигурированным.
        # Реальные вызовы тогда упадут в тестах через мок.
        return
    Configuration.configure(settings.yookassa_shop_id, settings.yookassa_secret_key)


# Конфигурация при импорте — удобно для prod, безопасно для dev (no-op).
configure()


@dataclass(slots=True)
class CreatedPayment:
    yookassa_payment_id: str
    confirmation_url: str
    raw: dict[str, Any]


def kopecks_to_rub_str(kopecks: int) -> str:
    """`29900` -> `"299.00"` — формат для YooKassa."""
    return f"{Decimal(kopecks) / Decimal(100):.2f}"


def build_receipt(
    *,
    email: str,
    description: str,
    amount_kopecks: int,
    item_subject: str = "service",
) -> dict[str, Any]:
    """Чек 54-ФЗ. vat_code=1 — без НДС (для самозанятых)."""
    return {
        "customer": {"email": email},
        "items": [
            {
                "description": description,
                "quantity": "1",
                "amount": {
                    "value": kopecks_to_rub_str(amount_kopecks),
                    "currency": "RUB",
                },
                "vat_code": 1,
                "payment_subject": item_subject,
                "payment_mode": "full_prepayment",
            }
        ],
    }


def is_configured() -> bool:
    return bool(settings.yookassa_shop_id and settings.yookassa_secret_key)


def _stub_create(*, idempotency_key: str, **kwargs) -> CreatedPayment:
    """Fallback для dev/test когда YooKassa не настроен.

    Возвращает stub confirmation_url чтобы фронт мог продолжать flow в demo-режиме.
    Чек/webhook симулирует Сергей вручную (или через test helper).
    """
    return CreatedPayment(
        yookassa_payment_id=f"stub-{idempotency_key[:10]}",
        confirmation_url=f"https://yookassa.example/stub-checkout/{idempotency_key}",
        raw={"status": "pending", "stub": True},
    )


def create_payment(
    *,
    idempotency_key: str,
    amount_kopecks: int,
    description: str,
    user_email: str,
    metadata: dict[str, Any],
    save_payment_method: bool = False,
    return_url: str | None = None,
) -> CreatedPayment:
    """Создать платёж в YooKassa.

    Если креды не настроены (dev) — возвращает stub.
    """
    if not is_configured():
        return _stub_create(idempotency_key=idempotency_key)

    payload = {
        "amount": {
            "value": kopecks_to_rub_str(amount_kopecks),
            "currency": "RUB",
        },
        "description": description,
        "metadata": metadata,
        "save_payment_method": save_payment_method,
        "confirmation": {
            "type": "redirect",
            "return_url": return_url or settings.yookassa_return_url,
        },
        "receipt": build_receipt(
            email=user_email,
            description=description,
            amount_kopecks=amount_kopecks,
        ),
        "capture": True,
    }
    raw_payment = YooPayment.create(payload, idempotency_key)
    raw_dict = raw_payment.__dict__ if hasattr(raw_payment, "__dict__") else dict(raw_payment)
    confirmation_url = ""
    if hasattr(raw_payment, "confirmation") and raw_payment.confirmation:
        confirmation_url = getattr(raw_payment.confirmation, "confirmation_url", "") or ""
    return CreatedPayment(
        yookassa_payment_id=raw_payment.id,
        confirmation_url=confirmation_url,
        raw=raw_dict,
    )


def create_recurring_payment(
    *,
    idempotency_key: str,
    payment_method_id: str,
    amount_kopecks: int,
    description: str,
    user_email: str,
    metadata: dict[str, Any],
) -> CreatedPayment:
    """Autopayment по сохранённой карте (без подтверждения юзера).

    Используется в cron для Pro подписок.
    """
    if not is_configured():
        return _stub_create(idempotency_key=idempotency_key)

    payload = {
        "amount": {
            "value": kopecks_to_rub_str(amount_kopecks),
            "currency": "RUB",
        },
        "description": description,
        "metadata": metadata,
        "payment_method_id": payment_method_id,
        "receipt": build_receipt(
            email=user_email,
            description=description,
            amount_kopecks=amount_kopecks,
        ),
        "capture": True,
    }
    raw_payment = YooPayment.create(payload, idempotency_key)
    raw_dict = raw_payment.__dict__ if hasattr(raw_payment, "__dict__") else dict(raw_payment)
    return CreatedPayment(
        yookassa_payment_id=raw_payment.id,
        confirmation_url="",
        raw=raw_dict,
    )
