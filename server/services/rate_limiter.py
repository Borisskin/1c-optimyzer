"""Sprint 11 Phase D — Rate limiter для Force Refresh.

In-process state (не shared между uvicorn workers — в dev это OK).
Production / multi-worker — нужен Redis (Sprint 12+).

Cooldowns:
  - Per-item: 5 минут на конкретный cache_key (защищает от спам-кликов одного
    и того же AI ответа)
  - Per-session: 10 force refreshes / час total (защищает от distributed DoS
    через множество ключей)

Sergey's reasoning (Sprint 11 ADR-059):
- AI ответы при temperature=0 ~95% детерминистичны
- Force refresh — illusion of control, реально использовать 1-2 раза за сессию
- 5 мин — время чтения ответа + обдумывание нужен ли fresh
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


PER_ITEM_COOLDOWN = timedelta(minutes=5)
PER_SESSION_LIMIT_PER_HOUR = 10
PER_SESSION_WINDOW = timedelta(hours=1)


@dataclass
class RateLimitStatus:
    """Status для UI countdown."""

    allowed: bool
    per_item_remaining_seconds: int  # 0 если cooldown истёк
    per_session_used: int  # сколько раз использовалось в текущем окне
    per_session_limit: int  # максимум 10
    per_session_remaining_seconds: int  # сколько до сброса самого старого refresh
    reason: Optional[str] = None  # 'per_item' | 'per_session' | None если allowed


class ForceRefreshRateLimiter:
    """In-process rate limiter для Force Refresh операций."""

    def __init__(self):
        self._per_item: dict[str, datetime] = {}
        self._session: list[datetime] = []
        self._lock = threading.Lock()

    def check(self, cache_key: str, now: Optional[datetime] = None) -> RateLimitStatus:
        """Проверяет статус БЕЗ записи (для UI status endpoint)."""
        now = now or datetime.utcnow()
        with self._lock:
            return self._compute_status(cache_key, now)

    def check_and_record(
        self, cache_key: str, now: Optional[datetime] = None
    ) -> RateLimitStatus:
        """Проверяет статус И записывает использование если allowed."""
        now = now or datetime.utcnow()
        with self._lock:
            status = self._compute_status(cache_key, now)
            if status.allowed:
                self._per_item[cache_key] = now
                self._session.append(now)
            return status

    def _compute_status(self, cache_key: str, now: datetime) -> RateLimitStatus:
        """Внутренний расчёт. Caller держит lock."""
        # Cleanup expired session refreshes (rolling 1-hour window)
        cutoff = now - PER_SESSION_WINDOW
        self._session[:] = [t for t in self._session if t >= cutoff]

        # Per-item check
        last_refresh = self._per_item.get(cache_key)
        per_item_remaining = 0
        if last_refresh:
            elapsed = now - last_refresh
            if elapsed < PER_ITEM_COOLDOWN:
                per_item_remaining = int(
                    (PER_ITEM_COOLDOWN - elapsed).total_seconds()
                )

        # Per-session check
        per_session_used = len(self._session)
        per_session_remaining = 0
        if per_session_used >= PER_SESSION_LIMIT_PER_HOUR:
            oldest = min(self._session)
            per_session_remaining = int(
                (PER_SESSION_WINDOW - (now - oldest)).total_seconds()
            )

        # Determine allowed + reason
        if per_item_remaining > 0:
            return RateLimitStatus(
                allowed=False,
                per_item_remaining_seconds=per_item_remaining,
                per_session_used=per_session_used,
                per_session_limit=PER_SESSION_LIMIT_PER_HOUR,
                per_session_remaining_seconds=per_session_remaining,
                reason="per_item",
            )
        if per_session_used >= PER_SESSION_LIMIT_PER_HOUR:
            return RateLimitStatus(
                allowed=False,
                per_item_remaining_seconds=0,
                per_session_used=per_session_used,
                per_session_limit=PER_SESSION_LIMIT_PER_HOUR,
                per_session_remaining_seconds=per_session_remaining,
                reason="per_session",
            )
        return RateLimitStatus(
            allowed=True,
            per_item_remaining_seconds=0,
            per_session_used=per_session_used,
            per_session_limit=PER_SESSION_LIMIT_PER_HOUR,
            per_session_remaining_seconds=0,
            reason=None,
        )

    def reset(self) -> None:
        """Полный сброс — для тестов."""
        with self._lock:
            self._per_item.clear()
            self._session.clear()


# Singleton (process-wide state)
_global_limiter: Optional[ForceRefreshRateLimiter] = None
_singleton_lock = threading.Lock()


def get_rate_limiter() -> ForceRefreshRateLimiter:
    global _global_limiter
    if _global_limiter is None:
        with _singleton_lock:
            if _global_limiter is None:
                _global_limiter = ForceRefreshRateLimiter()
    return _global_limiter


def reset_rate_limiter_for_tests() -> ForceRefreshRateLimiter:
    """Полностью пересоздаёт singleton — для тестов."""
    global _global_limiter
    with _singleton_lock:
        _global_limiter = ForceRefreshRateLimiter()
        return _global_limiter
