# Sprint 11 — AI Caching + Performance Regression Tracking: Итоговый отчёт

**Дата:** 2026-05-26
**Тег:** `v0.11.0-internal`
**Тип спринта:** Feature sprint — двойной фокус (cache infrastructure + regression detection)

---

## Краткий итог

Sprint 11 закрывает критический gap в unit economics проекта — добавляет
агрессивное AI caching (целевой hit rate 70-80%) для сокращения inference
cost с **$60-90/мес/юзер** до **$5-10/мес/юзер** + полноценный Performance
Regression Tracking для use case «после релиза стало хуже».

**Тесты до → после:**
- Backend: 916 → **966** (+50 в `regression/` module)
- Server: 216 → **291** (+75 в `ai_cache/` + `rate_limiter`)
- Frontend: 121 → **122** (без новых component тестов — vitest config без jsdom)

**TypeScript:** 0 ошибок. `tsc --noEmit` чистый.

**Итого: +126 новых тестов.**

---

## Архитектурное deviation от Sprint 11 spec

Spec предполагал **two-tier cache** (per-archive DuckDB + global SQLite).
Reality: frontend идёт **напрямую** в server `/v1/ai/...`, минуя backend
sidecar. Per-archive cache в backend требует рефакторинга всего AI flow.

**Решение (ADR-057):** single-tier cache в `server/services/ai_cache/`.
SQLite файл `<project_root>/data/ai_cache.db`. Cache key — content-canonical
(см. ADR-058), shared между всеми пользователями и архивами. Даёт 90%
бизнес-бенефита (cross-user + cross-archive hits) при 10% сложности.

Trade-off: теряем «cache travels с архивом» (когда юзер шарит архив колеге).
Приемлемо — колега всё равно получит cache hit если содержимое плана совпадает.

---

## Phase A — AI Cache Infrastructure (server-side)

### `server/services/ai_cache/`

| Файл | Назначение |
|------|-----------|
| `models.py` | `CacheEntry` dataclass, `CacheType` enum (7 типов), `CacheStats` |
| `canonicalize.py` | 6 нормализации + `compute_cache_key` (sha256) |
| `storage.py` | SQLite layer: WAL mode, threading.local connections, CRUD + cleanup + stats |
| `service.py` | High-level `CacheService` (sync + async wrappers через asyncio.to_thread) |
| `__init__.py` | Public API exports |

### Cache types

```
PLAN_MSSQL_XML, PLAN_MSSQL_TEXT, PLAN_PG_TEXT, PLAN_PG_JSON,
QUERY, LOGCFG, REGRESSION
```

### TTL strategy

| Тип | TTL | Обоснование |
|---|---|---|
| Plan AI (любые) | Forever | План детерминирован → объяснение тоже |
| Query AI | 90 дней | Диагностики bsl-LS могут обновляться |
| Logcfg AI | 30 дней | AI prompt и шаблоны эволюционируют |
| Regression | Forever | Метрики операции детерминируют объяснение |

### PROMPT_VERSION invalidation

Каждый AI endpoint имеет константу: `PROMPT_VERSION_PLAN_MSSQL`,
`_PLAN_PG`, `_QUERY`, `_LOGCFG`, `_REGRESSION`. Все равны `"v1"` на старте.
Cache key включает version → bump = automatic invalidation (старые entries
не находятся при lookup). Старые записи удаляются периодическим cleanup.

### Тесты Phase A

- `test_ai_cache_canonicalize.py` — **27** тестов
  - MSSQL XML с разными ActualRows → same canonical
  - PG JSON с разными Buffers → same canonical
  - SDBL с whitespace + comments → same canonical
  - Logcfg description case-insensitive + punctuation
- `test_ai_cache_storage.py` — **13** тестов (CRUD, expiry, invalidation, stats, persistence)
- `test_ai_cache_service.py` — **22** теста (sync + async API, singleton, integration)

**Итого: 62 теста.**

---

## Phase B — Plan AI cache integration

