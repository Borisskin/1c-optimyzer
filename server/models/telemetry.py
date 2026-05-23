"""TelemetryEvent — анонимные метрики использования.

НЕ привязываем к user_id для Free юзеров (только anonymous device_fingerprint).
Авто-cleanup >90 дней — через cron в services/scheduler.py.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, UUIDPrimaryKey


class TelemetryEvent(Base, UUIDPrimaryKey):
    """Одно событие телеметрии."""

    __tablename__ = "telemetry_events"

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        index=True,
        nullable=True,
    )
    device_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    app_version: Mapped[str] = mapped_column(String(32), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)

    # Категория и тип события. Категория — "tech" / "behavior" / "conversion".
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Произвольная payload (JSON). НЕ хранить SQL, имена БД, контексты —
    # см. privacy section в README.
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
