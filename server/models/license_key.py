"""LicenseKey — одноразовый ключ активации Pro в desktop.

Генерируется при успешной оплате Pro. Юзер получает на email. При активации
в desktop приходит на /v1/license/activate, привязывается к user_id + device.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class LicenseKey(Base, UUIDPrimaryKey, TimestampMixin):
    """Activation key (формат OPTM-XXXX-XXXX-XXXX-XXXX)."""

    __tablename__ = "license_keys"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_device_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("devices.id"),
        nullable=True,
    )
    issued_for_payment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("payments.id"),
        nullable=True,
    )

    user: Mapped["User"] = relationship()  # noqa: F821
