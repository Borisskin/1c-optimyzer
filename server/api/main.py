"""FastAPI app entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api import __version__
from api.routers import auth, credits, dashboard, devices, subscriptions, usage
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

    # CORS — только для cabinet и landing.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limit.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Роутеры.
    app.include_router(auth.router)
    app.include_router(subscriptions.router)
    app.include_router(credits.router)
    app.include_router(devices.router)
    app.include_router(usage.router)
    app.include_router(dashboard.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "env": settings.env}

    return app


app = create_app()
