"""Base для всех SQLAlchemy моделей.

Используем DeclarativeBase (SQLAlchemy 2.x) + общий type-mapping.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


def gen_uuid() -> str:
    """UUID хранится как строка — кросс-совместимо с SQLite и PostgreSQL."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""

    # SQLite не умеет нативные UUID, поэтому используем String(36).
    # Для PostgreSQL можно потом перейти на UUID — Alembic мигрирует.


class TimestampMixin:
    """Стандартные created_at / updated_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKey:
    """UUID-primary key — строкой ради SQLite-совместимости."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
