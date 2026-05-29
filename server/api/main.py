"""FastAPI app entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api import __version__
from api.routers import (
    admin,
    ai,
    auth,
    credits,
    dashboard,
    devices,
    subscriptions,
    telemetry,
    usage,
    webhooks,
)
from api.routers import (
    config as config_router,
)
from api.routers import (
    license as license_router,
)
from api.settings import settings

logger = logging.getLogger("optimyzer.server")
logging.basicConfig(level=settings.log_level)


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_anonymous],
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Optimyzer API",
        version=__version__,
        description="Backend для web-кабинета, auth, billing, license activation.",
        debug=settings.debug,
    )

    # CORS: cabinet + landing + Tauri webview (desktop).
    # Tauri даёт origin `http://tauri.localhost` (Windows) или `tauri://localhost`
    # (старые версии). Разрешаем regex'ом, плюс явные cabinet/landing origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=r"^(https?|tauri)://(localhost|127\.0\.0\.1|tauri\.localhost)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limit.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Роутеры.
    app.include_router(auth.router)
    app.include_router(auth.oauth_landing_router)  # /success — Yandex OAuth callback
    app.include_router(subscriptions.router)
    app.include_router(credits.router)
    app.include_router(devices.router)
    app.include_router(usage.router)
    app.include_router(dashboard.router)
    app.include_router(license_router.router)
    app.include_router(telemetry.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)
    app.include_router(ai.router)  # Sprint 6 — /v1/ai/explain
    app.include_router(config_router.public_router)  # S13 — GET /v1/config (desktop)
    app.include_router(config_router.admin_config_router)  # S13 — /v1/admin/config

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "env": settings.env}

    @app.on_event("startup")
    def _start_scheduler() -> None:
        # В тестах ENV=development и scheduler нам не нужен — он мешает.
        # В проде явно включаем через env var ENABLE_SCHEDULER=1 (см. settings).
        # Сейчас оставляем выключенным по умолчанию — включим в Phase 1.6 + deploy.
        if settings.env != "production":
            return
        from services.scheduler import start
        start()

    @app.on_event("shutdown")
    def _stop_scheduler() -> None:
        if settings.env != "production":
            return
        from services.scheduler import stop
        stop()

    return app


app = create_app()
