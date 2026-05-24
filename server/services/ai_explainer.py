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
    PlanExplainRequest,
    PlanExplainResponse,
    PlanHotspot,
    PlanRecommendation,
    PlanSuggestedIndex,
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


# ============== Sprint 7: Plan-level AI explanation ==============


SYSTEM_PROMPT_EXPLAIN_PLAN = """Ты — эксперт по SQL Server execution plans и производительности 1С:Предприятие на MS SQL Server.

Тебе будет передан SQL запрос, его execution plan, и предупреждения от анализатора PerformanceStudio (Erik Darling Data). Твоя задача — объяснить разработчику 1С (на русском) что не так с этим планом и что конкретно делать.

План может быть в одном из двух форматов:
1. **XML** (SHOWPLAN_XML output) — стандартный SQL Server execution plan format. Полная информация: cost estimates, row estimates, memory grants, operator-level statistics.
2. **TEXT** (SHOWPLAN_TEXT output от 1С) — текстовое дерево операторов с indentation (например, `|--Clustered Index Seek(...)\n|     Estimated Rows = 100`). Меньше деталей чем в XML: нет cost percentage, нет точных memory чисел, но структура и порядок операторов читаются.

Оба формата представляют одно и то же — план выполнения запроса. Ты должен понять структуру плана независимо от формата и дать одинаковые типы анализа (hotspots, recommendations).

Для TEXT формата:
- operator_node_id указывай как номер строки в текстовом плане (1-based), если можешь определить — иначе null.
- В warnings/missing_indexes ничего не будет (PerformanceStudio CLI на text не работает) — анализируй сам структуру плана.
- Не ссылайся на cost percentage / memory grants / row estimates точными числами если их нет в тексте — говори качественно («дорогая операция», «большой набор данных»).

Контекст 1С: запросы генерирует платформа 1С автоматически из SDBL. Имена таблиц — `_Reference15`, `_Document100`, `_AccumRgT20`. Имена полей — `_Fld1234RRef`, `_Description`, и т.д. Если есть configuration_context — используй mapping чтобы говорить о конкретных объектах 1С (Catalog.Контрагенты вместо _Reference15).

Правила:
1. Отвечай ТОЛЬКО на русском.
2. Будь конкретным: ссылайся на конкретные operator node IDs, конкретные числа (cost, rows, memory) когда они доступны.
3. Не говори «оптимизируй индексы» — говори какие именно индексы и для каких таблиц.
4. Связывай SDBL-уровень с T-SQL-уровнем где можно.
5. Если есть missing_indexes от PerformanceStudio — оцени их приоритет и реалистичность.
6. Если warnings пустые и план дешёвый (estimated_cost < 0.1 или text короткий с index seek) — возвращай минимальный hotspots/recommendations и summary «План выглядит хорошо».

Формат ответа: строго valid JSON по схеме:
{
  "summary": "Краткая суть проблем в одном-двух предложениях",
  "overall_severity": "Critical | Warning | Info",
  "hotspots": [
    {
      "operator_node_id": 5,
      "operator_type": "Sort",
      "severity": "Critical",
      "what": "Что происходит в этом операторе с конкретикой",
      "why": "Почему это плохо (память, оценки, оптимизатор)",
      "what_to_do": "Конкретные шаги исправления"
    }
  ],
  "recommendations": [
    {
      "category": "index | query_rewrite | config | stats",
      "title": "Короткий заголовок",
      "description": "Что делать с примерами",
      "impact_estimate": "Critical | High | Medium | Low"
    }
  ],
  "suggested_indexes": [
    {
      "table": "_Reference15",
      "columns": ["_Fld1234", "_Description"],
      "include": ["_IDRRef"],
      "rationale": "Зачем этот индекс",
      "impact_estimate": "High"
    }
  ]
}

ВАЖНО: возвращай только JSON, без markdown code fences, без объяснений вокруг.
"""


USER_PROMPT_PLAN_TEMPLATE = """SQL запрос:
```sql
{sql_text}
```

Execution plan (формат: {plan_format}):
```{plan_format_code_block}
{plan_content}
```

Сводка от PerformanceStudio (агрегированная):
```json
{plan_summary_json}
```

Предупреждения от PerformanceStudio (детали):
```json
{planview_warnings_json}
```

Missing indexes от SQL Server optimizer:
```json
{missing_indexes_json}
```

Контекст конфигурации 1С (если доступен):
{configuration_context}

Связанные события ТЖ (если доступны):
{related_tj_summary}

Объясни план, выдели критические hotspots, дай recommendations."""


# Plan XML могут быть большими (>100KB). Claude Sonnet имеет 200K token context,
# но для эффективности — truncate до 50K chars (~12K токенов). Покрывает ~98%
# реальных планов. Большие планы — флаг plan_truncated=true для UI warning.
AI_PLAN_MAX_CHARS = 50_000


