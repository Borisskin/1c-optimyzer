"""Sprint 10 Phase A — тесты generate_logcfg endpoint и service.

Все тесты мокируют Anthropic API через unittest.mock — не требуют реального ключа.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.ai import (
    EventConfig,
    LogcfgConfig,
    LogcfgEvents,
    LogcfgGenerateRequest,
    LogcfgGenerateResponse,
)
from services.ai_explainer import (
    AiExplainerError,
    AiNotConfiguredError,
    generate_logcfg,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_ai_response(events: dict | None = None) -> str:
    """Генерирует валидный JSON-ответ Haiku для тестов."""
    if events is None:
        events = {
            "CALL": {"enabled": True, "threshold_cs": 100},
            "DBMSSQL": {"enabled": True, "threshold_cs": 10},
            "EXCP": {"enabled": True, "threshold_cs": None},
        }
    return json.dumps({
        "config": {
            "events": events,
            "capture_plans": False,
            "log_directory": "C:\\1C-TechLog",
            "history_hours": 72,
        },
        "explanation": "Для расследования медленных операций нужны CALL, DBMSSQL и EXCP.",
        "events_rationale": [
            {"event": "CALL", "threshold": "100 cs (1 с)", "why": "Верхний уровень вызовов"},
            {"event": "DBMSSQL", "threshold": "10 cs (100 мс)", "why": "SQL запросы к БД"},
        ],
        "estimated_use_duration": "30-60 минут",
        "warnings": [],
    }, ensure_ascii=False)


def _mock_response(text: str) -> Any:
    """Создаёт mock объект anthropic response."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.model = "claude-haiku-4-5"
    return response


# ---------------------------------------------------------------------------
# Тесты: успешная генерация
# ---------------------------------------------------------------------------

class TestGenerateLogcfgSuccess:
    @pytest.mark.asyncio
    async def test_basic_response_parsed(self) -> None:
        """Корректный JSON → правильно десериализованный LogcfgGenerateResponse."""
        req = LogcfgGenerateRequest(problem_description="Тормозит проведение документов")

        mock_response = _mock_response(_make_valid_ai_response())

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert isinstance(result, LogcfgGenerateResponse)
        assert result.config.events.CALL is not None
        assert result.config.events.CALL.enabled is True
        assert result.config.events.CALL.threshold_cs == 100
        assert result.config.events.DBMSSQL is not None
        assert result.config.events.DBMSSQL.threshold_cs == 10
        assert result.config.events.EXCP is not None
        assert result.model_used == "claude-haiku-4-5"
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_explanation_populated(self) -> None:
        """explanation поле заполняется из AI ответа."""
        req = LogcfgGenerateRequest(problem_description="Дедлоки при работе нескольких пользователей")
        mock_response = _mock_response(_make_valid_ai_response())

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert len(result.explanation) > 0
        assert len(result.events_rationale) == 2

    @pytest.mark.asyncio
    async def test_capture_plans_true(self) -> None:
        """capture_plans=true корректно парсится."""
        ai_json = json.dumps({
            "config": {
                "events": {"DBMSSQL": {"enabled": True, "threshold_cs": 10}},
                "capture_plans": True,
                "log_directory": "C:\\1C-TechLog",
                "history_hours": 72,
            },
            "explanation": "С планами запросов.",
            "events_rationale": [],
            "estimated_use_duration": "60 минут",
            "warnings": ["Объём увеличится в 3-4 раза"],
        })
        req = LogcfgGenerateRequest(problem_description="Нужны планы запросов MSSQL")
        mock_response = _mock_response(ai_json)

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert result.config.capture_plans is True
        assert len(result.warnings) == 1

    @pytest.mark.asyncio
    async def test_both_db_events_included(self) -> None:
        """Если dbms=both → AI включает и DBMSSQL и DBPOSTGRS."""
        events = {
            "DBMSSQL": {"enabled": True, "threshold_cs": 10},
            "DBPOSTGRS": {"enabled": True, "threshold_cs": 10},
            "EXCP": {"enabled": True, "threshold_cs": None},
        }
        req = LogcfgGenerateRequest(
            problem_description="Медленные запросы к базе данных",
            dbms="both",
        )
        mock_response = _mock_response(_make_valid_ai_response(events))

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert result.config.events.DBMSSQL is not None
        assert result.config.events.DBPOSTGRS is not None
        assert result.config.events.DBMSSQL.enabled
        assert result.config.events.DBPOSTGRS.enabled

    @pytest.mark.asyncio
    async def test_platform_version_passed_to_prompt(self) -> None:
        """platform_version передаётся в user message."""
        req = LogcfgGenerateRequest(
            problem_description="Тормозит закрытие месяца",
            platform_version="8.3.22",
        )
        mock_response = _mock_response(_make_valid_ai_response())

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await generate_logcfg(req)

        call_args = mock_client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert "8.3.22" in user_content


