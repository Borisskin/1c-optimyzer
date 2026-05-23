"""Payment — каждая YooKassa-транзакция (purchase Credits / Pro / recurring)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentPurpose(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    CREDITS = "credits"


class Payment(Base, UUIDPrimaryKey, TimestampMixin):
    """Одна оплата."""

    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    purpose: Mapped[PaymentPurpose] = mapped_column(
        Enum(PaymentPurpose, name="payment_purpose"),
        nullable=False,
    )
    package_or_plan: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_kopecks: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    confirmation_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")  # noqa: F821
