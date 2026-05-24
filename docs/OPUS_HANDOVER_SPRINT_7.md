# Opus Handover — Sprint 7 → Sprint 8

**Audience:** архитектор (Claude Opus 4.7).
**Purpose:** что нужно знать для планирования следующих sprints без чтения всех 7 SPRINT_X_REPORT'ов.

---

## Что мы построили в Sprint 7

**Plan Analyzer** — 3-й анализатор Optimyzer. End-to-end:

```
.sqlplan / paste XML / ТЖ архив
        ↓
PerformanceStudio CLI (30 rule-based detectors) + html-query-plan visualization
        ↓
Claude Sonnet/Haiku 4.5 → structured AI explanation на русском
        ↓
UI: AiPlanExplanationCard + PlanVisualization + Statements + Warnings + MissingIndexes
```

Для **text format** (из 1С `planSQLText`) пайплайн короче — PerformanceStudio и visualization не работают на text, только PlanTextView + AI.

## Reusable infrastructure из Sprint 7

| Компонент | Файл | Reuse в Sprint 8+ |
|---|---|---|
| `planview.cli` (subprocess wrapper + candidate paths + cache) | `backend/.../planview/cli.py` | Шаблон для PostgreSQL pev2 wrapper |
| `loadQP()` inline-bundle pattern (Vite `?raw` + `new Function().call(window)`) | `frontend/src/vendor/qpLoader.ts` | Шаблон для bundling других UMD библиотек без external HTTP |
| `_migrate_plan_text` (idempotent ALTER TABLE) | `backend/.../storage/duckdb_store.py` | Шаблон для будущих schema migrations |
| `patch-logcfg-for-plans.ps1` self-elevation pattern (UAC via `Start-Process -Verb RunAs`) | `scripts/patch-logcfg-for-plans.ps1` | Шаблон для других системных правок (settings.json, registry) |
| `formatAiError()` (CloudError → human messages) | `frontend/.../PlanAnalyzer.tsx` | Применить ко всем cloud.* call sites — лучше UX |
| `PlanExplainRequest.plan_format` discriminator | `server/schemas/ai.py` | Pattern для multi-format AI endpoints |

## Открытые архитектурные вопросы для Sprint 8+

### Q1. text planSQLText → XML конвертер (TD-Sprint8-B)?

**Контекст:** В Phase D мы решили **не делать** конвертацию text → XML для Sprint 7. Сейчас text path короткий (только PlanTextView + AI, без visualization и PerformanceStudio rules). Это допустимо как MVP, но снижает ценность ТЖ-импорта vs прямого `.sqlplan`.

**Опции:**
- **A.** Investigate существующие OSS конвертеры (поискать в research/). Если есть — интегрировать.
- **B.** Self-build парсер на sqlparse + heuristics. Сложно — operator tree depth >10, есть много non-standard 1С extensions.
- **C.** Принять как ограничение forever. AI всё равно понимает text.

**Рекомендация:** Spike 1-2 дня в Sprint 8 на A. Если не находим — fallback на C.

### Q2. AI caching strategy (TD-Sprint8-D)?

**Сейчас:** каждый AI request → новый Anthropic call. Один и тот же план + одни warnings → одинаковый ответ → wasted tokens.

**Опции:**
- **A.** SQLite cache по `hash(sql_text + plan_xml + plan_format)`. Простой, embeddable.
- **B.** Server-side Redis. Требует infra.
- **C.** Skip кэширование, опираться на Anthropic prompt caching (200K context, $5/$15 per Mtok cached).

**Рекомендация:** A для desktop (cache в DuckDB архива). C для server endpoints (Phase 1 INFRA).

### Q3. PerformanceStudio CLI patch (TD-Sprint8-A)

`batch_hash_table_build.sqlplan` ломает CLI на JsonException (>64 depth). Опции:
- Отправить PR upstream (Erik Darling Data) с `MaxDepth=128` или `ReferenceHandler.Preserve`
- Wrap output с pre-truncation operator tree depth
- Skip these planов forever (mark in KNOWN_BROKEN)

