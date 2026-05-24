"""Тесты /v1/ai/explain (Sprint 6 Phase D)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from schemas.ai import (
    ConfigurationContext,
    DiagnosticInput,
    ExplainRequest,
)
from services import ai_explainer


client = TestClient(app)


SAMPLE_DIAG = DiagnosticInput(
    code="RefOveruse",
    message="Избавьтесь от .Ссылка",
    severity="Major",
    range_start_line=4,
    range_start_char=12,
    range_end_line=4,
    range_end_char=35,
    snippet="Док.Ссылка.Контрагент.Ссылка",
)


SAMPLE_REQUEST = ExplainRequest(
    query_sdbl="ВЫБРАТЬ Док.Ссылка.Контрагент.Ссылка.Наименование ИЗ Документ.Реализация КАК Док",
    diagnostics=[SAMPLE_DIAG],
    configuration_context=ConfigurationContext(
        mdo_types_used=["Document.Реализация"],
    ),
)


SAMPLE_CLAUDE_OUTPUT = {
    "explanation_summary": "В запросе обнаружено лишнее использование .Ссылка",
    "issues": [
        {
            "title": "Дублирующееся .Ссылка в цепочке полей",
            "severity": "Major",
            "what": "В строке 4 цепочка Док.Ссылка.Контрагент.Ссылка.Наименование...",
            "why": "Каждое .Ссылка генерирует дополнительный JOIN в T-SQL",
            "what_to_do": "Замените на Док.Ссылка.Контрагент.Наименование",
            "linked_diagnostic_codes": ["RefOveruse"],
        }
    ],
    "suggested_rewrite": {
        "available": True,
        "sdbl": "ВЫБРАТЬ Док.Ссылка.Контрагент.Наименование ИЗ Документ.Реализация КАК Док",
        "reasoning": "Убраны дублирующиеся .Ссылка",
    },
}


def _make_mock_response(text: str, model: str = "claude-sonnet-4-5-20250929") -> MagicMock:
    """Mock Claude API response."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.model = model
    return response


class TestExtractJson:
    def test_no_fence(self) -> None:
        text = '{"a": 1}'
        assert ai_explainer.extract_json(text) == text

    def test_with_fence(self) -> None:
        text = '```json\n{"a": 1}\n```'
        assert ai_explainer.extract_json(text) == '{"a": 1}'

    def test_with_prose_around(self) -> None:
        text = 'Вот JSON ответ:\n{"a": 1}\nКонец'
        cleaned = ai_explainer.extract_json(text)
        assert cleaned == '{"a": 1}'

    def test_already_clean(self) -> None:
        text = '{"explanation_summary": "ok", "issues": []}'
        assert ai_explainer.extract_json(text) == text


class TestExplainEndpoint:
    def test_no_api_key_returns_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("api.settings.settings.anthropic_api_key", "")
        # Также монка в services.ai_explainer settings — он импортирует через api.settings
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "", raising=False
        )
        resp = client.post("/v1/ai/explain", json=SAMPLE_REQUEST.model_dump())
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error"] == "ai_not_configured"

    def test_successful_explain_with_mocked_claude(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(json.dumps(SAMPLE_CLAUDE_OUTPUT, ensure_ascii=False))
        )

        def _factory(**_: object) -> MagicMock:
            return mock_client

        monkeypatch.setattr("services.ai_explainer.anthropic.AsyncAnthropic", _factory)

        resp = client.post("/v1/ai/explain", json=SAMPLE_REQUEST.model_dump())
        assert resp.status_code == 200
        body = resp.json()
        assert body["explanation_summary"] == "В запросе обнаружено лишнее использование .Ссылка"
        assert len(body["issues"]) == 1
        assert body["issues"][0]["severity"] == "Major"
        assert body["suggested_rewrite"]["available"] is True
        assert body["model_used"] == "claude-sonnet-4-5-20250929"
        assert body["duration_ms"] >= 0

    def test_invalid_json_triggers_retry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )

        mock_client = MagicMock()
        # Первый вызов — невалидный, второй — валидный.
        mock_client.messages.create = AsyncMock(
            side_effect=[
                _make_mock_response("oops, not json"),
                _make_mock_response(json.dumps(SAMPLE_CLAUDE_OUTPUT, ensure_ascii=False)),
            ]
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic",
            lambda **_: mock_client,
        )

        resp = client.post("/v1/ai/explain", json=SAMPLE_REQUEST.model_dump())
        assert resp.status_code == 200
        assert mock_client.messages.create.call_count == 2

    def test_empty_diagnostics_returns_no_issues(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "services.ai_explainer.settings.anthropic_api_key", "sk-test-fake"
        )

        no_issues_output = {
            "explanation_summary": "Проблем не найдено",
            "issues": [],
            "suggested_rewrite": {"available": False},
        }
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_mock_response(json.dumps(no_issues_output, ensure_ascii=False))
        )
        monkeypatch.setattr(
            "services.ai_explainer.anthropic.AsyncAnthropic",
            lambda **_: mock_client,
        )

        req = ExplainRequest(query_sdbl="ВЫБРАТЬ 1", diagnostics=[])
        resp = client.post("/v1/ai/explain", json=req.model_dump())
        assert resp.status_code == 200
        body = resp.json()
        assert body["issues"] == []
        assert body["suggested_rewrite"]["available"] is False

    def test_validation_rejects_empty_sdbl(self) -> None:
        resp = client.post(
            "/v1/ai/explain",
            json={"query_sdbl": "", "diagnostics": []},
        )
        assert resp.status_code == 422  # Pydantic validation

    def test_validation_rejects_too_long_sdbl(self) -> None:
        huge = "ВЫБРАТЬ 1 " * 10000
        resp = client.post(
            "/v1/ai/explain",
            json={"query_sdbl": huge, "diagnostics": []},
        )
        assert resp.status_code == 422


class TestPromptBuilding:
    def test_user_prompt_contains_sdbl_and_diagnostics(self) -> None:
        prompt = ai_explainer._build_user_prompt(SAMPLE_REQUEST)
        assert "Док.Ссылка.Контрагент.Ссылка.Наименование" in prompt
        assert "RefOveruse" in prompt
        assert "Major" in prompt
        assert "Document.Реализация" in prompt
