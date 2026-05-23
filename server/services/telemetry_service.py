"""Бизнес-логика телеметрии — приём, агрегация, cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from models.telemetry import TelemetryEvent
from models.user import User
from schemas.telemetry import (
    TelemetryEventIn,
    TelemetrySummary,
    TelemetrySummaryRow,
)


def record_batch(
    db: Session,
    events: list[TelemetryEventIn],
    *,
    user: User | None = None,
) -> int:
    """Сохранить batch событий.

    Если user is None — anonymous (Free pre-activation). user_id не пишем.
    """
    now = datetime.utcnow()
    rows = [
        TelemetryEvent(
            user_id=user.id if user else None,
            device_fingerprint=e.device_fingerprint,
            app_version=e.app_version,
            platform=e.platform,
            category=e.category,
            event_type=e.event_type,
            payload=e.payload,
            timestamp=e.timestamp,
            received_at=now,
        )
        for e in events
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)


def cleanup_old_events(db: Session, *, max_age_days: int = 90) -> int:
    """Удалить события старше max_age_days. Возвращает количество удалённых."""
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    stmt = delete(TelemetryEvent).where(TelemetryEvent.timestamp < cutoff)
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)


def summarize(db: Session, *, period_days: int = 30) -> TelemetrySummary:
    """Aggregate metrics за последние period_days дней для /v1/admin."""
    start = datetime.utcnow() - timedelta(days=period_days)

    total = int(
        db.scalar(
            select(func.count(TelemetryEvent.id)).where(TelemetryEvent.timestamp >= start)
        )
        or 0
    )
    unique_devices = int(
        db.scalar(
            select(func.count(func.distinct(TelemetryEvent.device_fingerprint))).where(
                TelemetryEvent.timestamp >= start
            )
        )
        or 0
    )

    def _top(column, limit: int = 20) -> list[TelemetrySummaryRow]:
        rows = db.execute(
            select(column, func.count(TelemetryEvent.id))
            .where(TelemetryEvent.timestamp >= start)
            .group_by(column)
            .order_by(func.count(TelemetryEvent.id).desc())
            .limit(limit)
        ).all()
        return [TelemetrySummaryRow(key=str(k), count=int(c)) for k, c in rows]

    return TelemetrySummary(
        period_days=period_days,
        total_events=total,
        unique_devices=unique_devices,
        by_category=_top(TelemetryEvent.category, 10),
        by_event_type=_top(TelemetryEvent.event_type, 30),
        by_app_version=_top(TelemetryEvent.app_version, 10),
        by_platform=_top(TelemetryEvent.platform, 10),
    )
