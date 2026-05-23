"""Credits — пакеты разовых AI-операций (Mini/Standard/Bulk)."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class CreditsPackage(str, enum.Enum):
    MINI = "mini"           # 30 операций
    STANDARD = "standard"   # 100 операций
    BULK = "bulk"           # 300 операций


# Конфиг пакетов — единый источник истины. Цена / лимит / TTL.
PACKAGE_CONFIG: dict[CreditsPackage, dict[str, int]] = {
    CreditsPackage.MINI: {"operations": 30, "price_kopecks": 29900, "ttl_days": 30},
    CreditsPackage.STANDARD: {"operations": 100, "price_kopecks": 99000, "ttl_days": 30},
    CreditsPackage.BULK: {"operations": 300, "price_kopecks": 249000, "ttl_days": 30},
}


class Credits(Base, UUIDPrimaryKey, TimestampMixin):
    """Один пакет — один ряд. Тратится монотонно через `operations_used`."""

    __tablename__ = "credits"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    package: Mapped[CreditsPackage] = mapped_column(
        Enum(CreditsPackage, name="credits_package"),
        nullable=False,
    )
    operations_total: Mapped[int] = mapped_column(Integer, nullable=False)
    operations_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship(back_populates="credits")  # noqa: F821

    @property
    def operations_remaining(self) -> int:
        return max(self.operations_total - self.operations_used, 0)

    @property
    def is_available(self) -> bool:
        return (
            self.is_active
            and self.operations_remaining > 0
            and self.expires_at > datetime.utcnow()
        )
