"""AI orchestration для /v1/ai/explain (Sprint 6 Phase D).

Минимальная реализация — без auth, caching, multi-model routing (это всё
прийдёт в Phase 1 INFRA параллельно). В Sprint 6 endpoint обслуживает
desktop-приложение Сергея локально для разработки.

Структура prompts:
  SYSTEM — роль AI + правила формата + JSON schema
  USER — данные запроса + диагностики + контекст

Ожидаемый Claude output — strict JSON с полями из ExplainResponse.
Защита от невалидного JSON — extract_json + одна попытка retry.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import anthropic

from api.settings import settings
from schemas.ai import (
    ExplainRequest,
    ExplainResponse,
    IssueExplanation,
    SuggestedRewrite,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_EXPLAIN = """Ты — эксперт по производительности 1С:Предприятие и SDBL запросам. Объясняешь разработчику 1С проблемы в его запросе понятным русским языком.

Правила:
1. Отвечай ТОЛЬКО на русском языке.
2. Будь конкретным: ссылайся на конкретные строки кода и значения, а не общими фразами.
3. Не давай советов вроде «оптимизируй запрос» — давай actionable шаги с примером кода.
4. Группируй связанные проблемы вместе (если две диагностики срабатывают на одно место — один issue с двумя linked_diagnostic_codes).
5. Если переписывание запроса даст значимый прирост — предложи suggested_rewrite с конкретным SDBL.
6. Не пиши маркетинг ("ваш запрос великолепен"). Будь как сеньор-ревьюер.

Формат ответа: строго valid JSON по схеме:
{
  "explanation_summary": "Краткая суть проблем в одном предложении (или 'Проблем не найдено' если diagnostics пустой)",
  "issues": [
    {
      "title": "Короткое название проблемы (5-7 слов)",
      "severity": "Blocker | Critical | Major | Minor | Info",
      "what": "Что именно происходит в коде с цитатой проблемного фрагмента",
      "why": "Почему это плохо технически (план запроса, оптимизатор, индексы, временные таблицы)",
      "what_to_do": "Конкретные шаги исправления с примером кода",
      "linked_diagnostic_codes": ["RefOveruse", "..."]
    }
  ],
  "suggested_rewrite": {
    "available": true,
    "sdbl": "переписанный SDBL запрос целиком",
    "reasoning": "что и почему изменено"
  }
}

Если ни одной проблемы нет — issues = [] и suggested_rewrite.available = false.
Если diagnostics пустой — issues = [] и summary "Проблем не найдено".
ВАЖНО: возвращай только JSON, без markdown code fences, без объяснений вокруг.
"""


USER_PROMPT_TEMPLATE = """Запрос SDBL:
```sdbl
{sdbl}
```

Диагностики от bsl-language-server (количество: {diag_count}):
```json
{diagnostics_json}
```

Контекст конфигурации (используемые объекты):
```json
{config_json}
```

Объясни проблемы и предложи переписывание если оно даст эффект."""


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> str:
    """Очищает Claude output от markdown fences если они есть."""
    cleaned = _JSON_FENCE_RE.sub("", text).strip()
    # Если в начале есть префикс типа "Вот JSON:" — берём от первой {
    if not cleaned.startswith("{"):
        idx = cleaned.find("{")
        if idx >= 0:
            cleaned = cleaned[idx:]
    # И до последней }
    if not cleaned.endswith("}"):
        idx = cleaned.rfind("}")
        if idx >= 0:
            cleaned = cleaned[: idx + 1]
    return cleaned


def _build_user_prompt(req: ExplainRequest) -> str:
    diagnostics_serializable: list[dict[str, Any]] = [d.model_dump() for d in req.diagnostics]
    config = req.configuration_context.model_dump() if req.configuration_context else {}
    return USER_PROMPT_TEMPLATE.format(
        sdbl=req.query_sdbl,
        diag_count=len(req.diagnostics),
        diagnostics_json=json.dumps(diagnostics_serializable, ensure_ascii=False, indent=2),
        config_json=json.dumps(config, ensure_ascii=False, indent=2),
    )


class AiExplainerError(RuntimeError):
    """Базовая ошибка orchestrator'а."""


class AiNotConfiguredError(AiExplainerError):
    """ANTHROPIC_API_KEY не задан в settings."""


async def explain_query(req: ExplainRequest) -> ExplainResponse:
    """Главная функция: SDBL + diagnostics → structured explanation от Claude.

    Raises:
        AiNotConfiguredError если api key пустой.
        AiExplainerError для прочих сбоев (parse, API rate limit, network).
    """
    if not settings.anthropic_api_key:
        raise AiNotConfiguredError(
            "ANTHROPIC_API_KEY не задан в server/.env — Phase D работает в dev-mode"
        )

    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.ai_request_timeout_s,
    )
    user_msg = _build_user_prompt(req)
    started = time.monotonic()

    try:
        response = await client.messages.create(
            model=settings.ai_model_default,
            max_tokens=settings.ai_max_tokens,
            system=SYSTEM_PROMPT_EXPLAIN,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        raise AiExplainerError(f"Anthropic API error: {e}") from e

    elapsed_ms = int((time.monotonic() - started) * 1000)
    # Claude возвращает content как list of TextBlock — берём первый текстовый.
    text_parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            text_parts.append(text)
    raw_text = "\n".join(text_parts)
    json_text = extract_json(raw_text)

    try:
        parsed: dict[str, Any] = json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.warning("Claude вернул невалидный JSON: %s | raw: %s", e, raw_text[:200])
        # Один retry с явным указанием на ошибку.
        retry_msg = (
            f"{user_msg}\n\nТвой предыдущий ответ был невалидным JSON. "
            f"Ошибка: {e}. Верни ТОЛЬКО valid JSON без markdown."
        )
        try:
            response = await client.messages.create(
                model=settings.ai_model_default,
                max_tokens=settings.ai_max_tokens,
                system=SYSTEM_PROMPT_EXPLAIN,
                messages=[{"role": "user", "content": retry_msg}],
            )
        except anthropic.APIError as ex:
            raise AiExplainerError(f"Retry API error: {ex}") from ex
        retry_text = "\n".join(
            getattr(b, "text", "") or "" for b in response.content
        )
        json_text = extract_json(retry_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as ex:
            raise AiExplainerError(
                f"Claude вернул невалидный JSON даже после retry: {ex}"
            ) from ex

    # Конструируем response.
    issues_raw = parsed.get("issues", [])
    issues = [IssueExplanation(**i) for i in issues_raw if isinstance(i, dict)]
    rewrite_raw = parsed.get("suggested_rewrite", {})
    if not isinstance(rewrite_raw, dict):
        rewrite_raw = {}
    rewrite = SuggestedRewrite(**rewrite_raw)

    return ExplainResponse(
        explanation_summary=str(parsed.get("explanation_summary", "")),
        issues=issues,
        suggested_rewrite=rewrite,
        model_used=response.model,
        duration_ms=elapsed_ms,
    )
