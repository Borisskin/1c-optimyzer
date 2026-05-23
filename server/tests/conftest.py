"""Общие фикстуры для тестов сервера."""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

# Подменяем env-переменные ДО импорта settings — pydantic-settings читает .env в момент первого импорта.
os.environ["ENV"] = "development"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-only-secret-must-be-at-least-32-characters-long-yes-this-one-is"
os.environ["YANDEX_CLIENT_ID"] = "test-client-id"
os.environ["YANDEX_CLIENT_SECRET"] = "test-client-secret"
os.environ["YANDEX_REDIRECT_URI"] = "http://testserver/oauth/callback"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://testserver"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import db as db_module
from api.db import get_db
from api.main import create_app
from models import Base

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


# Каждый тест получает свежую in-memory БД — fastest и изолированно.
@pytest.fixture()
def test_engine():
    # StaticPool — единое соединение для всех сессий. Без него каждая сессия
    # к `:memory:` SQLite получает свою БД (in-memory SQLite per-connection),
    # и тесты ломаются: create_all создаёт таблицы в одной БД, get_db ходит в другую.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Generator["Session", None, None]:
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(test_engine, db_session) -> "FastAPI":
    """FastAPI app с переопределённой DB dependency."""
    app = create_app()

    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # Подмена и module-level singleton — на случай если что-то импортит SessionLocal напрямую.
    db_module.SessionLocal = SessionLocal  # type: ignore[assignment]
    return app


@pytest.fixture()
def client(app) -> "TestClient":
    from fastapi.testclient import TestClient

    return TestClient(app)