Hooked в `services/ai_explainer.explain_plan_query()` — обёрнут cache wrapper
поверх существующих `explain_mssql_plan()` + `explain_pg_plan()`. Cache type
определяется через `_plan_cache_type_for(req)`:
- engine=mssql + plan_format=xml → `PLAN_MSSQL_XML`
- engine=mssql + plan_format=text → `PLAN_MSSQL_TEXT`
- engine=postgres + plan_format=text → `PLAN_PG_TEXT`
- engine=postgres + plan_format=json → `PLAN_PG_JSON`

`PlanExplainRequest.force_refresh` — bypass cache lookup.
`PlanExplainResponse.was_cached + cache_age_seconds + cache_key` — UI metadata.

### Тесты Phase B

`test_ai_cache_integration.py` (Plan section) — **11** тестов:
- Cache miss → AI called → cache write → second call = hit (no AI)
- Same plan с разными runtime stats → cache hit (canonicalization работает)
- Different engines → different cache keys
- Force refresh bypasses cache
- PROMPT_VERSION bump invalidates
- All 4 cache types produce distinct keys

---

## Phase C — Query AI + Logcfg AI cache integration

`explain_query()` и `generate_logcfg()` — same pattern:
- Refactored к `_*_uncached()` + cache wrapper
- `force_refresh + was_cached + cache_age_seconds + cache_key` fields
- TTL=90 days (Query) / 30 days (Logcfg)

### Canonicalization для Query

```python
canonical = f"sdbl={canonicalize_sdbl(query_sdbl)}|diag={sorted_json(diagnostics)}"
```

Sorted diagnostics — порядок не важен для AI, но без sort → cache miss на
тривиальном переupорядочивании.

### Тесты Phase C

13 интеграционных тестов:
- Query: cache hit на одинаковых SDBL/диагностиках, comments/whitespace нормализация, diagnostic order не ломает кеш, force refresh, TTL=90 дней
- Logcfg: case-insensitive cache hit, punctuation, different platforms/dbms → different keys, force refresh, TTL=30 дней

---

## Phase D — Force Refresh UI + Rate Limiting

### `services/rate_limiter.py`

```python
PER_ITEM_COOLDOWN = timedelta(minutes=5)
PER_SESSION_LIMIT_PER_HOUR = 10
PER_SESSION_WINDOW = timedelta(hours=1)
```

`ForceRefreshRateLimiter` singleton с in-memory state. `check_and_record()`
вызывается в каждом AI POST endpoint когда `req.force_refresh=true`. Cooldown
hit → HTTP 429 с детализированным `detail` (`error`, `reason`,
`per_item_remaining_seconds`, `per_session_used`, `per_session_limit`).

### Endpoint для UI countdown

```
GET /v1/ai/force_refresh_status/{cache_key}
→ ForceRefreshStatusResponse(allowed, per_item_remaining_seconds, ...)
```

UI polling каждые 5 сек для live countdown.

### UI компонент `ForceRefreshButton.tsx`

- Маленькая icon-only кнопка (refresh stroke icon, 14×14)
- Положение: рядом с severity badge в AiPlanExplanationCard header
- UX (по memory rule «скрывать имплементационные детали»):
  - Allowed: tooltip «Обновить ответ AI»
  - Cooldown: disabled + tooltip «Доступно через 4:23» (БЕЗ упоминания cache)
  - НЕ показывает «⚡ из кэша» badge
- Polling: 5-сек интервал пока есть cacheKey

### Тесты Phase D

`test_rate_limiter.py` — **14** тестов:
- Per-item cooldown enforcement
- Per-session limit enforcement
- Different keys не блокируют друг друга
- Session window rolls (старые expire)
- `check()` vs `check_and_record()` separation
- Reset for tests
- API integration: 429 при second force_refresh

---

## Phase E — Regression Detection Engine

### `backend/regression/`

```
operation_matcher.py  — compute_fingerprint + match_operations
classifier.py         — classify_match + 5 ChangeType + 3 Confidence
data_loader.py        — DuckDB query на context_normalized (QUANTILE_CONT)
```