**Рекомендация:** PR upstream — это OSS-friendly. Patch держать локально пока merged. Параллельно skip в KNOWN_BROKEN.

### Q4. UI: 1 tab vs 3 tabs для import (open question)

Сейчас 3 tabs (Файл / XML / Из архива ТЖ). Сергей попросил оставить до E.5 manual demo для финального решения.

Аргументы за **1 tab «Smart Import»**:
- Меньше cognitive load
- Auto-detection: file → analyze_file, paste content starts with `<` → XML, archive selector только если архив загружен
- Less UI surface

Аргументы за **3 tabs (текущее)**:
- Explicit user intent
- Empty states более понятные (нет смешения «загрузите архив» с «выберите файл»)
- Архив-import имеет совсем другой UX (list событий вместо одного picker)

**Рекомендация:** После Сергеевой demo решить. Я склоняюсь к 3 tabs — UX честнее.

### Q5. Plan Visualization scale на huge planов (TD)

Phase A+B+C не тестировал planов с >200 операторами. Регрессия в Phase E.2 включает large fixtures (`many_lines2.sqlplan` и т.п.) но manual UI test не делал. Возможные issues:
- SVG dimensions overflow → horizontal scroll или squish
- Tooltip overlap
- DOM nodes >1000 → React render perf

**Рекомендация:** Sprint 9 «edge cases harden» включить manual test с искусственным 500-операторным планом.

### Q6. Cost optimization — Haiku vs Sonnet routing

Sprint 7 переключил default на Haiku 4.5 для dev (~6× дешевле). Перед prod merge — вернуть Sonnet. Лучшее решение: **multi-model routing по tier**:
- Free → Haiku (5 запросов/мес лимит)
- Pro → Sonnet (1000 soft cap)
- Business → Opus 4.7 (unlimited reasonable)

Это часть Sprint 11 (AI Query Rewriter v2 + multi-model routing).

## Metrics баланс

### Codebase size
- **Sprint 6 closure:** Backend 574 tests, Server 112 tests, ~25K LOC Python + ~20K LOC TS
- **Sprint 7 closure:** Backend **705** tests (+131), Server **131** tests (+19), +1500 LOC new

### Production-readiness gates passed
- ✅ All 81 tested .sqlplan analyse без crash (1 known issue)
- ✅ Performance < targets (5s / 15s / 20s)
- ✅ AI endpoint 503 при отсутствии key (graceful)
- ✅ Visualization работает на >40 разнообразных planов
- ⏸ Manual demo session (E.5)
- ⏸ Manual TJ end-to-end (D.4)

### Bundle impact
- Backend Python wheel: no change (planview.exe идёт как Tauri resource, не Python)
- Tauri installer: **+96 MB** (planview.exe self-contained .NET runtime)
- Total installer: ожидается ~300 MB (с JRE для bsl-LS из Sprint 6)

## Tech debt backlog для Sprint 8 prioritization

1. **TD-Sprint8-A**: PerfStudio CLI deep tree bug — easy fix upstream PR (4-8h)
2. **TD-Sprint8-B**: text→XML converter — research-heavy (2-3 дня)
3. **TD-Sprint8-C**: CSS bloat refactor PlanAnalyzer.module.css — pure cleanup (2-3h)
4. **TD-Sprint8-D**: AI caching — простой SQLite cache (1 день)

Plus general (не Sprint 7 specific):
- Phase 1.6 telemetry buffer — server endpoint pending
- README upgrade с screenshot demo flow

## Roadmap recommendations

**Sprint 8 scope (предложение):**
- TD-Sprint8-A (PerfStudio upstream PR + KNOWN_BROKEN cleanup)
- TD-Sprint8-D (DuckDB AI cache)
- PostgreSQL pev2 — отдельная killer-feature
- E.5 manual demo от Sprint 7 → bugs file → fix

**Sprint 9 scope (предложение):**
- TD-Sprint8-B (text→XML converter) — если найдём OSS
- Edge cases harden (huge plans, broken XML, AI fallbacks)
- Deep real-world testing на больших archives (>50K events)
- Q5 large plan UI perf
