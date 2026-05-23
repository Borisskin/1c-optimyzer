"""Usage — каждая AI-операция."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, UUIDPrimaryKey


class UsageOperationType(str, enum.Enum):
    AI_EXPLANATION = "ai_explanation"
    AI_DEADLOCK_EXPLANATION = "ai_deadlock_explanation"
    AI_REWRITE = "ai_rewrite"
    AI_SLOW_QUERY_EXPLANATION = "ai_slow_query_explanation"


class UsageBilledAgainst(str, enum.Enum):
    FREE_QUOTA = "free_quota"
    PRO_QUOTA = "pro_quota"
    CREDITS_BALANCE = "credits_balance"


class Usage(Base, UUIDPrimaryKey):
    """Один аудит-запис об AI-операции."""

    __tablename__ = "usage"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("devices.id"),
        index=True,
        nullable=True,
    )
    operation_type: Mapped[UsageOperationType] = mapped_column(
        Enum(UsageOperationType, name="usage_operation_type"),
        nullable=False,
    )
    archive_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    cost_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    billed_against: Mapped[UsageBilledAgainst] = mapped_column(
        Enum(UsageBilledAgainst, name="usage_billed_against"),
        nullable=False,
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Cost-tracking — нам для расчёта маржи, юзеру не показываем.
    ai_tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="usage_records")  # noqa: F821
    device: Mapped["Device | None"] = relationship(back_populates="usage_records")  # noqa: F821
