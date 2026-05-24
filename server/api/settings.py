"""Application settings via pydantic-settings.

Все значения тянутся из root `.env` (см. `<repo>/.env.example`). Один файл —
общий для всех компонентов (server / cabinet / frontend / desktop backend).

В тестах можно переопределять через monkeypatch или фикстуру `Settings()`
с явными аргументами.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень репозитория — два уровня вверх от server/api/settings.py.
# Делаем абсолютный путь, чтобы env читался независимо от cwd.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Global app settings."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "DEBUG"
    host: str = "127.0.0.1"
    port: int = 8001

    # --- Database ---
    database_url: str = "sqlite+pysqlite:///./optimyzer.db"

    # --- JWT ---
    jwt_secret: str = Field(
        default="dev-only-secret-NEVER-use-in-production-CHANGE-ME-LONG-RANDOM",
        min_length=32,
    )
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_days: int = 30
    jwt_device_ttl_days: int = 90
    jwt_algorithm: str = "HS256"

    # --- Yandex OAuth ---
    yandex_client_id: str = ""
    yandex_client_secret: str = ""
    # Должно СОВПАДАТЬ с тем что зарегистрировано в oauth.yandex.ru/client.
    # Дев: http://localhost:8001/success — uvicorn ловит callback напрямую
    # на :8001/success (routers/auth.py OAUTH_LANDING_PATH = "/success").
    yandex_redirect_uri: str = "http://localhost:8001/success"
    yandex_oauth_authorize_url: str = "https://oauth.yandex.ru/authorize"
    yandex_oauth_token_url: str = "https://oauth.yandex.ru/token"
    yandex_user_info_url: str = "https://login.yandex.ru/info"

    # --- YooKassa ---
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_webhook_secret: str = ""
    yookassa_return_url: str = "http://127.0.0.1:5173/credits?status=pending"

    # --- CORS ---
    cors_allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    # --- Email ---
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Optimyzer <hello@optimyzer.pro>"

    # --- Rate limiting ---
    rate_limit_authenticated: str = "100/minute"
    rate_limit_anonymous: str = "20/minute"

    # --- Admin ---
    admin_username: str = "admin"
    admin_password: str = "change-me"

    # --- Cookies ---
    cookie_secure: bool = False
    cookie_domain: str = ""
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # --- Soft caps ---
    free_ai_monthly_limit: int = 5
    pro_ai_monthly_soft_cap: int = 1000
    device_limit_free: int = 1
    device_limit_pro: int = 5

    # --- Sprint 6: Cloud AI orchestration ---
    anthropic_api_key: str = ""
    ai_model_default: str = "claude-sonnet-4-5-20250929"
    ai_model_business: str = "claude-opus-4-5-20250929"
    ai_max_tokens: int = 4000
    ai_request_timeout_s: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Кешируем — Settings() читает env_file каждый раз без кеша."""
    return Settings()


# Удобный singleton для импортов: `from api.settings import settings`
settings = get_settings()
