"""Sprint 7 — тесты /v1/ai/explain_plan endpoint.

Покрывает:
    - POST happy-path (XML format + mocked Claude)
    - POST happy-path (text format, без warnings/missing_indexes)
    - 503 при отсутствии ANTHROPIC_API_KEY
    - 502 при API error
    - plan_format default → "xml"
    - plan_format validation (text/xml only)
    - plan truncation для >50K планов
    - prompt template содержит {plan_format} и {plan_content}
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


SAMPLE_PLAN_XML = '<?xml version="1.0"?><ShowPlanXML><BatchSequence/></ShowPlanXML>'
SAMPLE_PLAN_TEXT = (
    "|--Clustered Index Seek(OBJECT:([dbo].[_Reference15]))\n"
    "|     SEEK:([_Reference15].[_IDRRef]=(?))\n"
    "|     Estimated Rows = 1\n"
)


SAMPLE_PLAN_REQUEST_XML = {
    "sql_text": "SELECT TOP 100 _Description FROM dbo._Reference15",
    "plan_xml": SAMPLE_PLAN_XML,
    "plan_format": "xml",
    "planview_warnings": [],
    "missing_indexes": [],
    "plan_summary": None,
}

SAMPLE_PLAN_REQUEST_TEXT = {
    "sql_text": "SELECT TOP 100 _Description FROM dbo._Reference15",
    "plan_xml": SAMPLE_PLAN_TEXT,
    "plan_format": "text",
    "planview_warnings": [],
    "missing_indexes": [],
    "plan_summary": None,
}


SAMPLE_CLAUDE_PLAN_OUTPUT = {
    "summary": "План использует efficient Clustered Index Seek по PK — без проблем.",
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


# === Endpoint tests ===


class TestExplainPlanEndpoint:
    def test_no_api_key_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "", raising=False
        )
        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PLAN_REQUEST_XML)
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "ai_not_configured"

    def test_successful_xml_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(
                json.dumps(SAMPLE_CLAUDE_PLAN_OUTPUT, ensure_ascii=False)
            )
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PLAN_REQUEST_XML)
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_severity"] == "Info"
        assert "Clustered Index Seek" in body["summary"]
        assert body["model_used"] == "claude-haiku-4-5-20251001"
        assert body["plan_truncated"] is False

    def test_successful_text_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(
                json.dumps(SAMPLE_CLAUDE_PLAN_OUTPUT, ensure_ascii=False)
            )
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PLAN_REQUEST_TEXT)
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_severity"] == "Info"

        # Проверяем что в user-prompt действительно ушёл text формат.
        call_args = mock_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "формат: text" in user_msg
        assert SAMPLE_PLAN_TEXT.strip() in user_msg
        # И НЕ должно быть XML fence для text формата
        assert "```text" in user_msg
        assert "```xml" not in user_msg.replace("```xml\n```", "")  # допустимы пустые xml упоминания в SYSTEM

    def test_plan_format_defaults_to_xml(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Если plan_format не передан — Pydantic подставит "xml" по умолчанию."""
        req_without_format = {**SAMPLE_PLAN_REQUEST_XML}
        del req_without_format["plan_format"]

        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(json.dumps(SAMPLE_CLAUDE_PLAN_OUTPUT))
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=req_without_format)
        assert resp.status_code == 200
        user_msg = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "формат: xml" in user_msg

    def test_plan_format_invalid_rejected(self) -> None:
        """plan_format='wrong' → 422 Pydantic validation error."""
        bad_req = {**SAMPLE_PLAN_REQUEST_XML, "plan_format": "wrong"}
        resp = client.post("/v1/ai/explain_plan", json=bad_req)
        assert resp.status_code == 422

    def test_api_error_returns_502(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Anthropic SDK выбросил APIError → 502 bad gateway."""
        import anthropic

        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )
        mock_client = MagicMock()
        # APIError(message, request, body) — упрощённый mock через side_effect.
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIError(
                message="rate limit", request=MagicMock(), body=None
            )
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic", lambda **_: mock_client
        )

        resp = client.post("/v1/ai/explain_plan", json=SAMPLE_PLAN_REQUEST_XML)
        assert resp.status_code == 502
        body = resp.json()
        assert body["detail"]["error"] == "ai_orchestration_failed"


# === Schema tests ===


class TestPlanExplainRequestSchema:
    def test_minimum_valid(self) -> None:
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml="<x/>",
            planview_warnings=[],
            missing_indexes=[],
        )
        assert req.plan_format == "xml"

    def test_text_format_accepted(self) -> None:
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml="some text plan",
            plan_format="text",
            planview_warnings=[],
            missing_indexes=[],
        )
        assert req.plan_format == "text"

    def test_invalid_format_rejected(self) -> None:
        """Sprint 8 Phase B — теперь plan_format='json' допустим (для PG EXPLAIN FORMAT JSON).

        Проверяем что нелегальный 'xml-text-junk' отвергается.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlanExplainRequest(
                sql_text="SELECT 1",
                plan_xml="<x/>",
                plan_format="xml-text-junk",  # type: ignore[arg-type]
                planview_warnings=[],
                missing_indexes=[],
            )

    def test_json_format_now_accepted(self) -> None:
        """Sprint 8 Phase B — json format добавлен для PG re-EXPLAIN flow."""
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml='[{"Plan":{}}]',
            plan_format="json",
            engine="postgres",
            planview_warnings=[],
            missing_indexes=[],
        )
        assert req.plan_format == "json"
        assert req.engine == "postgres"

    def test_engine_defaults_to_mssql(self) -> None:
        """Backward-compat: engine не передан → "mssql" (Sprint 7 default)."""
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml="<x/>",
            planview_warnings=[],
            missing_indexes=[],
        )
        assert req.engine == "mssql"

    def test_engine_invalid_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlanExplainRequest(
                sql_text="SELECT 1",
                plan_xml="<x/>",
                engine="oracle",  # type: ignore[arg-type]
                planview_warnings=[],
                missing_indexes=[],
            )

    def test_extra_fields_forbidden(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlanExplainRequest(
                sql_text="SELECT 1",
                plan_xml="<x/>",
                planview_warnings=[],
                missing_indexes=[],
                unknown_field="x",  # type: ignore[call-arg]
            )

    def test_min_length_validation(self) -> None:
        """plan_xml пустая строка → ValidationError (min_length=1)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlanExplainRequest(
                sql_text="SELECT 1",
                plan_xml="",
                planview_warnings=[],
                missing_indexes=[],
            )


# === Prompt builder tests ===


class TestPromptBuilder:
    def test_xml_format_uses_xml_fence(self) -> None:
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=SAMPLE_PLAN_XML,
            plan_format="xml",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, truncated = ai_explainer._build_plan_user_prompt(req)
        assert "формат: xml" in prompt
        assert "```xml" in prompt
        assert SAMPLE_PLAN_XML in prompt
        assert truncated is False

    def test_text_format_uses_text_fence(self) -> None:
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=SAMPLE_PLAN_TEXT,
            plan_format="text",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, truncated = ai_explainer._build_plan_user_prompt(req)
        assert "формат: text" in prompt
        assert "```text" in prompt
        assert SAMPLE_PLAN_TEXT.strip() in prompt

    def test_truncation_triggers_for_huge_plan(self) -> None:
        huge_plan = "<x>" + "a" * (ai_explainer.AI_PLAN_MAX_CHARS + 10_000) + "</x>"
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=huge_plan,
            plan_format="xml",
            planview_warnings=[],
            missing_indexes=[],
        )
        prompt, truncated = ai_explainer._build_plan_user_prompt(req)
        assert truncated is True
        assert "TRUNCATED" in prompt

    def test_no_truncation_for_normal_plan(self) -> None:
        normal = "<x>" + "a" * 1000 + "</x>"
        req = PlanExplainRequest(
            sql_text="SELECT 1",
            plan_xml=normal,
            planview_warnings=[],
            missing_indexes=[],
        )
        _prompt, truncated = ai_explainer._build_plan_user_prompt(req)
        assert truncated is False

    def test_system_prompt_mentions_both_formats(self) -> None:
        """Регресс: MSSQL SYSTEM prompt упоминает XML и TEXT форматы (Phase D).

        Sprint 8 Phase B: SYSTEM_PROMPT_EXPLAIN_PLAN переименован в
        SYSTEM_PROMPT_EXPLAIN_MSSQL_PLAN — PG получил свой prompt.
        """
        sys_prompt = ai_explainer.SYSTEM_PROMPT_EXPLAIN_MSSQL_PLAN
        assert "XML" in sys_prompt
        assert "TEXT" in sys_prompt or "text" in sys_prompt
        assert "SHOWPLAN_TEXT" in sys_prompt


class TestTruncatePlanXml:
    """Тесты на _truncate_plan_xml — обрезка больших планов до AI_PLAN_MAX_CHARS."""

    def test_under_max_returns_unchanged(self) -> None:
        small = "<x>" + ("a" * 500) + "</x>"
        result, truncated = ai_explainer._truncate_plan_xml(small)
        assert result == small
        assert truncated is False

    def test_over_max_truncated_to_80_percent(self) -> None:
        huge = "<x>" + ("a" * (ai_explainer.AI_PLAN_MAX_CHARS + 5_000)) + "</x>"
        result, truncated = ai_explainer._truncate_plan_xml(huge)
        assert truncated is True
        # Контент короче оригинала, плюс есть TRUNCATED маркер.
        assert len(result) < len(huge)
        assert "TRUNCATED" in result

    def test_truncated_keeps_original_size_in_marker(self) -> None:
        huge = "x" * (ai_explainer.AI_PLAN_MAX_CHARS * 2)
        result, _ = ai_explainer._truncate_plan_xml(huge)
        # Маркер содержит оригинальный размер для трассировки.
        assert str(len(huge)) in result
