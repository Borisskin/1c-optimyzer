"""Sprint 11 Phase D — тесты rate limiter для Force Refresh."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from services.rate_limiter import (
    PER_ITEM_COOLDOWN,
    PER_SESSION_LIMIT_PER_HOUR,
    PER_SESSION_WINDOW,
    ForceRefreshRateLimiter,
)


@pytest.fixture
def limiter() -> ForceRefreshRateLimiter:
    return ForceRefreshRateLimiter()


class TestPerItemCooldown:
    def test_first_refresh_allowed(self, limiter):
        status = limiter.check_and_record("k1")
        assert status.allowed is True
        assert status.per_item_remaining_seconds == 0

    def test_second_refresh_same_item_blocked(self, limiter):
        limiter.check_and_record("k1")
        status = limiter.check_and_record("k1")
        assert status.allowed is False
        assert status.reason == "per_item"
        assert 0 < status.per_item_remaining_seconds <= 300  # 5 min

    def test_different_keys_dont_block_each_other(self, limiter):
        limiter.check_and_record("k1")
        # Different key — allowed
        status = limiter.check_and_record("k2")
        assert status.allowed is True

    def test_per_item_recovers_after_cooldown(self, limiter):
        past = datetime.utcnow() - PER_ITEM_COOLDOWN - timedelta(seconds=1)
        limiter._per_item["k1"] = past
        status = limiter.check_and_record("k1", now=datetime.utcnow())
        assert status.allowed is True

    def test_check_doesnt_record(self, limiter):
        """check() БЕЗ записи — для UI polling."""
        status1 = limiter.check("k1")
        assert status1.allowed is True
        status2 = limiter.check("k1")
        assert status2.allowed is True  # всё ещё allowed (не записали)


class TestPerSessionCooldown:
    def test_under_limit_allowed(self, limiter):
        for i in range(PER_SESSION_LIMIT_PER_HOUR):
            status = limiter.check_and_record(f"k{i}")
            assert status.allowed is True

    def test_over_limit_blocked(self, limiter):
        for i in range(PER_SESSION_LIMIT_PER_HOUR):
            limiter.check_and_record(f"k{i}")
        # 11th refresh blocked
        status = limiter.check_and_record(f"k_extra")
        assert status.allowed is False
        assert status.reason == "per_session"

    def test_session_count_tracked(self, limiter):
        for i in range(5):
            limiter.check_and_record(f"k{i}")
        status = limiter.check("any_key")
        assert status.per_session_used == 5
        assert status.per_session_limit == 10

    def test_session_window_rolls(self, limiter):
        """Старые refreshes выходят из окна → новые allowed."""
        past = datetime.utcnow() - PER_SESSION_WINDOW - timedelta(seconds=1)
        # Заполняем 10 старыми entries
        for i in range(PER_SESSION_LIMIT_PER_HOUR):
            limiter._session.append(past)
        # Новый запрос — старые expired, должен быть allowed
        status = limiter.check_and_record("k_new", now=datetime.utcnow())
        assert status.allowed is True


class TestStatusReporting:
    def test_status_includes_all_fields(self, limiter):
        limiter.check_and_record("k1")
        status = limiter.check("k1")
        assert status.per_item_remaining_seconds > 0
        assert status.per_session_used == 1
        assert status.per_session_limit == 10
        assert status.per_session_remaining_seconds == 0  # not at limit yet

    def test_status_per_session_remaining_when_at_limit(self, limiter):
        for i in range(PER_SESSION_LIMIT_PER_HOUR):
            limiter.check_and_record(f"k{i}")
        status = limiter.check("any_key")
        assert status.allowed is False
        assert status.per_session_remaining_seconds > 0


class TestReset:
    def test_reset_clears_all(self, limiter):
        for i in range(5):
            limiter.check_and_record(f"k{i}")
        limiter.reset()
        # All slots fresh
        for i in range(5):
            status = limiter.check_and_record(f"k{i}")
            assert status.allowed is True


class TestRateLimiterApiIntegration:
    """Integration test через FastAPI endpoint."""

    def test_force_refresh_status_endpoint(self, client):
        from services.rate_limiter import get_rate_limiter

        # No history — allowed
        resp = client.get("/v1/ai/force_refresh_status/test_key")
        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert body["per_item_remaining_seconds"] == 0
        assert body["per_session_used"] == 0
        assert body["per_session_limit"] == 10

        # After recording → blocked
        limiter = get_rate_limiter()
        limiter.check_and_record("test_key")
        resp = client.get("/v1/ai/force_refresh_status/test_key")
        body = resp.json()
        assert body["allowed"] is False
        assert body["per_item_remaining_seconds"] > 0

    def test_explain_plan_force_refresh_rate_limited_429(self, client, monkeypatch):
        """Two force refreshes на same key → second returns 429."""
        from unittest.mock import AsyncMock, MagicMock
        import json

        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(
                json.dumps(
                    {
                        "summary": "ok",
                        "overall_severity": "Info",
                        "hotspots": [],
                        "recommendations": [],
                        "suggested_indexes": [],
                    },
                    ensure_ascii=False,
                )
            )
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic",
            lambda **_: mock_client,
        )

        req = {
            "sql_text": "SELECT 1",
            "plan_xml": "<ShowPlanXML/>",
            "plan_format": "xml",
            "engine": "mssql",
            "force_refresh": True,
        }
        # First force_refresh — allowed (consumes per-item slot)
        resp1 = client.post("/v1/ai/explain_plan", json=req)
        assert resp1.status_code == 200
        # Second force_refresh — blocked by per-item cooldown
        resp2 = client.post("/v1/ai/explain_plan", json=req)
        assert resp2.status_code == 429
        detail = resp2.json()["detail"]
        assert detail["error"] == "force_refresh_rate_limited"
        assert detail["reason"] == "per_item"


def _mock_response(text: str, model: str = "claude-haiku-4-5"):
    from unittest.mock import MagicMock

    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.model = model
    return resp
