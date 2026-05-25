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
    EventRationale,
    ExplainRequest,
    ExplainResponse,
    IssueExplanation,
    LogcfgConfig,
    LogcfgEvents,
    LogcfgGenerateRequest,
    LogcfgGenerateResponse,
    PlanExplainRequest,
    PlanExplainResponse,
    PlanHotspot,
    PlanRecommendation,
    PlanSuggestedIndex,
    SuggestedRewrite,
)

logger = logging.getLogger(__name__)


# ============== Sprint 9 Phase D: Generic AI enum normalizer ==============


def normalize_ai_enum(
    value: Any,
    mapping: dict[str, str],
    default: str,
    field_name: str = "enum",
) -> str:
    """Normalize AI-returned enum values to schema-valid options.

    AI иногда возвращает нестандартные значения enum (например, 'High' вместо
    'Critical', 'Moderate' вместо 'Warning'). Эта функция нормализует их через
    mapping, с fallback на default.

    Args:
        value: значение из AI response (может быть любого типа)
        mapping: lowercased input -> valid output
        default: fallback если не нашли в mapping
        field_name: для logging (помогает при дебаге)

    Returns:
        valid enum value из mapping или default
    """
    if not isinstance(value, str):
        logger.warning("AI returned non-string %s: %r (type=%s)", field_name, value, type(value).__name__)
        return default
    normalized = value.lower().strip()
    result = mapping.get(normalized, None)
    if result is None:
        logger.info("AI returned unknown %s %r, falling back to %r", field_name, value, default)
        return default
    return result


# Predefined severity mapping: AI-возвращаемые варианты -> canonical
SEVERITY_MAPPING: dict[str, str] = {
    "critical": "Critical",
    "high": "Critical",
    "blocker": "Critical",
    "error": "Critical",
    "warning": "Warning",
    "medium": "Warning",
    "moderate": "Warning",
    "warn": "Warning",
    "info": "Info",
    "low": "Info",
    "minor": "Info",
    "informational": "Info",
}

# Impact mapping для recommendations/suggested_indexes
IMPACT_MAPPING: dict[str, str] = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "minor": "Low",
}


# ============ end Sprint 9 Phase D ============


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


