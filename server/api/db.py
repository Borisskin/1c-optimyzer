"""SQLAlchemy engine + session factory.

Используем sync engine. Async добавим если упрёмся в перформанс (для запуска
вряд ли понадобится — FastAPI спокойно работает с sync БД через ThreadPool).
"""

from __future__ import annotations

from collections.abc import Generator

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.settings import PROJECT_ROOT, settings


def _resolve_database_url(url: str) -> str:
    """SQLite-URL с относительным путём резолвим от корня репо, не от CWD.

    Без этого uvicorn запущенный из `server/` ищет БД в `server/server/...`.
    PostgreSQL и абсолютные пути возвращаются как есть.
    """
    if not url.startswith("sqlite"):
        return url
    marker = ":///"
    idx = url.find(marker)
    if idx < 0:
        return url
    prefix = url[: idx + len(marker)]
    path = url[idx + len(marker) :]
    # Уже абсолютный (Linux: /var/..., Windows: D:/...) — не трогаем.
    if path.startswith("/") or (len(path) >= 2 and path[1] == ":"):
        return url
    if path.startswith("./"):
        path = path[2:]
    abs_path = (PROJECT_ROOT / path).resolve()
    return f"{prefix}{abs_path.as_posix()}"


# SQLite требует connect_args для thread-safety.
connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    _resolve_database_url(settings.database_url),
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