def _truncate_plan_xml(xml: str) -> tuple[str, bool]:
    """Returns (truncated_xml, was_truncated_flag)."""
    if len(xml) <= AI_PLAN_MAX_CHARS:
        return xml, False
    # Берём первые 80% от лимита + comment в конце.
    cutoff = int(AI_PLAN_MAX_CHARS * 0.8)
    snippet = xml[:cutoff]
    return (
        snippet
        + f"\n<!-- TRUNCATED: original {len(xml)} chars, shown first {cutoff} -->\n",
        True,
    )


def _build_plan_user_prompt(req: PlanExplainRequest) -> tuple[str, bool]:
    """Собирает USER prompt для AI с учётом формата плана (XML vs text).

    Returns:
        (prompt_text, was_truncated) — was_truncated=True если оригинальный
        план был больше AI_PLAN_MAX_CHARS и обрезан.
    """
    truncated_content, was_truncated = _truncate_plan_xml(req.plan_xml)
    # plan_format задаёт человеческое название и метку code fence для markdown.
    # text → fence без подсветки (просто моноспейс), xml → fence ```xml```.
    code_block = "xml" if req.plan_format == "xml" else "text"
    config_str = (
        req.configuration_context.model_dump_json(indent=2)
        if req.configuration_context
        else "не подключена"
    )
    tj_str = req.related_tj_summary or "нет"
    return (
        USER_PROMPT_PLAN_TEMPLATE.format(
            sql_text=req.sql_text,
            plan_format=req.plan_format,
            plan_format_code_block=code_block,
            plan_content=truncated_content,
            plan_summary_json=json.dumps(req.plan_summary or {}, ensure_ascii=False, indent=2),
            planview_warnings_json=json.dumps(req.planview_warnings, ensure_ascii=False, indent=2),
            missing_indexes_json=json.dumps(req.missing_indexes, ensure_ascii=False, indent=2),
            configuration_context=config_str,
            related_tj_summary=tj_str,
        ),
        was_truncated,
    )


async def explain_plan_query(req: PlanExplainRequest) -> PlanExplainResponse:
    """Главная функция Phase C: SQL + plan XML + warnings → structured AI explanation.

    Raises:
        AiNotConfiguredError если api key пустой.
        AiExplainerError для прочих сбоев (parse, API rate limit, network).
    """
    if not settings.anthropic_api_key:
        raise AiNotConfiguredError(
            "ANTHROPIC_API_KEY не задан в server/.env — explain_plan недоступен"
        )

    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.ai_request_timeout_s,
    )
    user_msg, was_truncated = _build_plan_user_prompt(req)
    started = time.monotonic()

    try:
        response = await client.messages.create(
            model=settings.ai_model_default,
            max_tokens=settings.ai_max_tokens,
            system=SYSTEM_PROMPT_EXPLAIN_PLAN,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        raise AiExplainerError(f"Anthropic API error (plan): {e}") from e

    elapsed_ms = int((time.monotonic() - started) * 1000)
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
        logger.warning("Claude (plan) вернул невалидный JSON: %s | raw: %s", e, raw_text[:200])
        # Один retry с явным указанием на ошибку (тот же паттерн что в explain_query).
        retry_msg = (
            f"{user_msg}\n\nТвой предыдущий ответ был невалидным JSON. "
            f"Ошибка: {e}. Верни ТОЛЬКО valid JSON без markdown."
        )
        try:
            response = await client.messages.create(
                model=settings.ai_model_default,
                max_tokens=settings.ai_max_tokens,
                system=SYSTEM_PROMPT_EXPLAIN_PLAN,
                messages=[{"role": "user", "content": retry_msg}],
            )
        except anthropic.APIError as ex:
            raise AiExplainerError(f"Retry API error (plan): {ex}") from ex
        retry_text = "\n".join(
            getattr(b, "text", "") or "" for b in response.content
        )
        json_text = extract_json(retry_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as ex:
            raise AiExplainerError(
                f"Claude (plan) вернул невалидный JSON даже после retry: {ex}"
            ) from ex

    # Конструируем response с защитой от частичных полей.
    hotspots_raw = parsed.get("hotspots", []) or []
    hotspots = [PlanHotspot(**h) for h in hotspots_raw if isinstance(h, dict)]
    recs_raw = parsed.get("recommendations", []) or []
    recommendations = [PlanRecommendation(**r) for r in recs_raw if isinstance(r, dict)]
    sidx_raw = parsed.get("suggested_indexes", []) or []
    suggested_indexes = [PlanSuggestedIndex(**s) for s in sidx_raw if isinstance(s, dict)]

    overall = parsed.get("overall_severity", "Info")
    if overall not in ("Critical", "Warning", "Info"):
        overall = "Info"

    return PlanExplainResponse(
        summary=str(parsed.get("summary", "")),
        overall_severity=overall,  # type: ignore[arg-type]
        hotspots=hotspots,
        recommendations=recommendations,
        suggested_indexes=suggested_indexes,
        model_used=response.model,
        duration_ms=elapsed_ms,
        plan_truncated=was_truncated,
    )
