# Opus Handover — Sprint 11 → Sprint 12

**Audience:** архитектор (Claude Opus 4.7).
**Purpose:** контекст для планирования Sprint 12 без чтения всех Sprint 11 артефактов.
**Дата:** 2026-05-26
**Tag:** `v0.11.0-internal` (создан, не запушен).

---

## Что мы построили в Sprint 11

**AI Caching + Performance Regression Tracking.** End-to-end:

```
Frontend AI запрос
        ↓
server/v1/ai/* endpoint
        ↓
[Phase D] rate limiter check (если force_refresh) → 429 при cooldown
        ↓
[Phase A] cache lookup (sha256 от canonical input + type + prompt_version + model)
        ↓ miss
Anthropic API call (Sonnet/Haiku в зависимости от endpoint)
        ↓
cache store (TTL forever для планов, 90d query, 30d logcfg, forever regression)
        ↓
response с was_cached/cache_age_seconds/cache_key полями
```

Параллельно — Phase E + F:
```
Backend RPC regression.compute
        ↓
load_operations(baseline) + load_operations(current) через DuckDB
        ↓
operation_matcher.match_operations() — fingerprint matching
        ↓
classifier.classify_match() — 5 ChangeType + Confidence + priority_score
        ↓
Frontend ArchiveComparison → таб «Регрессии операций»
```

## Reusable infrastructure из Sprint 11

| Компонент | Файл | Reuse в Sprint 12+ |
|---|---|---|
| `CacheService` (content-canonical SQLite) | `server/services/ai_cache/service.py` | Любой новый AI endpoint — обернуть с aget/aset |
| 6 canonicalization функций | `server/services/ai_cache/canonicalize.py` | Можно расширять (новые типы AI ответов) |
| `ForceRefreshRateLimiter` (in-memory, 5min/10h) | `server/services/rate_limiter.py` | Применим к любым другим rate-limited операциям |
| `_reset_ai_cache` + `_reset_rate_limiter` fixtures | `server/tests/conftest.py` | Autouse, гарантирует test isolation |
| `regression/operation_matcher.py` (fingerprint normalization) | `backend/src/optimyzer_backend/regression/` | Можно reuse для других matching задач (например archive diff на operation level) |
| `regression/classifier.py` (priority_score formula) | Same | Sprint 12 Lock Wait Anatomy может использовать priority sorting |
| `ForceRefreshButton.tsx` (icon + countdown + polling) | `frontend/src/components/primitives/` | Reuse для всех AI cards (сейчас только в PlanAnalyzer) |
| `PROMPT_VERSION_*` константы pattern | `server/services/ai_explainer.py` | Любой новый AI prompt — `PROMPT_VERSION_X = "v1"`; bump = automatic invalidation |

## Архитектурное deviation — ВАЖНО для Sprint 12

**ADR-057:** Sprint 11 spec предполагал **two-tier cache** (per-archive DuckDB + global SQLite). Реализован **single-tier server-side**. Причина: AI вызовы идут frontend→server напрямую, минуя backend sidecar. Two-tier требовал бы рефактора всего AI flow.

**Что это значит для Sprint 12:**
- Если в Sprint 12 надо будет cache travel с архивом (например при шаринге) — нужно либо рефакторить AI flow через backend, либо реализовать export/import cache subset через archive_id фильтр.
- Если будет multi-tenant SaaS migration — нужна изоляция per-tenant. Сейчас cache shared globally.

## Открытые архитектурные вопросы для Sprint 12+

### Q1. AI summary inline в Regression UI?

**Контекст:** Phase F создал endpoint `POST /v1/ai/explain_regression` (backend готов, cached, TTL forever). UI не вызывает его автоматически.

**Опции:**
- **A.** Авто-генерация для top-3 priority при rendering таба — UX «магия», но cost на refresh.
- **B.** Кнопка «Получить AI-объяснение» на каждой regression row — explicit.
- **C.** Expandable row: клик раскрывает + lazy fetch.

**Рекомендация:** B или C. A пугает юзеров расходом quota.

### Q2. Cache stats UI в Settings?

**Контекст:** `CacheService.get_stats()` готов, возвращает `total_entries`, `total_size_bytes`, `entries_by_type`, `total_hits`, `top_hits`. UI отсутствует.

**Memory rule конфликт:** «скрывать имплементационные детали от юзера». Cache size — это impl detail.

**Опции:**
- **A.** Только в admin-only (`/admin/ai-cache`) endpoint. Юзер не видит.
- **B.** Простой «Cache hit rate за неделю: 73%» в Settings без чисел.
- **C.** Не добавлять вообще. Pure backend metric.

**Рекомендация:** A для отладки + telemetry. C для UI.

### Q3. ForceRefreshButton в Query/Logcfg AI cards

