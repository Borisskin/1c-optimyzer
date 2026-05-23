"""User — две дороги: email-only (desktop) или Yandex OAuth (cabinet)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey, TimestampMixin):
    """Пользователь.

    Identity ─ email (всегда). yandex_id опционально — заполняется когда юзер
    логинится в cabinet через Yandex OAuth. Desktop-юзеры создаются только
    с email (без yandex_id) через /v1/license/lookup-by-email.
    """

    __tablename__ = "users"

    # Заполняется только при Yandex OAuth (cabinet). Desktop-юзеры — NULL.
    yandex_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # связи — string-references чтобы не получить циркулярный импорт
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscription: Mapped["Subscription | None"] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    credits: Mapped[list["Credits"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
    devices: Mapped[list["Device"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
    usage_records: Mapped[list["Usage"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
