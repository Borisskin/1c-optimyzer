"""Sprint 8 Phase B — тесты /v1/ai/explain_plan endpoint с engine='postgres'.

Покрывает:
    - PG SYSTEM prompt содержит 1С-specific знание (enable_mergejoin=off, mchar, ...)
    - PG plan text format → роутится в explain_pg_plan
    - PG plan JSON format → роутится в explain_pg_plan
    - Endpoint dispatcher по engine: mssql → explain_mssql_plan, postgres → explain_pg_plan
    - PG mock Claude — assert что user prompt содержит реальный план + контекст 1С
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from schemas.ai import PlanExplainRequest
from services import ai_explainer


client = TestClient(app)


# Реальный PG plan из tools/sprint8_discovery/pg_tj_samples/dbpostgrs_sample.log
SAMPLE_PG_PLAN_TEXT = """Seq Scan on pg_catalog.pg_tablespace  (cost=0.00..1.02 rows=2 width=64) (actual time=0.011..0.011 rows=0.00 loops=1)
  Output: spcname
  Filter: ((pg_tablespace.spcname = 'v81c_index'::name) OR (pg_tablespace.spcname = 'v81c_data'::name))
  Rows Removed by Filter: 2
  Buffers: shared hit=1
Planning Time: 0.783 ms
Execution Time: 0.024 ms"""

# Mock PG plan JSON (как от EXPLAIN FORMAT JSON).
SAMPLE_PG_PLAN_JSON = json.dumps([
    {
        "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "pg_tablespace",
            "Total Cost": 1.02,
            "Plan Rows": 2,
            "Plan Width": 64,
        },
        "Planning Time": 0.783,
        "Execution Time": 0.024,
    }
])


SAMPLE_PG_REQUEST_TEXT = {
    "sql_text": "SELECT spcname FROM pg_tablespace WHERE spcname IN ('v81c_index', 'v81c_data')",
    "plan_xml": SAMPLE_PG_PLAN_TEXT,
    "plan_format": "text",
    "engine": "postgres",
    "planview_warnings": [],
    "missing_indexes": [],
    "plan_summary": None,
}

SAMPLE_PG_REQUEST_JSON = {
    "sql_text": "SELECT spcname FROM pg_tablespace",
    "plan_xml": SAMPLE_PG_PLAN_JSON,
    "plan_format": "json",
    "engine": "postgres",
    "planview_warnings": [],
    "missing_indexes": [],
    "plan_summary": None,
}

# Mock Claude response (как PG-AI вернул бы).
SAMPLE_PG_CLAUDE_OUTPUT = {
    "summary": "Seq Scan на маленькой системной таблице — план оптимальный, проблем нет.",
    "overall_severity": "Info",
    "hotspots": [],
    "recommendations": [],
    "suggested_indexes": [],
}


def _make_mock_response(text: str, model: str = "claude-haiku-4-5-20251001") -> MagicMock:
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.model = model
    return response


# ============================================================
# PG SYSTEM prompt — 1С-specific knowledge
# ============================================================


class TestPgSystemPrompt:
    def test_pg_system_prompt_mentions_enable_mergejoin_off(self) -> None:
        """PG SYSTEM prompt должен содержать enable_mergejoin=off (1С запрещает Merge Join)."""
        sp = ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        assert "enable_mergejoin" in sp
        assert "off" in sp

    def test_pg_system_prompt_mentions_cpu_operator_cost(self) -> None:
        """PG SYSTEM prompt должен предупредить про scaling cost (0.001 vs 0.005)."""
        sp = ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        assert "cpu_operator_cost" in sp
        assert "0.001" in sp

    def test_pg_system_prompt_mentions_mchar_mvarchar(self) -> None:
        """PG SYSTEM prompt должен знать про custom типы 1С (mchar/mvarchar)."""
        sp = ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        assert "mchar" in sp
        assert "mvarchar" in sp

    def test_pg_system_prompt_mentions_1c_naming(self) -> None:
        """PG SYSTEM prompt описывает naming convention (_reference15, _document, _accumrg)."""
        sp = ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        assert "_reference15" in sp or "_reference" in sp
        assert "_document" in sp
        assert "_accumrg" in sp

    def test_pg_system_prompt_lists_pg_operators(self) -> None:
        """PG SYSTEM prompt объясняет PG-операторы (Seq Scan, Hash Join, Memoize)."""
        sp = ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        assert "Seq Scan" in sp
        assert "Hash Join" in sp
        assert "Memoize" in sp

    def test_pg_system_prompt_forbids_merge_join_recommendation(self) -> None:
        """PG SYSTEM prompt явно запрещает рекомендовать Merge Join."""
        sp = ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        # Должна быть явная инструкция: «НЕ рекомендуй Merge Join».
        # Допустимы разные формулировки — главное mention.
        assert "Merge Join" in sp
        # Любая из форм: "НЕ рекомендуй" / "Не предлагай" / etc.
        forbid_markers = ["НЕ рекомендуй", "не предлагай", "отключён", "Merge Join — он"]
        assert any(m in sp for m in forbid_markers), f"PG prompt should forbid Merge Join recommendations, got: {sp[:500]}"


# ============================================================
# PG endpoint dispatcher
# ============================================================


class TestPgPlanEndpoint:
    def test_pg_text_routes_to_pg_explainer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """engine=postgres + plan_format=text → используется SYSTEM_PROMPT_EXPLAIN_PG_PLAN."""
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(
                json.dumps(SAMPLE_PG_CLAUDE_OUTPUT, ensure_ascii=False)
            )
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PG_REQUEST_TEXT)
        assert resp.status_code == 200

        # Assert что вызов Claude был с PG SYSTEM prompt, не MSSQL.
        call_args = mock_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        assert system_prompt == ai_explainer.SYSTEM_PROMPT_EXPLAIN_PG_PLAN
        # И сам план попал в user message.
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "Seq Scan on pg_catalog.pg_tablespace" in user_msg
        assert "Planning Time: 0.783 ms" in user_msg

    def test_pg_json_routes_to_pg_explainer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """engine=postgres + plan_format=json → PG explainer + json код-fence."""
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(json.dumps(SAMPLE_PG_CLAUDE_OUTPUT))
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PG_REQUEST_JSON)
        assert resp.status_code == 200

        user_msg = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        # JSON format → code fence ```json.
        assert "```json" in user_msg

    def test_mssql_default_still_routes_to_mssql_explainer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backward-compat: запрос без engine → MSSQL flow (Sprint 7 default)."""
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(json.dumps(SAMPLE_PG_CLAUDE_OUTPUT))
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        # Запрос БЕЗ engine — должен быть mssql default.
        req = {
            "sql_text": "SELECT 1",
            "plan_xml": '<?xml version="1.0"?><ShowPlanXML/>',
            "plan_format": "xml",
            "planview_warnings": [],
            "missing_indexes": [],
        }
        resp = client.post("/v1/ai/explain_plan", json=req)
        assert resp.status_code == 200

        system_prompt = mock_client.messages.create.call_args.kwargs["system"]
        assert system_prompt == ai_explainer.SYSTEM_PROMPT_EXPLAIN_MSSQL_PLAN

    def test_pg_prompt_includes_1c_settings_in_user_msg(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User prompt для PG должен явно перечислить 1С SET-команды для контекста."""
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(json.dumps(SAMPLE_PG_CLAUDE_OUTPUT))
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PG_REQUEST_TEXT)
        assert resp.status_code == 200

        user_msg = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        # User prompt должен напомнить AI про 1С-specific settings.
        assert "enable_mergejoin = off" in user_msg
        assert "cpu_operator_cost = 0.001" in user_msg


# ============================================================
# PG prompt builder unit tests
# ============================================================


class TestPgPromptBuilder:
    def test_pg_text_uses_text_code_block(self) -> None:
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=SAMPLE_PG_PLAN_TEXT,
            plan_format="text",
            engine="postgres",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, truncated = ai_explainer._build_pg_plan_user_prompt(req)
        assert "```text" in prompt
        assert "Seq Scan on pg_catalog.pg_tablespace" in prompt
        assert truncated is False

    def test_pg_json_uses_json_code_block(self) -> None:
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=SAMPLE_PG_PLAN_JSON,
            plan_format="json",
            engine="postgres",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, truncated = ai_explainer._build_pg_plan_user_prompt(req)
        assert "```json" in prompt
        assert "Plan" in prompt

    def test_pg_truncation_for_huge_plan(self) -> None:
        huge = "Seq Scan " + ("a" * (ai_explainer.AI_PLAN_MAX_CHARS + 5_000))
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=huge,
            plan_format="text",
            engine="postgres",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, truncated = ai_explainer._build_pg_plan_user_prompt(req)
        assert truncated is True
        assert "TRUNCATED" in prompt

    def test_pg_user_prompt_includes_set_reminders(self) -> None:
        """User prompt для PG обязан перечислить SET-команды клиента (контекст для AI)."""
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=SAMPLE_PG_PLAN_TEXT,
            plan_format="text",
            engine="postgres",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, _ = ai_explainer._build_pg_plan_user_prompt(req)
        assert "enable_mergejoin" in prompt
        assert "cpu_operator_cost" in prompt
        assert "lock_timeout" in prompt
