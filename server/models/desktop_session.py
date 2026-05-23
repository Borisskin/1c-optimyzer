"""DesktopSession — short-lived сессия активации desktop приложения.

Device flow (как Apple TV / GitHub CLI):
1. Desktop при «Войти через Yandex» → POST /v1/license/desktop-init →
   server создаёт DesktopSession (status='pending'), возвращает session_id.
2. Desktop открывает в browser cabinet/desktop-activate?session=SESSION_ID
3. Cabinet после OAuth login → POST /v1/license/desktop-confirm с session_id →
   server связывает с user'ом, создаёт Device + JWT, status='confirmed'.
4. Desktop polling'ом GET /v1/license/desktop-poll?session=SESSION_ID каждые
   2 сек — когда confirmed, отдаёт access_token + user info.
5. Desktop сохраняет token, заходит в основной UI.

Без копи-паста ключей, без deep link.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, UUIDPrimaryKey


class DesktopSessionStatus(str, enum.Enum):
    PENDING = "pending"          # ждёт OAuth + confirm
    CONFIRMED = "confirmed"      # связана с user, token выдан
    CLAIMED = "claimed"          # desktop забрал token через polling
    EXPIRED = "expired"          # >10 минут — выкинута
    CANCELLED = "cancelled"      # юзер отменил в cabinet


class DesktopSession(Base, UUIDPrimaryKey):
    """Сессия активации desktop через cabinet."""

    __tablename__ = "desktop_sessions"

    fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    app_version: Mapped[str] = mapped_column(String(32), nullable=False)

    status: Mapped[DesktopSessionStatus] = mapped_column(
        Enum(DesktopSessionStatus, name="desktop_session_status"),
        nullable=False,
        default=DesktopSessionStatus.PENDING,
    )

    # Заполняется при confirm.
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("devices.id"),
        nullable=True,
    )
    issued_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