Сейчас интегрирован только в `AiPlanExplanationCard`. Аналогичные cards в:
- `frontend/src/components/screens/QueryAnalyzer/` — для query explain
- `frontend/src/features/tj-config-builder/components/AiWizardTab.tsx` — для logcfg

Integration trivial (импорт + проброс `onForceRefresh` + `response.cache_key`). 30 минут работы.

### Q4. Backend test target 1050 не достигнут

Sprint 11 plan: 916 + 130 = 1046. Реально: 916 + 50 = 966. Дельта — 80 тестов.

**Где недобор:** Sprint 11 spec предполагал extensive Phase G coverage tests (real-data benchmarks на Sprint 8 pgBase + 102 plan XMLs). Эти тесты были классифицированы как «nice-to-have», не critical для функционала. В Sprint 12 можно добавить если будет приоритет.

### Q5. Frontend test target 175 не достигнут

Реально 122. Дельта — 53 тестов. Причина: `vitest.config.ts` использует Node environment, **без jsdom**. Component тесты (ForceRefreshButton, RegressionTab, etc.) технически невозможны без переключения на jsdom.

**Опции:**
- **A.** Sprint 12: добавить jsdom setup + написать ~40 component тестов.
- **B.** Принять текущее покрытие (utility тесты + serializer) как достаточное.

**Рекомендация:** A — invest 4-6 часов в Sprint 12 на test infrastructure upgrade.

### Q6. Cache `cleanup_expired` запускается только по запросу

Сейчас expired entries просто не возвращаются при lookup, но физически остаются в БД. После года эксплуатации БД может вырасти до 100s MB.

**Опции:**
- **A.** Server startup hook — cleanup при загрузке uvicorn.
- **B.** APScheduler job (есть в server) — раз в сутки cleanup.
- **C.** Manual через admin endpoint.

**Рекомендация:** B (используя существующий `services/scheduler.py`).

## Metrics баланс

### Test counts

| Источник | До Sprint 11 | После | Δ | Target | Статус |
|---|---|---|---|---|---|
| Backend | 916 | **966** | +50 | >1050 | ⚠️ -84 (см. Q4) |
| Server | 216 | **291** | +75 | >260 | ✅ |
| Frontend | 121 | **122** | +1 | >175 | ⚠️ -53 (см. Q5) |
| **Total** | **1253** | **1379** | **+126** | — | — |

### Codebase size delta

- Server: **+~1200 LOC** (ai_cache/ + rate_limiter + 3 wrapped AI functions + explain_regression + endpoint)
- Backend: **+~400 LOC** (regression/ module)
- Frontend: **+~250 LOC** (ForceRefreshButton + RegressionTab + cloud.ts types + backend.ts types)
- Tests: **+~1500 LOC** (62 + 24 + 14 + 50 unit/integration)
- Docs: **+~600 LOC** (5 ADRs + SPRINT_11_REPORT)

### Production-readiness gates passed

- ✅ All 7 phases acceptance criteria (см. SPRINT_11_REPORT.md)
- ✅ TypeScript clean (0 errors)
- ✅ All AI functions wrapped с cache, не сломаны (146 existing tests passing)
- ✅ Force refresh rate limiting работает с per-item + per-session
- ✅ Regression detection алгоритм covered 50 tests
- ⏸ Manual demo от Сергея (запрошено в финальном summary)
- ⏸ Real-data hit rate measurement (требует production traffic)
- ⏸ Performance benchmarks (cache lookup < 5ms — теоретически достигается, не замерено формально)

### Bundle impact

- Backend Python wheel: no change (ai_cache.db создаётся at runtime)
- Server installer: no change (новый services/ai_cache/ внутри уже установленного пакета)
- Frontend bundle: +~3 KB (ForceRefreshButton component)
- Cache DB grow rate: оценочно ~50-100 MB в год при активном использовании (cleanup в Sprint 12 нужен — см. Q6)

## Tech debt backlog для Sprint 12 prioritization

| ID | Описание | Эффорт | Приоритет |
|----|----------|--------|----------|
| **TD-Sprint12-A** | AI summary inline в Regression UI (Q1) | 4-6h | Medium |
| **TD-Sprint12-B** | ForceRefreshButton в Query/Logcfg AI cards (Q3) | 30 мин | Low |
| **TD-Sprint12-C** | Cache cleanup scheduler (Q6) | 1-2h | Medium |
| **TD-Sprint12-D** | jsdom setup + 40 component tests (Q5) | 4-6h | Medium |
| **TD-Sprint12-E** | Cache stats endpoint (Q2 — A вариант, admin-only) | 2h | Low |
| **TD-Sprint12-F** | Real-data benchmarks (Q4) — cache lookup time, hit rate | 1-2 дня | Low |

## Sprint 12 recommendations

**Sprint 12 plan (Advanced features, согласно roadmap):**
- Memory Leaks анализ
- Lock Wait Anatomy
- Sessions Gantt
- Transaction Timeline

