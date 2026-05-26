"""Sprint 11 Phase B/C — integration тесты cache в AI endpoints.

Проверяет:
  - Plan AI (MSSQL XML, MSSQL text, PG text, PG JSON) — first call → miss → AI call → cache;
    second call → hit → no AI call.
  - Same plan с разными runtime stats → same cache key → hit (canonicalization).
  - force_refresh=True → bypass cache → AI call → cache update.
  - was_cached / cache_age_seconds / cache_key корректно проставляются.
  - Query AI + Logcfg AI используют cache.
  - PROMPT_VERSION bump invalidates cache (entries старой версии не находятся).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.ai import (
    ExplainRequest,
    LogcfgGenerateRequest,
    PlanExplainRequest,
)
from services import ai_explainer
from services.ai_cache import CacheType, get_cache


# ---------- Mock helpers ----------

SAMPLE_PLAN_AI_OUTPUT = {
    "summary": "План OK",
    "overall_severity": "Info",
    "hotspots": [],
    "recommendations": [],
    "suggested_indexes": [],
}

SAMPLE_QUERY_AI_OUTPUT = {
    "explanation_summary": "Проблем не найдено",
    "issues": [],
    "suggested_rewrite": {"available": False, "sdbl": None, "reasoning": None},
}

SAMPLE_LOGCFG_AI_OUTPUT = {
    "config": {
        "events": {"DBMSSQL": {"enabled": True, "threshold_cs": 10}},
        "capture_plans": False,
        "log_directory": "C:\\1C-TechLog",
        "history_hours": 72,
    },
    "explanation": "Для медленных SQL запросов нужен DBMSSQL.",
    "events_rationale": [
        {"event": "DBMSSQL", "threshold": "10 cs", "why": "SQL"}
    ],
    "estimated_use_duration": "30-60 минут",
    "warnings": [],
}


def _mock_anthropic_response(text: str, model: str = "claude-haiku-4-5-20251001") -> MagicMock:
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.model = model
    return resp


@pytest.fixture
def mock_anthropic_plan(monkeypatch: pytest.MonkeyPatch):
    """Mock Anthropic client returning SAMPLE_PLAN_AI_OUTPUT. Returns the mock for call assertions."""
    monkeypatch.setattr(
        "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
    )
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_anthropic_response(
            json.dumps(SAMPLE_PLAN_AI_OUTPUT, ensure_ascii=False)
        )
    )
    monkeypatch.setattr(
        "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
    )
    return mock_client


@pytest.fixture
def mock_anthropic_query(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
    )
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_anthropic_response(
            json.dumps(SAMPLE_QUERY_AI_OUTPUT, ensure_ascii=False)
        )
    )
    monkeypatch.setattr(
        "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
    )
    return mock_client


@pytest.fixture
def mock_anthropic_logcfg(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
    )
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_anthropic_response(
            json.dumps(SAMPLE_LOGCFG_AI_OUTPUT, ensure_ascii=False)
        )
    )
    monkeypatch.setattr(
        "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
    )
    return mock_client


# ============================================================================
# Phase B — Plan AI cache
# ============================================================================


PLAN_MSSQL_XML = (
    '<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan">'
    '<BatchSequence><Batch><Statements>'
    '<StmtSimple StatementId="1" EstimatedRows="100">'
    '<QueryPlan/>'
    '</StmtSimple>'
    '</Statements></Batch></BatchSequence>'
    '</ShowPlanXML>'
)


def _mssql_xml_req(force_refresh: bool = False) -> PlanExplainRequest:
    return PlanExplainRequest(
        sql_text="SELECT * FROM _Reference15",
        plan_xml=PLAN_MSSQL_XML,
        plan_format="xml",
        engine="mssql",
        planview_warnings=[],
        missing_indexes=[],
        force_refresh=force_refresh,
    )


def _pg_text_req(force_refresh: bool = False) -> PlanExplainRequest:
    return PlanExplainRequest(
        sql_text="SELECT * FROM _reference15",
        plan_xml="Seq Scan on _reference15 (cost=0..15 rows=500 width=20)",
        plan_format="text",
        engine="postgres",
        planview_warnings=[],
        missing_indexes=[],
        force_refresh=force_refresh,
    )


class TestPlanCacheMissThenHit:
    @pytest.mark.asyncio
    async def test_mssql_xml_first_call_miss_then_hit(self, mock_anthropic_plan):
        # First call — miss, AI is called
        req = _mssql_xml_req()
        resp1 = await ai_explainer.explain_plan_query(req)
        assert resp1.was_cached is False
        assert resp1.cache_key is not None
        assert resp1.summary == "План OK"
        assert mock_anthropic_plan.messages.create.call_count == 1

        # Second call with same input — hit, no AI call
        resp2 = await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert resp2.was_cached is True
        assert resp2.cache_age_seconds is not None
        assert resp2.cache_age_seconds >= 0
        assert resp2.cache_key == resp1.cache_key
        assert resp2.summary == "План OK"
        # Critical: AI was NOT called again
        assert mock_anthropic_plan.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_pg_text_first_call_miss_then_hit(self, mock_anthropic_plan):
        req = _pg_text_req()
        resp1 = await ai_explainer.explain_plan_query(req)
        assert resp1.was_cached is False
        assert mock_anthropic_plan.messages.create.call_count == 1

        resp2 = await ai_explainer.explain_plan_query(_pg_text_req())
        assert resp2.was_cached is True
        assert mock_anthropic_plan.messages.create.call_count == 1


class TestPlanCacheCanonicalization:
    @pytest.mark.asyncio
    async def test_mssql_xml_runtime_stats_dont_break_cache(self, mock_anthropic_plan):
        """Same plan с разными ActualRows → same cache key → hit."""
        plan_run1 = (
            '<ShowPlanXML><RelOp NodeId="0" EstimatedRows="100" ActualRows="100"/></ShowPlanXML>'
        )
        plan_run2 = (
            '<ShowPlanXML><RelOp NodeId="0" EstimatedRows="100" ActualRows="99999"/></ShowPlanXML>'
        )
        req1 = PlanExplainRequest(
            sql_text="X",
            plan_xml=plan_run1,
            plan_format="xml",
            engine="mssql",
        )
        req2 = PlanExplainRequest(
            sql_text="X",
            plan_xml=plan_run2,
            plan_format="xml",
            engine="mssql",
        )
        # First call → miss
        await ai_explainer.explain_plan_query(req1)
        assert mock_anthropic_plan.messages.create.call_count == 1
        # Second call with different ActualRows → still hit
        resp = await ai_explainer.explain_plan_query(req2)
        assert resp.was_cached is True
        assert mock_anthropic_plan.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_different_plans_different_cache_keys(self, mock_anthropic_plan):
        req1 = PlanExplainRequest(
            sql_text="X",
            plan_xml='<ShowPlanXML><Op EstimatedRows="100"/></ShowPlanXML>',
            plan_format="xml",
            engine="mssql",
        )
        req2 = PlanExplainRequest(
            sql_text="X",
            plan_xml='<ShowPlanXML><Op EstimatedRows="1000"/></ShowPlanXML>',
            plan_format="xml",
            engine="mssql",
        )
        resp1 = await ai_explainer.explain_plan_query(req1)
        resp2 = await ai_explainer.explain_plan_query(req2)
        assert resp1.cache_key != resp2.cache_key
        # Both were AI calls (cache miss for both)
        assert mock_anthropic_plan.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_different_engines_different_keys(self, mock_anthropic_plan):
        """Same XML text, but different engine → different cache key (cache_type differs)."""
        req_mssql = PlanExplainRequest(
            sql_text="X", plan_xml="Seq Scan on t", plan_format="text", engine="mssql",
        )
        req_pg = PlanExplainRequest(
            sql_text="X", plan_xml="Seq Scan on t", plan_format="text", engine="postgres",
        )
        resp1 = await ai_explainer.explain_plan_query(req_mssql)
        resp2 = await ai_explainer.explain_plan_query(req_pg)
        assert resp1.cache_key != resp2.cache_key


class TestPlanCacheForceRefresh:
    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, mock_anthropic_plan):
        # Prime cache
        await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert mock_anthropic_plan.messages.create.call_count == 1

        # Force refresh → AI is called again
        resp = await ai_explainer.explain_plan_query(_mssql_xml_req(force_refresh=True))
        assert resp.was_cached is False
        assert mock_anthropic_plan.messages.create.call_count == 2

        # Without force_refresh — now hit again (cache was updated)
        resp = await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert resp.was_cached is True
        assert mock_anthropic_plan.messages.create.call_count == 2  # unchanged


class TestPlanCacheMetadata:
    @pytest.mark.asyncio
    async def test_cache_key_format(self, mock_anthropic_plan):
        resp = await ai_explainer.explain_plan_query(_mssql_xml_req())
        # SHA256 hex = 64 chars
        assert len(resp.cache_key) == 64
        assert all(c in "0123456789abcdef" for c in resp.cache_key)

    @pytest.mark.asyncio
    async def test_was_cached_false_on_miss(self, mock_anthropic_plan):
        resp = await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert resp.was_cached is False
        assert resp.cache_age_seconds is None

    @pytest.mark.asyncio
    async def test_cache_age_increases(self, mock_anthropic_plan):
        import asyncio

        await ai_explainer.explain_plan_query(_mssql_xml_req())
        # Wait a moment
        await asyncio.sleep(1.1)
        resp = await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert resp.was_cached is True
        assert resp.cache_age_seconds is not None
        assert resp.cache_age_seconds >= 1


class TestPlanCachePromptVersionInvalidation:
    @pytest.mark.asyncio
    async def test_prompt_version_bump_invalidates(
        self, mock_anthropic_plan, monkeypatch: pytest.MonkeyPatch
    ):
        # First call with v1
        await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert mock_anthropic_plan.messages.create.call_count == 1

        # Bump version → cache key changes → miss
        monkeypatch.setattr(ai_explainer, "PROMPT_VERSION_PLAN_MSSQL", "v2")
        resp = await ai_explainer.explain_plan_query(_mssql_xml_req())
        assert resp.was_cached is False
        assert mock_anthropic_plan.messages.create.call_count == 2


# ============================================================================
# Phase B — All four Plan cache types tracked
# ============================================================================


class TestAllFourPlanCacheTypes:
    """Smoke test: each cache_type produces a distinct cache key."""

    @pytest.mark.asyncio
    async def test_four_distinct_keys(self, mock_anthropic_plan):
        req_mssql_xml = PlanExplainRequest(
            sql_text="X",
            plan_xml='<ShowPlanXML/>',
            plan_format="xml",
            engine="mssql",
        )
        req_mssql_text = PlanExplainRequest(
            sql_text="X", plan_xml="|--Seek", plan_format="text", engine="mssql",
        )
        req_pg_text = PlanExplainRequest(
            sql_text="X", plan_xml="Seq Scan", plan_format="text", engine="postgres",
        )
        req_pg_json = PlanExplainRequest(
            sql_text="X",
            plan_xml='{"Plan": {"Node Type": "Seq Scan"}}',
            plan_format="json",
            engine="postgres",
        )
        keys = set()
        for req in [req_mssql_xml, req_mssql_text, req_pg_text, req_pg_json]:
            resp = await ai_explainer.explain_plan_query(req)
            keys.add(resp.cache_key)
        # All 4 distinct
        assert len(keys) == 4


# ============================================================================
# Phase C — Query AI cache
# ============================================================================


def _query_req(
    sdbl: str = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты",
    diagnostics: list | None = None,
    force_refresh: bool = False,
) -> ExplainRequest:
    return ExplainRequest(
        query_sdbl=sdbl,
        diagnostics=diagnostics or [],
        force_refresh=force_refresh,
    )


class TestQueryCacheMissThenHit:
    @pytest.mark.asyncio
    async def test_query_cache_hit(self, mock_anthropic_query):
        resp1 = await ai_explainer.explain_query(_query_req())
        assert resp1.was_cached is False
        assert mock_anthropic_query.messages.create.call_count == 1

        resp2 = await ai_explainer.explain_query(_query_req())
        assert resp2.was_cached is True
        assert resp2.cache_key == resp1.cache_key
        assert mock_anthropic_query.messages.create.call_count == 1


class TestQueryCacheCanonicalization:
    @pytest.mark.asyncio
    async def test_whitespace_doesnt_break_cache(self, mock_anthropic_query):
        await ai_explainer.explain_query(_query_req("ВЫБРАТЬ * ИЗ Т"))
        resp = await ai_explainer.explain_query(
            _query_req("ВЫБРАТЬ\n\t* ИЗ Т")  # different whitespace
        )
        assert resp.was_cached is True
        assert mock_anthropic_query.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_comments_dont_break_cache(self, mock_anthropic_query):
        await ai_explainer.explain_query(_query_req("ВЫБРАТЬ * ИЗ Т"))
        resp = await ai_explainer.explain_query(
            _query_req("ВЫБРАТЬ /* комментарий */ * ИЗ Т")
        )
        assert resp.was_cached is True

    @pytest.mark.asyncio
    async def test_diagnostic_order_doesnt_break_cache(self, mock_anthropic_query):
        from schemas.ai import DiagnosticInput

        diag1 = DiagnosticInput(
            code="RefOveruse",
            message="msg1",
            severity="Critical",
            range_start_line=0,
            range_start_char=0,
            range_end_line=0,
            range_end_char=10,
            snippet="x",
        )
        diag2 = DiagnosticInput(
            code="ZAlias",
            message="msg2",
            severity="Major",
            range_start_line=1,
            range_start_char=0,
            range_end_line=1,
            range_end_char=10,
            snippet="y",
        )
        # First call: diagnostics in one order
        await ai_explainer.explain_query(
            _query_req(diagnostics=[diag1, diag2])
        )
        # Second call: same diagnostics in opposite order → still cache hit (sorted by code)
        resp = await ai_explainer.explain_query(
            _query_req(diagnostics=[diag2, diag1])
        )
        assert resp.was_cached is True
        assert mock_anthropic_query.messages.create.call_count == 1


class TestQueryCacheForceRefresh:
    @pytest.mark.asyncio
    async def test_query_force_refresh_bypasses(self, mock_anthropic_query):
        await ai_explainer.explain_query(_query_req())
        assert mock_anthropic_query.messages.create.call_count == 1

        resp = await ai_explainer.explain_query(_query_req(force_refresh=True))
        assert resp.was_cached is False
        assert mock_anthropic_query.messages.create.call_count == 2


class TestQueryCacheTtl:
    @pytest.mark.asyncio
    async def test_query_ttl_is_90_days(self, mock_anthropic_query):
        from services.ai_cache import get_cache

        await ai_explainer.explain_query(_query_req())
        # Inspect cache entry directly
        cache = get_cache()
        entry = list(cache.storage.iter_entries())[0]
        assert entry.expires_at is not None
        from datetime import datetime, timedelta
        delta = entry.expires_at - datetime.utcnow()
        # 90 days ± 1 day boundary
        assert timedelta(days=89) <= delta <= timedelta(days=90, hours=1)


# ============================================================================
# Phase C — Logcfg AI cache
# ============================================================================


def _logcfg_req(
    description: str = "Медленные SQL запросы при печати документа",
    force_refresh: bool = False,
) -> LogcfgGenerateRequest:
    return LogcfgGenerateRequest(
        problem_description=description,
        platform_version="8.3.24",
        dbms="mssql",
        force_refresh=force_refresh,
    )


class TestLogcfgCacheMissThenHit:
    @pytest.mark.asyncio
    async def test_logcfg_cache_hit(self, mock_anthropic_logcfg):
        resp1 = await ai_explainer.generate_logcfg(_logcfg_req())
        assert resp1.was_cached is False
        assert mock_anthropic_logcfg.messages.create.call_count == 1

        resp2 = await ai_explainer.generate_logcfg(_logcfg_req())
        assert resp2.was_cached is True
        assert mock_anthropic_logcfg.messages.create.call_count == 1


class TestLogcfgCacheCanonicalization:
    @pytest.mark.asyncio
    async def test_case_insensitive_cache_hit(self, mock_anthropic_logcfg):
        await ai_explainer.generate_logcfg(_logcfg_req("Медленный отчёт"))
        resp = await ai_explainer.generate_logcfg(_logcfg_req("МЕДЛЕННЫЙ ОТЧЁТ"))
        assert resp.was_cached is True

    @pytest.mark.asyncio
    async def test_punctuation_normalized(self, mock_anthropic_logcfg):
        await ai_explainer.generate_logcfg(_logcfg_req("Медленный отчёт по продажам"))
        resp = await ai_explainer.generate_logcfg(
            _logcfg_req("Медленный отчёт, по продажам!")
        )
        assert resp.was_cached is True

    @pytest.mark.asyncio
    async def test_different_platforms_different_keys(
        self, mock_anthropic_logcfg
    ):
        req1 = LogcfgGenerateRequest(
            problem_description="Стандартная проблема",
            platform_version="8.3.24",
            dbms="mssql",
        )
        req2 = LogcfgGenerateRequest(
            problem_description="Стандартная проблема",
            platform_version="8.3.20",  # different version
            dbms="mssql",
        )
        resp1 = await ai_explainer.generate_logcfg(req1)
        resp2 = await ai_explainer.generate_logcfg(req2)
        assert resp1.cache_key != resp2.cache_key

    @pytest.mark.asyncio
    async def test_different_dbms_different_keys(self, mock_anthropic_logcfg):
        req1 = LogcfgGenerateRequest(
            problem_description="Стандартная проблема",
            platform_version="8.3.24",
            dbms="mssql",
        )
        req2 = LogcfgGenerateRequest(
            problem_description="Стандартная проблема",
            platform_version="8.3.24",
            dbms="postgres",
        )
        resp1 = await ai_explainer.generate_logcfg(req1)
        resp2 = await ai_explainer.generate_logcfg(req2)
        assert resp1.cache_key != resp2.cache_key


class TestLogcfgCacheForceRefresh:
    @pytest.mark.asyncio
    async def test_logcfg_force_refresh_bypasses(self, mock_anthropic_logcfg):
        await ai_explainer.generate_logcfg(_logcfg_req())
        assert mock_anthropic_logcfg.messages.create.call_count == 1

        resp = await ai_explainer.generate_logcfg(_logcfg_req(force_refresh=True))
        assert resp.was_cached is False
        assert mock_anthropic_logcfg.messages.create.call_count == 2


class TestLogcfgCacheTtl:
    @pytest.mark.asyncio
    async def test_logcfg_ttl_is_30_days(self, mock_anthropic_logcfg):
        from services.ai_cache import get_cache

        await ai_explainer.generate_logcfg(_logcfg_req())
        cache = get_cache()
        entry = list(cache.storage.iter_entries())[0]
        assert entry.expires_at is not None
        from datetime import datetime, timedelta
        delta = entry.expires_at - datetime.utcnow()
        assert timedelta(days=29) <= delta <= timedelta(days=30, hours=1)