# ---------------------------------------------------------------------------
# Тесты: фильтрация неизвестных events
# ---------------------------------------------------------------------------

class TestEventFiltering:
    @pytest.mark.asyncio
    async def test_unknown_event_ignored(self) -> None:
        """AI вернул неизвестный event UNKNOWN → игнорируется, не падаем."""
        events = {
            "CALL": {"enabled": True, "threshold_cs": 100},
            "UNKNOWN_FUTURE_EVENT": {"enabled": True, "threshold_cs": 50},
            "EXCP": {"enabled": True, "threshold_cs": None},
        }
        req = LogcfgGenerateRequest(problem_description="Тест неизвестных событий от AI")
        mock_response = _mock_response(_make_valid_ai_response(events))

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        # CALL и EXCP сохранены, UNKNOWN_FUTURE_EVENT проигнорирован.
        assert result.config.events.CALL is not None
        assert result.config.events.EXCP is not None

    @pytest.mark.asyncio
    async def test_disabled_event_not_returned(self) -> None:
        """enabled=false событие не вызывает ошибки."""
        events = {
            "CALL": {"enabled": True, "threshold_cs": 100},
            "DBMSSQL": {"enabled": False, "threshold_cs": 10},
        }
        req = LogcfgGenerateRequest(problem_description="Только CALL события")
        mock_response = _mock_response(_make_valid_ai_response(events))

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert result.config.events.CALL is not None
        assert result.config.events.CALL.enabled is True
        # DBMSSQL есть но disabled
        assert result.config.events.DBMSSQL is not None
        assert result.config.events.DBMSSQL.enabled is False


# ---------------------------------------------------------------------------
# Тесты: обработка ошибок
# ---------------------------------------------------------------------------