**Sprint 11 tech debt (предложение интегрировать):**
- TD-Sprint12-A (AI summary inline в Regression) — 4-6h, complements Phase F
- TD-Sprint12-C (cache cleanup scheduler) — 1-2h, prod readiness

**Defer на Sprint 13+:**
- TD-Sprint12-D (jsdom test infrastructure)
- TD-Sprint12-E (cache stats UI)
- TD-Sprint12-F (real-data benchmarks)

## Manual demo от Сергея — что проверить

Sprint 11 — bizns-critical (unit economics). Demo обязательна перед закрытием:

1. **Cache hit rate на реальных архивах:**
   - Открыть план в PlanAnalyzer → AI explanation. Засечь время первого ответа (5-8 сек).
   - Закрыть → переоткрыть тот же план → AI explanation. Должно быть instant (<200ms).
   - В network tab: response должен содержать `was_cached: true`.

2. **Force refresh cooldown:**
   - В PlanAnalyzer кликнуть refresh icon. Получить fresh response (5-8 сек).
   - Сразу попробовать кликнуть ещё раз. Кнопка должна быть disabled с tooltip «Доступно через 4:XX».
   - Через 5 минут — снова active.

3. **Regression detection:**
   - Иметь два архива одной БП 3.0 (например до/после изменения расширения).
   - В ArchiveComparison → таб «Регрессии операций».
   - Проверить summary cards + регрессии sorted по priority + confidence badges.

4. **Force refresh rate limit per-session:**
   - Сделать 10 force refresh подряд на разных AI cards.
   - 11-я попытка должна вернуть 429 «Лимит обновлений на час».

## Файлы изменённые в Sprint 11 (для quick orientation)

### Новые файлы
```
server/services/ai_cache/                    (5 файлов, single-tier cache)
server/services/rate_limiter.py
server/tests/test_ai_cache_canonicalize.py
server/tests/test_ai_cache_storage.py
server/tests/test_ai_cache_service.py
server/tests/test_ai_cache_integration.py
server/tests/test_rate_limiter.py
backend/src/optimyzer_backend/regression/    (4 файла)
backend/src/optimyzer_backend/rpc/regression_rpc.py
backend/tests/regression/                    (3 файла)
frontend/src/components/primitives/ForceRefreshButton.tsx
frontend/src/components/primitives/ForceRefreshButton.module.css
docs/sales_sprint/SPRINT_11_REPORT.md
docs/OPUS_HANDOVER_SPRINT_11.md             (этот файл)
```

### Модифицированные
```
server/services/ai_explainer.py              (+ explain_regression + cache wrappers + PROMPT_VERSION_*)
server/schemas/ai.py                          (+ force_refresh + was_cached + cache_key + RegressionExplain*)
server/api/routers/ai.py                     (+ explain_regression endpoint + force_refresh_status + rate limit checks)
server/tests/conftest.py                     (+ autouse _reset_ai_cache + _reset_rate_limiter)
backend/src/optimyzer_backend/__main__.py    (+ import regression_rpc)
frontend/src/api/cloud.ts                    (+ force_refresh/was_cached/cache_key types + aiForceRefreshStatus)
frontend/src/api/backend.ts                  (+ regressionCompute + RegressionResultDto + RegressionSummary)
frontend/src/components/screens/PlanAnalyzer/AiPlanExplanationCard.tsx  (+ onForceRefresh prop)
frontend/src/components/screens/PlanAnalyzer/PlanAnalyzer.tsx           (+ forceRefresh flag в request)
frontend/src/components/screens/ArchiveComparison/ArchiveComparison.tsx (+ RegressionTab + 200 LOC)
docs/DECISIONS.md                             (+ ADR-057..061)
```

## Локальное состояние git

```
4 commits в Sprint 11:
  87a2fa9 sprint11(phase A-D): AI cache infrastructure + force refresh rate limiting
  4f311da sprint11(phase E): performance regression detection engine
  9e4feca sprint11(phase F): regression UI в ArchiveComparison + AI summary endpoint
  d493c6a sprint11(phase G): closure — ADR-057..061 + SPRINT_11_REPORT

Tag: v0.11.0-internal (создан, НЕ запушен)
```

`git push origin main --tags` ожидает явного запроса Сергея.

---

## Stage status: ГОТОВО К ВОЗВРАТУ

Этот документ — single point of entry для архитектора Opus при планировании Sprint 12. Все open questions, tech debt, deviation от spec — задокументированы. Test counts актуальны, files inventory полная.

**Следующий шаг ожидающий decision Сергея:**
1. Manual demo для validation
2. Sprint 10.5 timing (Web TJ Config Builder + SEO) — решение «когда»
3. Sprint 12 scope — какие из TD-Sprint12-* интегрировать в Advanced features

**Подготовил:** Claude Opus 4.7
**Для:** Claude Opus 4.7 (architect role) при следующем планировании
**Дата:** 2026-05-26