### Fingerprint

```python
fingerprint = (operation_name, context_first_line_normalized)
```

Нормализация убирает: timestamps, UUIDs, usernames, session IDs, connection IDs,
document numbers — runtime values которые не должны влиять на matching.

Trade-off (ADR-060): same `operation_name` с разным business context (Печать
кассовых vs Печать накладных) считается **разными операциями**. UI показывает
их раздельно — это правильно для UX (разные регрессии разбираются отдельно).

### 5 ChangeType

| Type | Условие |
|---|---|
| `REGRESSION` | `current_p95 >= baseline_p95 × threshold` |
| `IMPROVEMENT` | `current_p95 <= baseline_p95 / threshold` |
| `NEW` | Operation в current, нет в baseline |
| `DISAPPEARED` | Operation в baseline, нет в current |
| `STABLE` | В пределах threshold |

### Confidence

- `HIGH`: 20+ samples в обоих архивах
- `MEDIUM`: 5-20 samples
- `LOW`: < 5 samples

Для matched берётся `min(baseline_confidence, current_confidence)`.

### Priority score

```python
priority = (ratio - 1) × log(count + 1) × current_p95
```

Комбинирует «насколько хуже × как часто × абсолютная величина». Used для
sorting top-N regressions в UI и для выбора кандидатов на AI summary.

### RPC

```
regression.compute(
    baseline_archive_id,
    current_archive_id,
    threshold=2.0,
    min_samples=5,
    top_n=50,
) → {
    summary: {total_*},
    regressions: [...top_n by priority_score],
    improvements: [...top_n by ratio asc],
    new: [...top_n by priority_score],
    disappeared: [...top_n],
    stable_count: N,
}
```

### Тесты Phase E

- `test_operation_matcher.py` — **13** тестов (fingerprint normalization + matching)
- `test_classifier.py` — **37** тестов (5 change types + confidence + priority + edge cases)

**Итого: 50 тестов.**

---

## Phase F — Regression UI + AI summary endpoint

### ArchiveComparison расширение

Новый таб «Регрессии операций» (иконка `AlertTriangle`):
- Controls: threshold (1.5-10×, default 2.0) + min_samples (default 5) + кнопка «Применить»
- Summary grid: 5 SummaryCard (🔴/🟢/🆕/❌/➖)
- RegressionSection × 4 для регрессий/улучшений/новых/исчезли
- RegressionRow с operation_name (truncated, full в tooltip), p95 baseline→current,
  Δ%, вызовы A→B, confidence badge

### AI summary endpoint

```
POST /v1/ai/explain_regression
  → RegressionExplainResponse(summary, model_used, duration_ms, ...)
```

Модель Haiku (короткий summary). Cache integration: TTL=forever (операция +
метрики детерминируют объяснение). Force refresh rate limiting.

**Scope note:** UI базовая инфраструктура готова, но **автогенерация AI
summary при rendering RegressionTab НЕ включена**. Можно добавить как
отдельный feature в Sprint 12 — нужны UX-решения когда и как показывать
AI summary inline (top-3 vs top-10? inline вы expandable?). Backend
endpoint готов, frontend integration — следующий шаг.

---

## Phase G — Closure

### Documentation

- `docs/DECISIONS.md`: ADR-057..061 (cache architecture, canonicalization,
  rate limiting, regression algorithm, UI placement)
- `docs/sales_sprint/SPRINT_11_REPORT.md` (этот файл)
- Tag `v0.11.0-internal`

### Cache stats UI (deferred)

Sprint 11 spec упоминал Settings → AI Cache tab со статистикой (hit rate,
storage size, top types). **Не включено в Phase G** — backend `get_stats()`
готов, UI можно добавить как маленький feature в Sprint 12 (нужны
UI решения по UX: показывать ли реальные cache numbers пользователю или
делать только admin-only через separate /admin endpoint).

### Periodic cleanup (deferred)

