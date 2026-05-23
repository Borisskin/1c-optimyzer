"""Subscription — Free / Pro."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"           # списание не прошло, ждём 7 дней
    CANCELLED = "cancelled"         # auto_renew=false, действует до ends_at
    EXPIRED = "expired"             # past ends_at, ничего не работает


class Subscription(Base, UUIDPrimaryKey, TimestampMixin):
    """Одна подписка на юзера."""

    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_subscription_user"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, name="subscription_plan"),
        nullable=False,
        default=SubscriptionPlan.FREE,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    early_adopter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_locked_kopecks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    yookassa_payment_method_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    yookassa_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscription")  # noqa: F821

    @property
    def is_pro_active(self) -> bool:
        return (
            self.plan == SubscriptionPlan.PRO
            and self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED)
            and self.ends_at > datetime.utcnow()
        )
