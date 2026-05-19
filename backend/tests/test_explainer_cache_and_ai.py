"""Sprint 3 Phase F — explainer cache + AI client tests.

AI live-API tests skipped если нет ANTHROPIC_API_KEY в env (по умолчанию).
Cache tests работают без сети.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from optimyzer_backend.explainer.cache import ExplainerCache, make_cache_key
from optimyzer_backend.explainer.claude_client import (
    ClaudeExplainerClient,
    _summarize_for_prompt,
)


# ---------- Cache ----------


def test_cache_key_deterministic() -> None:
    k1 = make_cache_key("arc-1", "deadlock", "104")
    k2 = make_cache_key("arc-1", "deadlock", "104")
    k3 = make_cache_key("arc-1", "deadlock", "105")
    assert k1 == k2
    assert k1 != k3


def test_cache_put_get_roundtrip(tmp_path: Path) -> None:
    cache = ExplainerCache(tmp_path / "cache.db")
    cache.put(
        cache_key="abc",
        archive_id="arc-1",
        anatomy_kind="deadlock",
        target_id="104",
        rule_id="deadlock_lock_escalation",
        ai_text="AI explanation text",
        model="claude-sonnet-4-6",
        tokens_in=120,
        tokens_out=300,
    )
    entry = cache.get("abc")
    assert entry is not None
    assert entry.ai_text == "AI explanation text"
    assert entry.rule_id == "deadlock_lock_escalation"
    assert entry.tokens_in == 120


def test_cache_get_missing_returns_none(tmp_path: Path) -> None:
    cache = ExplainerCache(tmp_path / "cache.db")
    assert cache.get("nonexistent") is None


def test_cache_replace_overwrites(tmp_path: Path) -> None:
    cache = ExplainerCache(tmp_path / "cache.db")
    cache.put(
        cache_key="abc",
        archive_id="arc-1",
        anatomy_kind="deadlock",
        target_id="104",
        rule_id=None,
        ai_text="v1",
        model="m1",
        tokens_in=10,
        tokens_out=20,
    )
    cache.put(
        cache_key="abc",
        archive_id="arc-1",
        anatomy_kind="deadlock",
        target_id="104",
        rule_id=None,
        ai_text="v2",
        model="m2",
        tokens_in=50,
        tokens_out=80,
    )
    entry = cache.get("abc")
    assert entry is not None
    assert entry.ai_text == "v2"
    assert entry.model == "m2"


def test_cache_evict_by_archive(tmp_path: Path) -> None:
    cache = ExplainerCache(tmp_path / "cache.db")
    for i in range(3):
        cache.put(
            cache_key=f"k{i}",
            archive_id="arc-A",
            anatomy_kind="deadlock",
            target_id=str(i),
            rule_id=None,
            ai_text="x",
            model="m",
            tokens_in=0,
            tokens_out=0,
        )
    cache.put(
        cache_key="other",
        archive_id="arc-B",
        anatomy_kind="deadlock",
        target_id="9",
        rule_id=None,
        ai_text="y",
        model="m",
        tokens_in=0,
        tokens_out=0,
    )
    assert cache.evict_archive("arc-A") == 3
    assert cache.get("k0") is None
    assert cache.get("other") is not None


def test_cache_stats(tmp_path: Path) -> None:
    cache = ExplainerCache(tmp_path / "cache.db")
    assert cache.stats() == {"entries": 0}
    cache.put(
        cache_key="k", archive_id="arc", anatomy_kind="deadlock", target_id="1",
        rule_id=None, ai_text="x", model="m", tokens_in=0, tokens_out=0,
    )
    assert cache.stats() == {"entries": 1}


# ---------- Client (without network) ----------


def test_client_disabled_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = ClaudeExplainerClient(api_key="")
    assert c.enabled is False
    result = c.generate(anatomy_kind="deadlock", anatomy_data={"x": 1})
    assert result.ok is False
    assert result.error is not None
    assert "AI not configured" in result.error


def test_summarize_truncates_long_strings() -> None:
    long_str = "x" * 1000
    out = _summarize_for_prompt({"sql": long_str}, max_str_len=100)
    assert len(out["sql"]) <= 102  # 100 + ellipsis "…"
    assert out["sql"].endswith("…")


def test_summarize_truncates_long_lists() -> None:
    out = _summarize_for_prompt({"items": list(range(50))})
    assert len(out["items"]) == 11  # 10 + 1 placeholder


def test_summarize_recurses_into_nested_dicts() -> None:
    out = _summarize_for_prompt({"a": {"b": "x" * 1000}}, max_str_len=20)
    assert len(out["a"]["b"]) <= 22


# ---------- Live AI test (skipped if no API key) ----------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY in env",
)
def test_claude_client_live_generation() -> None:
    """Live integration test — занимает 3-10 сек, требует API key."""
    c = ClaudeExplainerClient()
    assert c.enabled is True
    result = c.generate(
        anatomy_kind="deadlock",
        anatomy_data={"event_type": "TDEADLOCK", "participants": ["1001", "1002"]},
        rule_context="# Test\n\nThis is a test rule.",
    )
    assert result.ok is True
    assert len(result.text) > 50
    assert result.tokens_out > 0
