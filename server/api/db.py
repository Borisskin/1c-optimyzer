"""SQLAlchemy engine + session factory.

Используем sync engine. Async добавим если упрёмся в перформанс (для запуска
вряд ли понадобится — FastAPI спокойно работает с sync БД через ThreadPool).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.settings import settings

# SQLite требует connect_args для thread-safety.
connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    echo=settings.debug and settings.env == "development",
    connect_args=connect_args,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — даёт сессию и закрывает её в конце запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