Sprint 11 spec предполагал periodic cleanup expired entries on archive open.
В текущей архитектуре (server-side cache) — должен запускаться на server
startup или background scheduler. **Не включено в Phase G** — приоритет
ниже чем UI/UX features. Сейчас expired entries просто не возвращаются при
lookup (cleanup можно запустить вручную через service API).

---

## Scope-out (не входило в Sprint 11)

| Фича | Причина |
|------|---------|
| Two-tier cache (per-archive + global) | Архитектурный deviation (ADR-057) |
| AI summary inline в Regression UI | Backend готов, frontend integration — Sprint 12 |
| Cache stats UI в Settings | Backend готов, UI — Sprint 12 |
| Periodic cleanup on startup | Deferred (low priority) |
| ForceRefreshButton component tests | vitest config без jsdom |

---

## Breaking Changes

Нет. Все изменения аддитивны:
- `PlanExplainRequest.force_refresh: bool = False` (default false → backward-compat)
- `PlanExplainResponse.{was_cached, cache_age_seconds, cache_key}` — optional fields
- Аналогично для `ExplainRequest/Response`, `LogcfgGenerateRequest/Response`
- Новые endpoint'ы `/v1/ai/explain_regression` + `/v1/ai/force_refresh_status/{key}`
- Новый RPC `regression.compute`

---

## Business impact (ожидаемый)

| Метрика | Без caching | С caching (target) |
|---|---|---|
| AI calls/day на активного юзера | 100+ | 20-30 |
| Inference cost/month/user | $60-90 | $5-10 |
| Margin от Pro 9 900 ₽ | Убыточно (50%+ AI cost) | Profitable |
| AI response latency p50 | 5-8 sec | 50-100 ms (cache hit) |

Это **критический спринт для unit economics** — без него масштабирование
невозможно.

---

## Артефакты

| Путь | Тип | Описание |
|------|-----|---------|
| `server/services/ai_cache/` | module | 5 файлов, ~600 LOC |
| `server/services/rate_limiter.py` | service | ForceRefreshRateLimiter singleton |
| `server/tests/test_ai_cache_*.py` | tests | 62 unit-теста |
| `server/tests/test_rate_limiter.py` | tests | 14 тестов |
| `server/tests/test_ai_cache_integration.py` | tests | 24 integration теста |
| `server/services/ai_explainer.py` | modified | +explain_regression + cache wrappers |
| `server/schemas/ai.py` | modified | +RegressionExplain* + force_refresh/was_cached fields |
| `server/api/routers/ai.py` | modified | +explain_regression + force_refresh_status endpoint |
| `backend/src/optimyzer_backend/regression/` | module | 4 файла, ~400 LOC |
| `backend/src/optimyzer_backend/rpc/regression_rpc.py` | RPC | regression.compute |
| `backend/tests/regression/` | tests | 50 unit-тестов |
| `frontend/src/components/primitives/ForceRefreshButton.tsx` | UI component | Icon-only + countdown |
| `frontend/src/components/screens/ArchiveComparison/ArchiveComparison.tsx` | modified | +RegressionTab + 200 LOC |
| `frontend/src/api/cloud.ts` | modified | force_refresh/was_cached/cache_key + aiForceRefreshStatus |
| `frontend/src/api/backend.ts` | modified | regressionCompute + DTO types |

---

## Roadmap context (после Sprint 11)

```
✅ Sprint 10  — TJ Config Builder desktop (v0.10.0-internal)
✅ Sprint 11  — AI Caching + Regression Tracking (v0.11.0-internal)
   Sprint 10.5 — Web TJ Config Builder + SEO (когда решит Сергей)
   Sprint 12  — Advanced (Memory Leaks, Lock Wait Anatomy, Sessions Gantt,
               Transaction Timeline) + cache stats UI + regression AI summaries inline
   Sprint 13  — AI Rewriter v2 + Team Workspace
   Sprint 14  — UX Reorganization + Onboarding (pipeline-driven UI)
   Финал — Infrastructure + Marketing + Launch
```