SYSTEM_PROMPT_EXPLAIN_MSSQL_PLAN = """Ты — эксперт по SQL Server execution plans и производительности 1С:Предприятие на MS SQL Server.

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


USER_PROMPT_MSSQL_PLAN_TEMPLATE = """SQL запрос:
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
        USER_PROMPT_MSSQL_PLAN_TEMPLATE.format(
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


# ============== Sprint 8 Phase B — PostgreSQL plan prompts ==============


SYSTEM_PROMPT_EXPLAIN_PG_PLAN = """Ты — эксперт по PostgreSQL execution plans и производительности 1С:Предприятие на PostgreSQL.

ВАЖНЫЙ КОНТЕКСТ: 1С работает с PostgreSQL через **специальную сборку от фирмы 1С** (`PostgreSQL <ver>-2.1C`). Эта сборка имеет несколько критических особенностей которые нужно учитывать при анализе плана:

1. **`SET enable_mergejoin = off`** — 1С автоматически выполняет эту команду при каждом connect. Это значит: **НЕ рекомендуй переключение на Merge Join** — он технически отключён. Альтернативы: Hash Join (для больших equi-joins) или Nested Loop (для маленьких outer).

2. **`SET cpu_operator_cost = 0.001`** (5× меньше PG default 0.005). Это значит: cost numbers в плане **меньше** чем были бы в стандартном PG. Не сравнивай cost напрямую с типовыми "плохой план если cost > X" thresholds — учитывай этот scaling.

3. **`SET lock_timeout = 20000`** (20 секунд). Lock waits до 20 сек — нормальная ситуация в 1С-PG.

4. **Custom типы 1С:** `mchar(N)` (case-insensitive CHAR), `mvarchar(N)` (multi-byte VARCHAR), `fulleq` (точное равенство для NULL handling). Если в плане видишь `Filter: (..._fld100)::mvarchar = $1::mvarchar` — это **нормально** для 1С, не implicit cast antipattern.

5. **Naming convention 1С таблиц в PG (все lowercase, prefix-based):**
   - `_reference15` = Catalog (Справочник). Если есть configuration_context — резолвить в имя ("Справочник.Контрагенты")
   - `_document201` = Document (Документ)
   - `_accumrg7406` = AccumulationRegister (Регистр накопления)
   - `_inforg20917` = InformationRegister (Регистр сведений)
   - `_accrged7859` = CalculationRegisterTotalsForRefMD ("движения с расширенным агрегатом")
   - `_seq18593` = Sequence (Sequence для номеров документов)
   - `_fld11355` — это **Data Separator** (разделитель данных). Каждый индекс начинается с него. Если в плане видишь фильтр `_fld11355 = X` — это просто отбор по области данных, не проблема.
   - `_rref` суффикс — Reference (ссылка) на другую таблицу
   - `_idrref` — primary key, UUID 16 байт

6. **PostgreSQL EXPLAIN format отличия от MSSQL:**
   - Операторы: `Seq Scan`, `Index Scan`, `Index Only Scan`, `Bitmap Heap Scan`, `Hash Join`, `Nested Loop`, `Sort`, `Aggregate`, `Memoize` (с PG 14), `Limit`, `Append`, `Gather` (parallel)
   - Cost format: `(cost=startup..total rows=N width=N)`
   - Runtime: `(actual time=startup..total rows=N.NN loops=N)`
   - `Filter:` / `Index Cond:` / `Recheck Cond:` / `Hash Cond:` — predicates
   - `Rows Removed by Filter: N` — сколько строк сканировалось но отброшено фильтром (если N большое — antipattern)
   - `Heap Fetches: N` — для Index Only Scan, fetches к heap (если > 0 — VACUUM нужен)
   - `Buffers: shared hit=N read=N` — I/O (read = миссии в buffer cache)

7. **Что искать как antipatterns (специфика PG для 1С):**
   - **Plan Rows × Actual Rows divergence > 10×** — устаревшая статистика (нужен ANALYZE)
   - **Seq Scan на больших таблицах когда есть Index** — оптимизатор не выбрал индекс (статистика? cardinality? SARGable predicate?)
   - **Nested Loop с большим outer (> 10000 rows)** — обычно нужен Hash Join (но в 1С Merge Join выключен, так что у тебя только Hash Join как альтернатива)
   - **Sort с `Sort Method: external merge`** — work_mem мало, спилит на диск
   - **Memoize с низким hit rate** — кэш не работает, проверить параметры
   - **`Rows Removed by Filter: large`** — predicate не SARGable
   - **Heap Fetches > 0 в Index Only Scan** — нужен VACUUM таблицы
   - **Bitmap Heap Scan с большим Recheck** — индекс плохо selective

Задача: объясни план разработчику 1С на **русском** языке. Будь конкретным — ссылайся на конкретные строки/operators, конкретные числа из плана.

Если есть configuration_context — используй mapping чтобы говорить о бизнес-объектах 1С (Справочник.Контрагенты вместо _reference15).

Формат ответа: строго valid JSON по схеме:
{
  "summary": "Краткая суть проблем в одном-двух предложениях",
  "overall_severity": "Critical | Warning | Info",
  "hotspots": [
    {
      "operator_node_id": null,
      "operator_type": "Seq Scan / Hash Join / Memoize / ...",
      "severity": "Critical | Warning | Info",
      "what": "Что происходит конкретно с цитатой/числами",
      "why": "Почему это плохо технически",
      "what_to_do": "Конкретные шаги для разработчика 1С"
    }
  ],
  "recommendations": [
    {
      "category": "index | query_rewrite | config | stats",
      "title": "Короткий заголовок",
      "description": "Конкретные действия",
      "impact_estimate": "Critical | High | Medium | Low"
    }
  ],
  "suggested_indexes": [
    {
      "table": "_document201",
      "columns": ["_fld11355", "_fld5326rref"],
      "include": [],
      "rationale": "Зачем",
      "impact_estimate": "High"
    }
  ]
}

ВАЖНО:
- Возвращай только JSON, без markdown code fences, без объяснений вокруг.
- НИКОГДА не предлагай Merge Join — он отключён 1С через `enable_mergejoin = off`.
- Используй lowercase имена таблиц как в PG (`_document201`, не `_Document201`).

## Detected SQL Antipatterns (Sprint 8 Phase C)

Если в request передан `detected_antipatterns` (список найденных локально через sqlglot) — **используй его как стартовую точку** для своего анализа:
- **НЕ дублируй** их как hotspots — они уже найдены, юзер уже видит их в отдельной карточке UI
- **Расширяй с конкретикой плана** — например antipattern говорит "OFFSET без LIMIT", ты можешь дополнить: "в плане видно Seq Scan на _document201 — это особенно плохо для большой таблицы при OFFSET 50000"
- Если antipattern помечен `is_1c_context_only=true` — учитывай 1С-специфику в recommendations
- В recommendations можешь дать дополнительные шаги (например для `large_offset_pagination` → предложить keyset pagination с конкретным `WHERE id > $last_id` для таблицы из плана)
"""


USER_PROMPT_PG_PLAN_TEMPLATE = """SQL запрос (PostgreSQL):
```sql
{sql_text}
```

PostgreSQL execution plan ({plan_format} format):
```{plan_format_code_block}
{plan_content}
```

Контекст конфигурации 1С (если доступен):
{configuration_context}

Связанные события ТЖ (если доступны):
{related_tj_summary}

Уже обнаруженные локально антипаттерны (от sqlglot engine):
{detected_antipatterns}

Эта база работает на PostgreSQL 1С-сборке. Стандартные SET-команды клиента (применяются автоматически 1С при каждом connect):
- SET enable_mergejoin = off   (Merge Join отключён — не рекомендовать)
- SET cpu_operator_cost = 0.001 (cost numbers в 5× меньше PG default)
- SET lock_timeout = 20000      (20-сек таймаут блокировок — норма)

Объясни план, выдели критические hotspots (НЕ дублируй уже обнаруженные антипаттерны), дай recommendations с конкретными шагами для разработчика 1С."""


def _build_pg_plan_user_prompt(req: PlanExplainRequest) -> tuple[str, bool]:
    """Собирает USER prompt для PG plan AI.

    Returns:
        (prompt_text, was_truncated)
    """
    truncated_content, was_truncated = _truncate_plan_xml(req.plan_xml)
    # plan_format для PG: "text" (EXPLAIN ANALYZE TEXT) или "json" (FORMAT JSON).
    # MSSQL xml сюда не приходит (engine dispatcher отсеет).
    code_block = "json" if req.plan_format == "json" else "text"
    config_str = (
        req.configuration_context.model_dump_json(indent=2)
        if req.configuration_context
        else "не подключена"
    )
    tj_str = req.related_tj_summary or "нет"
    # Sprint 8 Phase C — форматируем detected_antipatterns в bullet list.
    if req.detected_antipatterns:
        antipatterns_lines = []
        for ap in req.detected_antipatterns:
            code = ap.get("code", "?")
            title = ap.get("title", "")
            severity = ap.get("severity", "?")
            desc = ap.get("description", "")
            rec = ap.get("recommendation", "")
            is_1c = ap.get("is_1c_context_only", False)
            ctx = " (1С-context)" if is_1c else ""
            antipatterns_lines.append(
                f"- [{severity}] **{code}**: {title}{ctx}\n  {desc}\n  Что делать: {rec}"
            )
        antipatterns_str = "\n".join(antipatterns_lines)
    else:
        antipatterns_str = "нет"
    return (
        USER_PROMPT_PG_PLAN_TEMPLATE.format(
            sql_text=req.sql_text,
            plan_format=req.plan_format,
            plan_format_code_block=code_block,
            plan_content=truncated_content,
            configuration_context=config_str,
            related_tj_summary=tj_str,
            detected_antipatterns=antipatterns_str,
        ),
        was_truncated,
    )


async def explain_plan_query(req: PlanExplainRequest) -> PlanExplainResponse:
    """Главная функция: SQL + plan + warnings → structured AI explanation.

    Sprint 8 Phase B: dispatcher по engine —
        engine='mssql' → explain_mssql_plan() (Sprint 7 logic, MSSQL prompts)
        engine='postgres' → explain_pg_plan() (PG prompts + 1С-specific knowledge)

    Raises:
        AiNotConfiguredError если api key пустой.
        AiExplainerError для прочих сбоев (parse, API rate limit, network).
    """
    if req.engine == "postgres":
        return await explain_pg_plan(req)
    return await explain_mssql_plan(req)


async def explain_mssql_plan(req: PlanExplainRequest) -> PlanExplainResponse:
    """MSSQL plan AI — SHOWPLAN_XML или SHOWPLAN_TEXT. Sprint 7 Phase C/D pattern."""
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
            system=SYSTEM_PROMPT_EXPLAIN_MSSQL_PLAN,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        raise AiExplainerError(f"Anthropic API error (mssql plan): {e}") from e

    return await _process_plan_response(
        response=response,
        started=started,
        was_truncated=was_truncated,
        system_prompt=SYSTEM_PROMPT_EXPLAIN_MSSQL_PLAN,
        user_msg=user_msg,
        client=client,
        engine_label="mssql",
    )


async def explain_pg_plan(req: PlanExplainRequest) -> PlanExplainResponse:
    """PostgreSQL plan AI — EXPLAIN ANALYZE TEXT или FORMAT JSON.

    Sprint 8 Phase B — отдельный prompt со знанием 1С-PG-сборки:
    enable_mergejoin=off, cpu_operator_cost=0.001, mchar/mvarchar, lowercase
    naming, etc. Подробности — SYSTEM_PROMPT_EXPLAIN_PG_PLAN.
    """
    if not settings.anthropic_api_key:
        raise AiNotConfiguredError(
            "ANTHROPIC_API_KEY не задан в server/.env — explain_plan недоступен"
        )

    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.ai_request_timeout_s,
    )
    user_msg, was_truncated = _build_pg_plan_user_prompt(req)
    started = time.monotonic()

    try:
        response = await client.messages.create(
            model=settings.ai_model_default,
            max_tokens=settings.ai_max_tokens,
            system=SYSTEM_PROMPT_EXPLAIN_PG_PLAN,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        raise AiExplainerError(f"Anthropic API error (pg plan): {e}") from e

    return await _process_plan_response(
        response=response,
        started=started,
        was_truncated=was_truncated,
        system_prompt=SYSTEM_PROMPT_EXPLAIN_PG_PLAN,
        user_msg=user_msg,
        client=client,
        engine_label="postgres",
    )


async def _process_plan_response(
    *,
    response: Any,
    started: float,
    was_truncated: bool,
    system_prompt: str,
    user_msg: str,
    client: Any,
    engine_label: str,
) -> PlanExplainResponse:
    """Общий post-processing для MSSQL/PG plan AI responses.

    Извлекает JSON, делает retry если невалидный, строит PlanExplainResponse.
    Логика идентична для обоих движков — только prompt отличается.
    """
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
        logger.warning(
            "Claude (%s plan) вернул невалидный JSON: %s | raw: %s",
            engine_label, e, raw_text[:200],
        )
        retry_msg = (
            f"{user_msg}\n\nТвой предыдущий ответ был невалидным JSON. "
            f"Ошибка: {e}. Верни ТОЛЬКО valid JSON без markdown."
        )
        try:
            response = await client.messages.create(
                model=settings.ai_model_default,
                max_tokens=settings.ai_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": retry_msg}],
            )
        except anthropic.APIError as ex:
            raise AiExplainerError(f"Retry API error ({engine_label} plan): {ex}") from ex
        retry_text = "\n".join(
            getattr(b, "text", "") or "" for b in response.content
        )
        json_text = extract_json(retry_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as ex:
            raise AiExplainerError(
                f"Claude ({engine_label} plan) вернул невалидный JSON даже после retry: {ex}"
            ) from ex

    # Нормализуем severity — AI иногда возвращает 'High'/'Medium'/'Low'
    # вместо 'Critical'/'Warning'/'Info'. Используем generic normalizer (Sprint 9 Phase D).
    def _norm_sev(h: dict) -> dict:
        h = dict(h)
        h["severity"] = normalize_ai_enum(h.get("severity", "Info"), SEVERITY_MAPPING, "Info", "hotspot.severity")
        return h

    def _norm_impact(obj: dict) -> dict:
        obj = dict(obj)
        if "impact_estimate" in obj:
            obj["impact_estimate"] = normalize_ai_enum(
                obj.get("impact_estimate", "Low"), IMPACT_MAPPING, "Low", "impact_estimate"
            )
        return obj

    hotspots_raw = parsed.get("hotspots", []) or []
    hotspots = [PlanHotspot(**_norm_sev(h)) for h in hotspots_raw if isinstance(h, dict)]
    recs_raw = parsed.get("recommendations", []) or []
    recommendations = [PlanRecommendation(**_norm_impact(r)) for r in recs_raw if isinstance(r, dict)]
    sidx_raw = parsed.get("suggested_indexes", []) or []
    suggested_indexes = [PlanSuggestedIndex(**_norm_impact(s)) for s in sidx_raw if isinstance(s, dict)]

    overall = normalize_ai_enum(
        parsed.get("overall_severity", "Info"), SEVERITY_MAPPING, "Info", "overall_severity"
    )

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


# ============== Sprint 10: TJ Config Builder AI ==============

# Модель — Haiku (convention «Haiku везде» для коротких структурированных задач).
AI_MODEL_LOGCFG = "claude-haiku-4-5"

SYSTEM_PROMPT_LOGCFG = """Ты — эксперт по технологическому журналу 1С:Предприятие. Юзер описывает проблему производительности, ты предлагаешь оптимальную настройку logcfg.xml в виде structured JSON.

Принципы:
1. Минимум events — только то что нужно для конкретной проблемы юзера.
2. Правильные пороги — чтобы не было ни overload, ни пропуска данных.
3. Detect движок БД из описания (MSSQL / PostgreSQL). Если не понятно — включи оба DBMSSQL + DBPOSTGRS.
4. Учитывай объём — предупреждай если settings приведут к большому файлу (> 500 МБ/час).

Пороги указываются в centiseconds (1 cs = 10 ms). Типичные значения:
- 100 cs = 1 секунда (для CALL, TLOCK)
- 10 cs = 100 ms (для DBMSSQL/DBPOSTGRS)
- 0 cs = все события без фильтра (для TDEADLOCK, EXCP — редких событий)

Возвращай строго valid JSON по схеме — и ТОЛЬКО JSON, без markdown fences, без пояснений вокруг:
{
  "config": {
    "events": {
      "CALL": {"enabled": true, "threshold_cs": 100},
      "DBMSSQL": {"enabled": true, "threshold_cs": 10},
      "EXCP": {"enabled": true, "threshold_cs": null}
    },
    "capture_plans": false,
    "log_directory": "C:\\\\1C-TechLog",
    "max_size_gb": 10
  },
  "explanation": "Краткое объяснение почему такая настройка подходит",
  "events_rationale": [
    {"event": "DBMSSQL", "threshold": "10 cs (100 мс)", "why": "Нужно ловить медленные запросы к БД"}
  ],
  "estimated_use_duration": "Собирать 30-60 минут с активной нагрузкой",
  "warnings": ["Если у вас мало места на диске — снизьте threshold для DBMSSQL до 100 cs"]
}"""

USER_PROMPT_LOGCFG_TEMPLATE = """Описание проблемы производительности:
{problem_description}

Известная информация о среде:
- Версия 1С: {platform_version}
- СУБД: {dbms}

Предложи оптимальную настройку logcfg.xml для сбора технологического журнала."""


async def generate_logcfg(req: LogcfgGenerateRequest) -> LogcfgGenerateResponse:
    """Sprint 10: генерация настройки logcfg.xml через Haiku по описанию проблемы.

    Raises:
        AiNotConfiguredError если ANTHROPIC_API_KEY не задан.
        AiExplainerError для прочих сбоев.
    """
    if not settings.anthropic_api_key:
        raise AiNotConfiguredError(
            "ANTHROPIC_API_KEY не задан в server/.env — generate_logcfg недоступен"
        )

    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.ai_request_timeout_s,
    )
    user_msg = USER_PROMPT_LOGCFG_TEMPLATE.format(
        problem_description=req.problem_description,
        platform_version=req.platform_version or "не указана",
        dbms=req.dbms or "не указана",
    )
    started = time.monotonic()

    try:
        response = await client.messages.create(
            model=AI_MODEL_LOGCFG,
            max_tokens=2000,
            system=SYSTEM_PROMPT_LOGCFG,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        raise AiExplainerError(f"Anthropic API error (generate_logcfg): {e}") from e

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
        logger.warning("Haiku вернул невалидный JSON (logcfg): %s | raw: %s", e, raw_text[:200])
        retry_msg = (
            f"{user_msg}\n\nТвой предыдущий ответ был невалидным JSON. "
            f"Ошибка: {e}. Верни ТОЛЬКО valid JSON без markdown."
        )
        try:
            response = await client.messages.create(
                model=AI_MODEL_LOGCFG,
                max_tokens=2000,
                system=SYSTEM_PROMPT_LOGCFG,
                messages=[{"role": "user", "content": retry_msg}],
            )
        except anthropic.APIError as ex:
            raise AiExplainerError(f"Retry API error (logcfg): {ex}") from ex
        retry_text = "\n".join(getattr(b, "text", "") or "" for b in response.content)
        json_text = extract_json(retry_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as ex:
            raise AiExplainerError(
                f"Haiku вернул невалидный JSON (logcfg) даже после retry: {ex}"
            ) from ex

    # Строим LogcfgConfig из parsed["config"].
    # AI может вернуть неполные / лишние поля — обрабатываем gracefully.
    config_raw = parsed.get("config", {})
    if not isinstance(config_raw, dict):
        config_raw = {}

    events_raw = config_raw.get("events", {})
    if not isinstance(events_raw, dict):
        events_raw = {}

    # Фильтруем только известные event типы (ignore неизвестных от AI).
    known_events = {
        "CALL", "SCALL", "SDBL", "DBMSSQL", "DBPOSTGRS",
        "TDEADLOCK", "TLOCK", "EXCP", "EXCPCNTX",
        "ADMIN", "MEM", "ATTN", "TTIMEOUT",
    }
    clean_events: dict[str, Any] = {}
    for ev_name, ev_val in events_raw.items():
        if ev_name not in known_events:
            logger.info("AI вернул неизвестный event %r — игнорируем", ev_name)
            continue
        if isinstance(ev_val, dict):
            enabled = bool(ev_val.get("enabled", False))
            threshold_raw = ev_val.get("threshold_cs")
            threshold = int(threshold_raw) if isinstance(threshold_raw, (int, float)) else None
            clean_events[ev_name] = {"enabled": enabled, "threshold_cs": threshold}

    try:
        config = LogcfgConfig(
            events=LogcfgEvents(**clean_events),
            capture_plans=bool(config_raw.get("capture_plans", False)),
            log_directory=str(config_raw.get("log_directory", "C:\\1C-TechLog")),
            max_size_gb=int(config_raw.get("max_size_gb", 10)),
        )
    except Exception as e:
        logger.warning("Не удалось распарсить LogcfgConfig из AI ответа: %s", e)
        config = LogcfgConfig()

    rationale_raw = parsed.get("events_rationale", [])
    rationale: list[EventRationale] = []
    for r in rationale_raw:
        if isinstance(r, dict):
            try:
                rationale.append(EventRationale(
                    event=str(r.get("event", "")),
                    threshold=str(r.get("threshold", "")),
                    why=str(r.get("why", "")),
                ))
            except Exception:
                pass

    return LogcfgGenerateResponse(
        config=config,
        explanation=str(parsed.get("explanation", "")),
        events_rationale=rationale,
        estimated_use_duration=str(parsed.get("estimated_use_duration", "30-60 минут")),
        warnings=[str(w) for w in parsed.get("warnings", []) if w],
        model_used=response.model,
        duration_ms=elapsed_ms,
    )