class TestGenerateLogcfgErrors:
    @pytest.mark.asyncio
    async def test_no_api_key_raises(self) -> None:
        """Нет API ключа → AiNotConfiguredError."""
        req = LogcfgGenerateRequest(problem_description="Тест без ключа API")

        with patch("services.ai_explainer.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""

            with pytest.raises(AiNotConfiguredError):
                await generate_logcfg(req)

    @pytest.mark.asyncio
    async def test_invalid_json_triggers_retry(self) -> None:
        """Первый ответ — невалидный JSON → retry → успех."""
        req = LogcfgGenerateRequest(problem_description="Тест retry при невалидном JSON")
        good_response = _mock_response(_make_valid_ai_response())
        bad_response = _mock_response("не JSON вообще { broken")

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            # Первый вызов → плохой ответ, второй (retry) → хороший.
            mock_client.messages.create = AsyncMock(
                side_effect=[bad_response, good_response]
            )
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert isinstance(result, LogcfgGenerateResponse)
        assert mock_client.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_invalid_json_both_attempts_raises(self) -> None:
        """Оба ответа невалидный JSON → AiExplainerError."""
        req = LogcfgGenerateRequest(problem_description="Тест двойного сбоя JSON")
        bad_response = _mock_response("не JSON вообще")

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=bad_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(AiExplainerError, match="невалидный JSON.*retry"):
                await generate_logcfg(req)

    @pytest.mark.asyncio
    async def test_empty_events_graceful(self) -> None:
        """AI вернул пустой events dict → не падаем, LogcfgConfig с defaults."""
        ai_json = json.dumps({
            "config": {
                "events": {},
                "capture_plans": False,
                "log_directory": "C:\\1C-TechLog",
                "history_hours": 72,
            },
            "explanation": "Пустая конфигурация.",
            "events_rationale": [],
            "estimated_use_duration": "30 минут",
            "warnings": [],
        })
        req = LogcfgGenerateRequest(problem_description="Минимальная конфигурация для теста")
        mock_response = _mock_response(ai_json)

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        assert isinstance(result, LogcfgGenerateResponse)
        # Все события None (не включены).
        assert result.config.events.CALL is None
        assert result.config.events.DBMSSQL is None

    @pytest.mark.asyncio
    async def test_missing_config_key_graceful(self) -> None:
        """AI не вернул поле config → fallback на defaults, не падаем."""
        ai_json = json.dumps({
            "explanation": "Что-то пошло не так.",
            "events_rationale": [],
            "estimated_use_duration": "30 минут",
            "warnings": [],
        })
        req = LogcfgGenerateRequest(problem_description="Тест отсутствия config")
        mock_response = _mock_response(ai_json)

        with patch("services.ai_explainer.settings") as mock_settings, \
             patch("services.ai_explainer.anthropic.AsyncAnthropic") as mock_client_cls:
            mock_settings.anthropic_api_key = "sk-test"
            mock_settings.ai_request_timeout_s = 30
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await generate_logcfg(req)

        # Defaults из LogcfgConfig.
        assert result.config.log_directory == "C:\\1C-TechLog"
        assert result.config.history_hours == 72


# ---------------------------------------------------------------------------
# Тесты: Pydantic схемы (без моков — unit validation)
# ---------------------------------------------------------------------------

class TestLogcfgSchemas:
    def test_event_config_valid(self) -> None:
        ec = EventConfig(enabled=True, threshold_cs=100)
        assert ec.enabled is True
        assert ec.threshold_cs == 100

    def test_event_config_no_threshold(self) -> None:
        ec = EventConfig(enabled=True)
        assert ec.threshold_cs is None

    def test_event_config_threshold_zero(self) -> None:
        ec = EventConfig(enabled=True, threshold_cs=0)
        assert ec.threshold_cs == 0

    def test_logcfg_config_defaults(self) -> None:
        cfg = LogcfgConfig()
        assert cfg.log_directory == "C:\\1C-TechLog"
        assert cfg.history_hours == 72
        assert cfg.capture_plans is False

    def test_logcfg_events_partial(self) -> None:
        """Можно создать LogcfgEvents только с нужными полями."""
        events = LogcfgEvents(
            CALL=EventConfig(enabled=True, threshold_cs=100),
            EXCP=EventConfig(enabled=True),
        )
        assert events.CALL is not None
        assert events.DBMSSQL is None
        assert events.EXCP is not None

    def test_request_min_length(self) -> None:
        """problem_description min 10 символов."""
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            LogcfgGenerateRequest(problem_description="мало")

    def test_request_valid_dbms_values(self) -> None:
        """Все допустимые значения dbms проходят валидацию."""
        for dbms in ("mssql", "postgres", "both", "unknown"):
            req = LogcfgGenerateRequest(
                problem_description="Достаточно длинное описание проблемы",
                dbms=dbms,  # type: ignore[arg-type]
            )
            assert req.dbms == dbms

    def test_request_dbms_default_unknown(self) -> None:
        req = LogcfgGenerateRequest(problem_description="Описание проблемы производительности")
        assert req.dbms == "unknown"
