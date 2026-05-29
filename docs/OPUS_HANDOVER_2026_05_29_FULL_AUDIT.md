# 1C-Optimyzer — Полный аудит проекта + Sprint 12 Handover

**Дата:** 2026-05-29
**Аудитория:** архитектор (Claude Opus 4.7)
**Цель:** одна точка входа в текущее состояние проекта. После двухдневной паузы (работа над сторонним CFE `goslog`-расширением) нужно восстановить полный контекст — что закрыто, что отложено, какие решения ждут Сергея, и под какие приоритеты планировать Sprint 12.
**Источник правды:** данные собраны прямой инспекцией репозитория `D:\1C-Optimyzer` (git log, файлы, метрики) — не пересказ.

---

## 0. TL;DR для Opus

- **Module 1 (Performance Investigation Workbench) production-ready** с конца Sprint 2 (2026-05-19). Дальше — наращивали возможности, не ломали базу.
- **Module 2 (Configuration Metadata + QueryAnalyzer)** закрыт через Sprint 4–5. Текущее состояние: QueryAnalyzer скрыт из Sidebar и shortcuts (commit `46c7bc1` после Sprint 5 fix batch) — решение Сергея, не bug.
- **Module 3 (Plan Analyzer)** — Sprint 7 для MSSQL, Sprint 8 для PostgreSQL. Engine dispatch автоматический, pev2 — opt-in для PG (Web Component + read-only PG connection).
- **Cloud (server + cabinet + landing)** — code-complete после Sales Sprint Phase 1+2 (tag `v0.6.0-internal`). Не задеплоен — ждёт Сергея с prod credentials, VDS, доменом.
- **Sprint 9** — hardening (real-world fixtures + AI enum normalizer + CSS lint), без новых аналитических фич.
- **Sprint 10** — TJ Config Builder desktop (новая группа Sidebar «ПОДГОТОВКА», `Ctrl+L`). После релиза словили 3 критических бага (см. §3.10).
- **Sprint 11** — AI Caching (унит-экономика) + Performance Regression Tracking. Tag `v0.11.0-internal` создан, **не запушен** — ждёт явного запроса Сергея. Manual demo от Сергея — ожидается.
- **Ничего критичного на main не сломано.** TypeScript clean, все 1 379 тестов зелёные.
- **Открытых решений Сергея:** 4 штуки (§7). Технического долга — 8 пунктов с эфортом от 30 минут до 1–2 дней (§6).

---

## 1. Состояние репозитория на 2026-05-29

### 1.1 Git

| Ветка | Состояние |
|-------|-----------|
| `main` | up-to-date с `origin/main`. Последний коммит — `eee38ee docs: IDEA_PUBLISH_GOSLOG_1C` |
| feature-ветки | 11 веток сохранены для исторической прослеживаемости (Sprint 0..8). Можно подчищать. |

### 1.2 Tags

```
v0.1.0-internal           — Sprint 0
v0.2.0-internal           — Sprint 1
v0.3.0-internal           — Sprint 2
v0.4.0-internal           — Sprint 3/3.5
v0.5.0-internal           — Sprint 4 + 5 (Module 2 closure)
v0.6.0-internal           — Sales Sprint (Phase 1+2)
v0.7.0-internal           — Sprint 7 Phase D-F closure (planSQLText pipeline)
v0.8.0-pg-core-internal   — Sprint 8 Phase B (промежуточный)
v0.8.0-internal           — Sprint 8 Phase C (15 PG антипаттернов)
v0.9.0-internal           — Sprint 9 (hardening)
v0.10.0-internal          — Sprint 10 (TJ Config Builder)
v0.11.0-internal          — Sprint 11 (AI Cache + Regression) — НЕ ЗАПУШЕН
```

### 1.3 Untracked в рабочем дереве

В корне лежат `SPRINT_*_PROMT.md` файлы (исходные prompts от архитектора, текущая копия — `SPRINT_7_PROMT.md`, `..._8`, `..._9`, `..._10`, `..._11`, `SALES_SPRINT_PROMT.md`). Эти файлы в `.gitignore` не попадают, но и не закоммичены — `git status` показывает их как untracked. Это намеренно: они приватный input от архитектора, не product artifact.

В корне также untracked:
- `find_pattern.ps1`, `fix_form_badge.ps1`, `patch_form_chip.ps1`, `unpatch_form_chip.ps1` — служебные PowerShell для отладки CFE `goslog`-расширения (сторонний проект, не относится к Optimyzer).
- 6 PDF в `docs/` (учебники 1С:Эксперт — справочные материалы Сергея).
- `frontend/.vite.err`, `server/.uvicorn.err` — runtime error логи dev-стендов.
- `server/uv.lock` — может появиться при переходе на `uv` менеджер пакетов.
- Папка `ТЖ/` — пользовательские архивы для тестов.

**Действие:** ничего срочного. При начале Sprint 12 — добавить в `.gitignore` `*.err`, `ТЖ/`, `*PROMT.md`, чтобы `git status` был чище.

### 1.4 Объёмы кода (фактические, на 2026-05-29)

| Subproject | LOC |
|---|---|
| `backend/` (Python sidecar, DuckDB, ТЖ-парсер, antipatterns, regression) | **12 848** |
| `server/` (FastAPI cloud API + AI cache + rate limiter) | **10 336** |
| `frontend/` (Tauri 2 + React desktop) | **19 960** |
| `cabinet/` (React webapp account.optimyzer.pro) | **1 079** |
| `landing/` (статика optimyzer.pro + /docs) | **1 827** (HTML) |
| **Итого исходников** | **~46 050 LOC** |

### 1.5 Тесты (актуально на конец Sprint 11)

| Suite | Кол-во | Прогон |
|---|---|---|
| Backend (Python) | **966** | `cd backend && pytest` |
| Server (Python, FastAPI) | **291** | `cd server && pytest` |
| Frontend (TypeScript, vitest) | **122** | `cd frontend && npm test` |
| **Итого** | **1 379** | |

TypeScript typecheck чист (`tsc --noEmit` — 0 ошибок в `frontend/` и `cabinet/`).

### 1.6 ADRs

`docs/DECISIONS.md` содержит **60 ADR** (ADR-001 … ADR-060+). Каждый sprint добавлял 3–6 решений. Последние 5: ADR-052..056 + ADR-057..061 (Sprint 11, в файле есть, грep по nuance — частично перемешаны порядки).

---

## 2. Архитектура — 5 деплоируемых юнитов

Карта проекта зафиксирована в `QUICKSTART.md` и не менялась после Sales Sprint:

| Юнит | Папка | Технологии | Запуск dev | Деплой |
|---|---|---|---|---|
| **Desktop sidecar** | `backend/` | Python 3.11+, DuckDB read-only, JSON-RPC over stdio, sqlparse | автостарт из `start.bat` | бандлится в `frontend/src-tauri/binaries/` |
| **Desktop UI** | `frontend/` | Tauri 2, React 18, TypeScript, CodeMirror 6, Recharts, Zustand | `.\start.bat` | Tauri build → MSI/DMG/AppImage |
| **Cloud API** | `server/` | FastAPI, SQLAlchemy 2, Alembic, SQLite/PostgreSQL, JWT, AI cache (SQLite), APScheduler | `uvicorn api.main:app --port 8001` | systemd unit на VDS + nginx |
| **Account cabinet** | `cabinet/` | React 18, Vite, React Router 6, TanStack Query 5, Recharts | `npm run dev` (порт 5173) | nginx (subdomain `account.optimyzer.pro`) |
| **Landing + docs** | `landing/` | HTML + CSS (без JS framework) + статические `/docs/*.html` | `python -m http.server 8000` | nginx (`optimyzer.pro`, есть `nginx.conf.example`) |

### 2.1 Поток AI запросов (важно для понимания Sprint 11)

```
Frontend AI запрос
        ↓
server/v1/ai/* endpoint  (минует backend sidecar)
        ↓
[Sprint 11 Phase D] rate limiter (если force_refresh)
        ↓
[Sprint 11 Phase A] cache lookup (sha256 от canonical input + type + prompt_version + model)
        ↓ miss
Anthropic API (Sonnet/Haiku, в зависимости от endpoint)
        ↓
cache store (TTL forever для планов, 90d query, 30d logcfg, forever regression)
        ↓
response: explanation + was_cached/cache_age_seconds/cache_key
```

**Архитектурное deviation (ADR-057):** изначальный Sprint 11 spec предполагал two-tier cache (per-archive DuckDB + global SQLite). Реализован single-tier server-side, потому что frontend ходит напрямую в `server/v1/ai/*` минуя backend sidecar. Two-tier требовал бы рефакторинга всего AI flow. Trade-off обсуждается в OPUS_HANDOVER_SPRINT_11.md §«Архитектурное deviation».

### 2.2 Поток парсинга ТЖ архива (Module 1)

```
Frontend DragDrop / file dialog
        ↓
Tauri command (Rust) → child-process spawn backend (Python)
        ↓
JSON-RPC over stdio
        ↓
backend ingest:
  - zip extractor (защита от zip-slip)
  - encoding auto-detect (UTF-8 BOM / plain / cp1251 / cp866)
  - streaming lexer (verified на 12 GiB)
  - SQL normalization (Sprint 1)
  - pyarrow Appender → DuckDB
  - SQLite metadata (per-archive)
```

После ingest UI получает access к 6+ предсобранным views (Sprint 2), SQL Console (Sprint 0+1), Анатомии операции (Sprint 3), QueryAnalyzer (Sprint 4–6, скрыт), PlanAnalyzer (Sprint 7–8).

### 2.3 Поток Plan Analyzer (Module 3, Sprint 7–8)

```
План на вход:
  - .sqlplan файл (MSSQL, SSMS export)
  - paste TEXT (MSSQL SHOWPLAN_TEXT или PG EXPLAIN TEXT)
  - paste JSON (PG)
  - автоэкстракт из ТЖ архива (если в logcfg.xml был <plansql/>)
        ↓
detectPlanEngine() — определяет mssql vs postgres
        ↓ ┐
        │ ├─ MSSQL: PerformanceStudio CLI (30 правил) + SSMS-style визуализация (html-query-plan)
        │ ├─ MSSQL: 9 T-SQL антипаттернов (sqlglot)
        │ └─ AI explanation с MSSQL-prompt
        │
        ├─ PG: pev2 (opt-in, через Vue Web Component, требует PG connection в OS keychain)
        ├─ PG: re-EXPLAIN через PG connection (asyncpg)
        ├─ PG: 15 PG-antipatterns (sqlglot + 1С-aware regex heuristic)
        └─ AI explanation с PG-prompt (знает 1С specifics: `enable_mergejoin=off`, `mchar/mvarchar`, lowercase naming)
```

Engine dispatch автоматический по событию ТЖ (`DBMSSQL` → MSSQL, `DBPOSTGRS` → PostgreSQL).

---

## 3. Sprint timeline — что делали и какие артефакты

### 3.1 Sprint 0 — Foundation (tag `v0.1.0-internal`)

Скаффолд проекта. Tauri shell + Python sidecar + JSON-RPC bridge + DuckDB store + OQL Console (read-only editor + 3 preset запросов). 29 backend тестов. Дизайн-соответствие с 18 экранами sidebar (только oql enabled).

Сделано: `SPRINT_0_REPORT.md`, `OPUS_HANDOVER_SPRINT_0.md`.

### 3.2 Sprint 1 — Ingest + OQL DSL (tag `v0.2.0-internal`)

OQL DSL → SQL компилятор. Pipeline `events | where ... | summarize ... by ...` → `SELECT ... GROUP BY ...` поверх DuckDB. CodeMirror 6 с custom OQL language (syntax highlighting, autocomplete, error markers). Sidecar heartbeat + auto-restart. Streaming ingest на 12 GiB архиве verified.

### 3.3 Sprint 2 — Investigation Workbench (tag `v0.3.0-internal`, Module 1 closure)

Шесть pre-built views (Slow Queries / Locks Timeline / Process Roles / Duration Histogram / Errors Feed / Activity Heatmap). Cross-filtering: клик в одном view применяется ко всем. Multi-archive Comparison (side-by-side diff с regression detection — основа для Sprint 11 Phase E/F). SQL Templates library (13 готовых запросов). Export CSV/TSV/JSON. Saved queries через SQLite. Archive management (per-item + bulk удаление).

**Module 1 production-ready** — после этого всё, что мы делали, — добавления на стабильную базу.

См. `SPRINT_2_REPORT.md`, `PROJECT_REACTIVATION_SPRINT_2.md` (был closure module 1 на Sprint 1, отменён).

### 3.4 Sprint 3 + 3.5 — Anatomy + Explainer (tag `v0.4.0-internal`)

«Анатомия операции» — drill-down на конкретный SQL-вызов с агрегатами по времени, ожиданиям, контексту. AiExplainerCard впервые подключила Anthropic API напрямую (до Sprint 11 без cache). Sprint 3.5 — mid-sprint фиксы UX и edge cases. Подробности — `SPRINT_3_5_REPORT.md`.

### 3.5 Sprint 4 — Query Analyzer initial

bsl-language-server подключён как jar-bundle. SDBL анализ через 19 диагностик. Реализован первый прототип Query Analyzer экрана.

См. `SPRINT_4_REPORT.md`.

### 3.6 Sprint 5 — Configuration Metadata (tag `v0.5.0-internal`)

Парсер Configuration.xml. Извлечение объектов конфигурации + Predefined.xml. Semantic rules engine (8 правил). ConfigurationBadge UI + Settings. RPC методы `configuration.*`. Golden test suite (30+ кейсов).

**После Sprint 5 — большой fix batch (10 фиксов).** В частности — Fix #5 «детектить опечатки типа объекта» — добавлено `check_predefined_item_not_exists` правило. Все 10 фиксов закрыты, см. список tasks #10–19 в TaskList.

**Sprint 5 closure event:** QueryAnalyzer был скрыт из Sidebar/shortcuts/routes — решение Сергея на основе market validation. Документировано в `QUERY_ANALYZER_HIDDEN_2026_05.md`. Код QueryAnalyzer не удалён, можно вернуть через флаг — но Sprint 4 как screen не используется напрямую (только через PlanAnalyzer integration).

### 3.7 Sales Sprint — Phase 1 + Phase 2 (tag `v0.6.0-internal`)

Это **параллельный side-track к Sprint 5/6**, заложен infrastructure-слой для коммерциализации:

**Phase 1.1** — Yandex OAuth + `server/` scaffold (FastAPI + SQLAlchemy 2 + Alembic; SQLite dev / PostgreSQL prod).
**Phase 1.2** — Subscriptions / Credits / Devices / Usage API. Soft caps engine (Pro > Credits > Free).
**Phase 1.3** — Web cabinet `cabinet/`: React 18 + Vite, 7 страниц + Login + OAuthCallback. Mobile responsive.
**Phase 1.4** — YooKassa integration: `services/yookassa_client.py` (vat_code=1 для самозанятого, stub-mode для dev). License key generation: `OPTM-XXXX-XXXX-XXXX-XXXX`. Recurring billing cron (PAST_DUE → CANCELLED через 7 дней).
**Phase 1.5** — License activation в desktop. `/v1/license/activate` (key + fingerprint → device JWT, проверка лимита устройств; 409 с active_devices если превышен). `/v1/license/heartbeat` (24h interval, graceful degradation после 7 дней). UI: `AccountTab.tsx` + `PaywallModal.tsx`. Backwards-compat: без accessToken AI работает как раньше.
**Phase 1.6** — Telemetry collector. `/v1/telemetry/batch` + `/v1/admin/telemetry/summary` (HTTP Basic). Buffer + localStorage в desktop, flush каждые 5 минут.

**Phase 2.1** — Landing deployment prep (`landing/` копия `DESIGN_CONCEPT/` + nginx.conf.example + robots.txt + sitemap.xml).
**Phase 2.2** — Onboarding flow (`WelcomeModal.tsx` + `EmptyArchiveState.tsx`).
**Phase 2.6** — Support page + `/docs/*` (7 minimum-документов).

**Phase 2.3, 2.4, 2.5 не сделаны** по явному решению Сергея от 2026-05-23 («делай все, кроме статьи и видео») — Инфостарт article / demo video / Telegram outreach остаются за Сергеем.

См. `docs/sales_sprint/PHASE_1_REPORT.md`, `PHASE_2_REPORT.md`, `DEPLOY_CHECKLIST.md`.

### 3.8 Sprint 7 — Plan Analyzer MSSQL (tag `v0.7.0-internal`)

**Phase A** — PerformanceStudio binary bundle (`frontend/src-tauri/binaries/planview/`). Tauri command `get_planview_path`. Backend planview wrapper + RPC `plan_analyzer.*`. Frontend `PlanAnalyzer` screen.
**Phase B** — html-query-plan визуализация (SSMS-style).
**Phase C** — AI `explain_plan` endpoint + `AiPlanExplanationCard` component.
**Phase D** — planSQLText pipeline (автоэкстракт планов из ТЖ архива).
  - D.1: `scripts/patch-logcfg-for-plans.ps1` (готовит logcfg.xml для plansqltext)
  - D.2: `docs/onboarding/enable-plansqltext.md`
  - D.3–D.7: tj_parser.py с polem plan_text + UI tab «Из архива ТЖ» + AI prompt update
**Phase E** — Tests (50+ unit + regression на ~82 .sqlplan + perf benchmarks + edge cases). **E.5 (Manual demo session) — pending** (см. §7).
**Phase F** — Closure (REPORT + HANDOVER + ADR-037..040 + README/NOTICE update).

См. `SPRINT_7_FINAL_REPORT.md`, `OPUS_HANDOVER_SPRINT_7.md`, `SPRINT_7_PHASE_D_RESOLUTION_planSQLText.md`.

### 3.9 Sprint 8 — PostgreSQL Support (tag `v0.8.0-internal`)

**Phase A** — Discovery: подключение к реальной 1С-PG `pgBase` (PostgreSQL 18.1-2.1C). 6 категорий: environment, schema, EXPLAIN format, ТЖ на PG, pg_stat_statements, pev2 feasibility. Подтверждено: можно делать text + JSON, pev2 ставится через Web Component.
**Phase B** — PG Plan Analyzer Core (`v0.8.0-pg-core-internal` промежуточный тег):
  - B.1: tj_parser DBPOSTGRS support + engine field
  - B.2: PlanAnalyzer UI engine detection + `PgPlanTextView`
  - B.3: AI prompts split (MSSQL/PG) — PG-prompt знает 1С specifics
  - B.4: PG connection storage в OS keychain + re-EXPLAIN service (asyncpg)
  - B.5: pev2 интеграция через Vue Web Component
  - B.6: Tests + docs + closure
**Phase C** — PG Antipatterns Engine:
  - C.1: Refactor `sql/antipatterns.py` → `sql_antipatterns/` модуль (`tsql/` + `postgres/`)
  - C.2: **15 PG детекторов** (offset_without_limit, ilike_without_trgm, mchar_vs_text_comparison и др.), ≥30 тестов. 1С-context detection через regex heuristic (по `_reference\d+`, `mchar`/`mvarchar`).
  - C.3: Dispatcher + QueryAnalyzer UI integration (правильный engine — правильные правила)
  - C.4: AI prompt integration — `detected_antipatterns` передаются в Claude как context
  - C.5: Real-data tests + edge cases
  - C.6: ADR-045..048 + tag `v0.8.0-internal`

**Coverage курса 1С:Эксперт после Phase C:** раздел 8 (План запроса) 80% → 95%, раздел 6 (ТЖ) 70% → 85%, общее 55% → ~62%. См. `docs/sales_sprint/EXPERT_COURSE_COVERAGE.md`.

См. `SPRINT_8_FINAL_REPORT.md`, `SPRINT_8_PHASE_A_PG_DISCOVERY.md`, `SPRINT_8_PHASE_B_REPORT.md`, `SPRINT_8_PHASE_C_AND_DEMO_REPORT.md`.

### 3.10 Sprint 9 — Deep Real-World Testing (tag `v0.9.0-internal`)

Hardening-спринт, никаких новых аналитических фич. +126 тестов (Backend 861 → 907, Frontend 23 → 72, Server +31).

**Phase A** — Real-world fixtures: 32 MSSQL запроса в sp_executesql + 34 PG запроса (из ТЖ + синтетика) + 14 PG text планов + 13 .sqlplan.
**Phase B** — Regression suite (`test_real_world_regression.py`, `test_performance.py`, `test_architecture.py`).
**Phase C** — TJ-simulator expansion: 7 новых кнопок (TDEADLOCK X-X, цепочка дедлок, Memory, N+1, тяжёлый SDBL, PG-паттерны, длинная транзакция).
**Phase D** — `normalize_ai_enum()` generic helper (SEVERITY_MAPPING + IMPACT_MAPPING). CSS Design Token Lint (`scripts/check-css-tokens.ps1` + `npm run lint:css`). Первый прогон обнаружил **254 нарушения в 32 файлах** — задокументированный техдолг pre-token CSS.
**Phase E** — Performance benchmarks (интегрированы в Phase B): малый запрос < 50ms, средний < 200ms, 30 запросов throughput < 1сек, sp_executesql unwrap < 1ms, stability ≤ 3× первого.
**Phase F** — ADR-049..052 + tag + докуменация.

См. `SPRINT_9_REPORT.md`.

### 3.11 Sprint 10 — TJ Config Builder (tag `v0.10.0-internal`)

**Первый инструмент в новой группе Sidebar «ПОДГОТОВКА» (выше группы «АНАЛИЗ»).** Цель: пользователь без знания XML-синтаксиса получает готовый `logcfg.xml`.

**Phase A** — Server: `POST /v1/ai/generate_logcfg` (Haiku, filter unknown events, retry 2× на invalid JSON, graceful degradation). +20 тестов. Backend RPC: `logcfg.detect_platform` — 3 стратегии (folder scan / TCP probe localhost:1541 / fallback 8.3.24). +9 тестов.
**Phase B** — Frontend feature module `features/tj-config-builder/`:
  - `types.ts` (EventType, LogcfgConfig, Template, VolumeEstimate)
  - `xmlSerializer.ts` — pure TS, генерирует канонический logcfg.xml. +21 тест.
  - `volumeEstimator.ts` — heuristic-оценка (МБ/час) для quiet / typical / busy. +14 тестов.
  - `templates.ts` — 6 built-in шаблонов (minimal / slow_operations / full_diagnostic / deadlocks_only / expert_audit / pre_release_baseline). +14 тестов.
**Phase C** — UI: Graphical Builder (CSS Modules, только `--o-*` tokens). Двухколоночный layout: события/настройки | sticky VolumePreview. Без disclosure-треугольников (memory rule). Download-only через Blob URL.
**Phase D** — AI Wizard: textarea описания + select СУБД + кнопка «Сгенерировать» → explanation + таблица rationale + warnings + срок сбора. Кнопка «Применить в конструкторе» → переключает на GraphicalBuilderTab с AI-конфигом.
**Phase E** — Sprint 10 closure: ADR-053..056 + REPORT + tag.

+78 новых тестов (Frontend 72 → 121).

См. `SPRINT_10_REPORT.md`.

### 3.12 Sprint 10 Post-Release Hotfix (commits `38d423a`, `6c0bb98`, `825f770`, `ce1a4ed`)

После релиза — верификация по официальной документации 1С (раздел 3.14 «Настройка ТЖ») + ручное тестирование. **Три независимых критических бага:**

**Bug 1 — Duration filter units, 100× занижение.** `threshold_cs` (centiseconds = 10 мс) писался в `<gt property="duration" value>` напрямую, но 1С ждёт **десятитысячные доли секунды** (1 unit = 100 мкс). Фактор пропущен. Фикс: умножение на 100. Тесты обновлены.

**Bug 2 — Тёмные тултипы.** `XmlPreview.module.css` и `EventHelp.module.css` использовали несуществующий `var(--o-surface)` → пустой fallback → webview дефолт `#252526` (VS Code Dark+). Фикс: замена на `var(--o-panel, #ffffff)` + добавление недостающих токенов в `optimyzer-design.css`.

**Bug 3 — Tauri fs permissions: writeTextFile падал + ложный setSaved.** В Tauri 2 `fs:default` = только чтение из app-директорий. Запись в произвольный путь требует явного `fs:allow-write-text-file`. Бага усугублялась `try/catch` который маскировал permission error и заваливал `setSaved(true)` несмотря на отсутствие файла. Фикс: разрешение в `capabilities/default.json` + удаление Blob-fallback и ложного success.

**Дополнительная верификация по разделу 3.14:** 100% соответствие по структуре XML (namespace, `<config>`, `<log>`, `<event>`, `<plansql/>` position и пр.). Регистр имён событий — uppercase (стандарт сообщества, документация допускает любой). Событие `ATTN` есть у нас, в таблице документации нет — есть в Infostart-сообществе для 8.3.24+. Наш инструмент актуальнее документации.

Открытые вопросы из hotfix-сессии (Q1–Q3) частично адресованы в §6.

См. `SPRINT_10_HOTFIX_REPORT.md`.

### 3.13 Sprint 11 — AI Caching + Performance Regression Tracking (tag `v0.11.0-internal`, не запушен)

**Двойной фокус:**
1. **AI Caching** (Phase A–D) — критично для unit economics. Без кеша: $60–90/мес/юзер AI cost vs выручка Pro 9 900 ₽ → убыточно. Cel: 70–80% hit rate → $5–10/мес/юзер.
2. **Performance Regression Tracking** (Phase E–F) — use case «после релиза стало хуже».

**Phase A** — `server/services/ai_cache/`: 5 файлов, ~600 LOC.
- `models.py`: CacheEntry, CacheType enum (7 типов), CacheStats
- `canonicalize.py`: 6 функций нормализации + `compute_cache_key` (sha256)
- `storage.py`: SQLite WAL mode, threading.local connections, CRUD + cleanup + stats
- `service.py`: CacheService (sync + async через asyncio.to_thread)
- TTL strategy: Plan AI = forever, Query = 90d, Logcfg = 30d, Regression = forever
- PROMPT_VERSION pattern (bump = automatic invalidation)
- 62 теста (27 canonicalize + 13 storage + 22 service)

**Phase B** — Plan AI cache integration. `explain_plan_query()` → cache wrapper над `explain_mssql_plan()` + `explain_pg_plan()`. 4 cache type (XML, MSSQL TEXT, PG TEXT, PG JSON). `force_refresh` + `was_cached` + `cache_age_seconds` + `cache_key` fields. +11 тестов.

**Phase C** — Query AI + Logcfg AI cache integration. Same pattern. Canonicalization для Query: `canonical = f"sdbl={canonicalize_sdbl(query_sdbl)}|diag={sorted_json(diagnostics)}"`. +13 интеграционных тестов.

**Phase D** — Force Refresh UI + Rate Limiting. `services/rate_limiter.py`:
- PER_ITEM_COOLDOWN = 5 min
- PER_SESSION_LIMIT_PER_HOUR = 10
- HTTP 429 с детализированным `detail`
- `GET /v1/ai/force_refresh_status/{cache_key}` для UI countdown polling
- UI: `ForceRefreshButton.tsx` (icon-only 14×14 рядом с severity badge). Tooltip «Доступно через 4:23» **без упоминания cache** (memory rule «скрывать impl details»). НЕ показывает «⚡ из кэша» badge. Интегрирован в `AiPlanExplanationCard` (но не в Query/Logcfg — см. §6).
- 14 тестов.

**Phase E** — Regression Detection Engine. `backend/regression/`:
- `operation_matcher.py` — `compute_fingerprint = (operation_name, context_first_line_normalized)`. Нормализация убирает timestamps, UUIDs, usernames, session IDs, connection IDs, document numbers.
- `classifier.py` — 5 ChangeType (REGRESSION / IMPROVEMENT / NEW / DISAPPEARED / STABLE) + 3 Confidence (HIGH 20+, MEDIUM 5–20, LOW <5) + priority_score = `(ratio - 1) × log(count + 1) × current_p95`
- `data_loader.py` — DuckDB query на context_normalized (QUANTILE_CONT)
- RPC `regression.compute(baseline_archive_id, current_archive_id, threshold, min_samples, top_n)` → summary + regressions/improvements/new/disappeared/stable_count
- 50 тестов (13 matcher + 37 classifier)

**Phase F** — Regression UI + AI summary endpoint. ArchiveComparison новый таб «Регрессии операций»:
- Controls: threshold (1.5–10×, default 2.0) + min_samples (default 5)
- Summary grid: 5 SummaryCard
- RegressionSection × 4
- RegressionRow: operation_name, p95 baseline→current, Δ%, calls A→B, confidence badge
- `POST /v1/ai/explain_regression` (Haiku, TTL=forever, cache integration). **Frontend integration НЕ включена** — backend готов, UI вызывает не автоматически. См. §6 TD-Sprint12-A.

**Phase G** — Closure. ADR-057..061. SPRINT_11_REPORT. Tag `v0.11.0-internal` (создан, не запушен).

### 3.14 Параллельный side-track — открытое исследование

`docs/sales_sprint/OPENSOURCE_RESEARCH_REPORT.md` (47 KB) — исследование 4 open-source проектов и их использование в продукте:
- **bsl-language-server** (главный фокус) — bundled jar в `frontend/src-tauri/binaries/bsl-language-server/` (с JRE 21). 19 SDBL диагностик.
- **sqlglot** — Python SQL parser, основа `sql_antipatterns/`.
- **PerformanceStudio** — 30 правил T-SQL, bundled в `binaries/planview/`.
- **html-query-plan** — visualizer, bundled JS.

Все 4 — с attribution в `NOTICE.md`.

### 3.15 Параллельный side-track — CFE расширение `goslog-checker-1c`

В 2026-05-26..29 параллельно (в репозитории `D:\goslog-cfe-1c`, **не в Optimyzer**) собрано CFE-расширение «ГосЛог Проверка контрагентов» для 1С:Бухгалтерии 3.0. ~1500 строк BSL, 4 модуля, HTTP-сервис, регламентное задание, обработка с формой настроек, заимствование Контрагенты + 4 формы. Финальный артефакт `goslog_check_1.0.0.2.cfe` ~148 KB.

В `docs/IDEA_AI_1C_DEV_DESKTOP.md` (черновик от Сергея + Claude) — стратегическая идея: упаковать этот workflow в **AI-IDE для разработки 1С** как отдельный десктоп-продукт. Tldr: ~200× ускорение vs ручная разработка (15 минут vs неделя). Целевой рынок ~50–80 тыс. разработчиков расширений CFE в РФ. Защищённая ниша (русский язык + 1С specifics). Главный технический инсайт: даже умная модель **массово галлюцинирует синтаксис 1С**, без RAG по эталонной выгрузке (BP_XML) продукт не работает.

В `docs/IDEA_PUBLISH_GOSLOG_1C.md` (commit `eee38ee`) — handover для Opus по запуску `goslog`-расширения на Инфостарте.

**Это side-track. Не блокирует Sprint 12 Optimyzer.** Но Opus может посмотреть как input при планировании long-term roadmap.

---

## 4. Текущее покрытие функционала

### 4.1 По модулям

| Модуль | Что покрыто | Sprint |
|---|---|---|
| **Module 1: Investigation Workbench** | TJ ingest до 12 GiB, 6 pre-built views, SQL Console, Cross-filtering, Multi-archive Comparison, Export, Saved queries | 0–2 |
| **Module 2: Code Analysis** | bsl-LS 19 SDBL diagnostics, Configuration.xml + Predefined.xml парсер, 8 semantic rules | 4–5 (QueryAnalyzer экран скрыт) |
| **Module 3: Plan Analyzer** | MSSQL .sqlplan + paste + ТЖ extract, html-query-plan visualizer, PerformanceStudio 30 правил, AI explain. PG TEXT + JSON + ТЖ extract, pev2 (opt-in), re-EXPLAIN, AI explain с 1С-spec | 7–8 |
| **Module 4: SQL Antipatterns** | 9 T-SQL + 15 PG (1С-aware) | 6 + 8C |
| **Module 5: TJ Config Builder** | 6 templates, graphical builder, AI wizard, volume estimator | 10 |
| **AI Layer** | Plan explain (MSSQL/PG), Query explain (SDBL + diagnostics), Logcfg generate, Regression explain | 3 + 7 + 8 + 10 + 11 |
| **AI Cache** | Single-tier server-side, 4 cache types, TTL strategy, PROMPT_VERSION invalidation, force refresh + rate limit | 11 |
| **Regression Engine** | Operation matcher (fingerprint) + classifier (5 types + 3 confidence + priority) + UI (ArchiveComparison tab) | 11 |
| **Cloud (server)** | Yandex OAuth, JWT, Subscriptions/Credits/Devices/Usage, YooKassa, License activation, Telemetry, Soft caps | Sales Phase 1 |
| **Cabinet** | 7 страниц (Overview, Subscription, Credits, Devices, Payments, Usage, Settings), mobile responsive | Sales Phase 1.3 |
| **Landing + Docs** | Static HTML, nginx.conf, robots.txt, sitemap, 7 doc-страниц, Yandex.Metrika placeholder | Sales Phase 2.1, 2.6 |
| **Onboarding** | WelcomeModal + EmptyArchiveState | Sales Phase 2.2 |

### 4.2 Coverage курса 1С:Эксперт

Из `docs/sales_sprint/EXPERT_COURSE_COVERAGE.md` (актуально на конец Sprint 8):

| Раздел | Покрытие |
|---|---|
| 6. Технологический журнал | **85%** |
| 8. План запроса | **95%** |
| Общее покрытие материала курса | **~62%** |

Sprint 11 (regression) добавил покрытие use case «после релиза стало хуже» — частично закрывает разделы про мониторинг и сравнение версий.

---

## 5. Технические наблюдения для long-term планирования

### 5.1 AI flow inconsistency

Sprint 11 deviation (ADR-057) выявил: frontend ходит в `server/v1/ai/*` напрямую, минуя backend sidecar. Это удобно для cache (single-tier), но создаёт ассиметрию:

- **Sidecar (backend/)**: парсинг ТЖ, DuckDB queries, antipatterns engine, planview, regression
- **Server (server/)**: auth, billing, telemetry, **AI explain**

Если на Sprint 12+ появится use case «AI должен видеть данные из DuckDB» (например, AI summary по архиву) — придётся либо передавать данные через frontend (что дорого по сети), либо строить вторичный канал backend↔server. Сейчас этого нет, но архитектурный риск стоит держать в голове.

### 5.2 CSS техдолг — 254 нарушения в 32 файлах

Sprint 9 Phase D создал линтер. `npm run lint:css` показывает 254 hardcoded hex-цвета в 32 `*.module.css`. Это pre-token CSS из Sprint 0–3. ADR-052 принимает: identify-first, fix-as-you-go. **Sprint 12+ можно делать сабтаску «10 файлов в месяц» — за 3 месяца долг исчезает.**

### 5.3 Frontend test infrastructure

Sprint 11 Q5: `vitest.config.ts` использует Node environment без jsdom → component тесты технически невозможны. 122 frontend теста — это utility + serializer + helpers. Все UI компоненты (ForceRefreshButton, RegressionTab, etc.) непокрыты тестами. **TD-Sprint12-D (см. §6) — 4–6 часов на jsdom setup + ~40 component tests.**

### 5.4 Cache cleanup техдолг

Sprint 11: expired entries в `ai_cache.db` физически не удаляются — только не возвращаются при lookup. Оценочно 50–100 МБ/год при активном использовании. APScheduler уже есть в `server/services/scheduler.py` (используется для billing). Раз в сутки cleanup — 1–2 часа работы. **TD-Sprint12-C.**

### 5.5 Sales Sprint stop rules ждут production

Все 6 stop rules Sprint 1.1–1.6 (Phase_1_Report) требуют:
- Yandex OAuth credentials (production)
- YooKassa account (production)
- Domain `optimyzer.pro` + VDS
- nginx + SSL (certbot)
- PostgreSQL вместо SQLite
- production Anthropic key с ротацией

**Без них код не верифицируется** — но он code-complete. См. `docs/sales_sprint/DEPLOY_CHECKLIST.md` для детального плана.

**Memory rule reminder:** при любом деплое на VDS первым делом читать `DEPLOY_CHECKLIST.md`. Критично: Yandex OAuth redirect сейчас `http://localhost/success` (тест Сергея), при деплое менять на `https://api.optimyzer.pro/success` и в Yandex admin, и в `.env`.

### 5.6 Manual demo долги

Из TaskList:
- **Sprint 7 E.5 — Manual demo session** (pending) — не было полноценной демки plan analyzer + ТЖ pipeline
- **Sprint 11 — Manual demo от Сергея** (запрошено в финальном summary) — cache hit rate validation на реальных архивах + force refresh cooldown + regression detection + per-session rate limit

Без этих демо нельзя ставить v0.7.0 / v0.11.0 как окончательно зрелые. Но это **не блокирующий** open vопрос — функционал прошёл automated tests.

---

## 6. Технический долг — backlog для Sprint 12 prioritization

### 6.1 Из Sprint 11

| ID | Описание | Эфорт | Приоритет |
|----|----------|--------|----------|
| **TD-Sprint12-A** | AI summary inline в Regression UI. Backend `POST /v1/ai/explain_regression` готов + cached + TTL forever. UI не вызывает автоматически. Опции: A) авто для top-3, B) кнопка на каждой row, C) expandable. Рекомендация: B или C — A пугает юзеров расходом quota. | 4–6h | **Medium** |
| **TD-Sprint12-B** | ForceRefreshButton в Query/Logcfg AI cards. Сейчас только в `AiPlanExplanationCard`. Интеграция: импорт + проброс `onForceRefresh` + `response.cache_key`. | 30 мин | Low |
| **TD-Sprint12-C** | Cache cleanup scheduler. Сейчас expired entries остаются физически. APScheduler есть. Раз в сутки cleanup. | 1–2h | **Medium** |
| **TD-Sprint12-D** | jsdom setup + ~40 component tests. Sprint 11 hit dead-end: vitest config без jsdom → component tests невозможны. | 4–6h | **Medium** |
| **TD-Sprint12-E** | Cache stats endpoint admin-only (`/admin/ai-cache`). `CacheService.get_stats()` готов. Memory rule: UI **не** показывать юзеру (impl detail). | 2h | Low |
| **TD-Sprint12-F** | Real-data benchmarks: cache lookup time (< 5ms теоретически), hit rate measurement в production traffic. | 1–2 дня | Low |

### 6.2 Из Sprint 10 hotfix

| ID | Описание | Эфорт |
|---|---|---|
| **TD-S10-Q1** | UAC при записи `C:\Program Files\...`. Сейчас бросает access denied. Опция C (рекомендовать `%USERPROFILE%\Documents\` + onboarding doc) — zero-code. Опция B (`write_file_as_admin` через `ShellExecuteEx(runas)`) — для Sprint 12. | C: 30 мин, B: 4–6h |
| **TD-S10-Q2** | CSS design-token contract enforcement. Policy: «никаких новых `--o-*` токенов вне `optimyzer-design.css`». Auto-check через grep в CI. | 1–2h |
| **TD-S10-Q3** | Integration smoke test для Save в TjConfigBuilder. Сейчас 50 unit-tests — чистая логика без Tauri API. Playwright + `@tauri-apps/api/path`. | 4h |

### 6.3 Из Sprint 9

| ID | Описание | Эфорт |
|---|---|---|
| **TD-S9-CSS** | 254 hardcoded hex-цвета в 32 CSS module. Identify-first done. Fix-as-you-go. | ~10 файлов/спринт |
| **TD-S9-FIXTURES** | `pg_plans_json/` (PG планы в FORMAT JSON), `tj_archives/` (реальные архивы ТЖ). Backlog. | — |

### 6.4 Из Sales Sprint Phase 1

| ID | Описание | Когда |
|---|---|---|
| Tauri OS keychain для JWT | требует new Tauri plugin + Rust перекомпил | Phase 2.x / Sprint 13+ |
| YooKassa refund flow | low priority, ручной через support | по запросу |
| Email-уведомления transactional | требует production SMTP | Phase 2.1 deploy time |
| Telegram bot | nice-to-have | Phase 2.x |
| 3-tabs Settings → Аккаунт детали | используем 2-tab упрощенный | по фидбеку |

### 6.5 Из Sprint 10 scope-out

| Фича | Причина scope-out |
|---|---|
| Apply locally (авто-копирование logcfg.xml) | UAC, risk |
| Валидация пути папки логов | Nice-to-have |
| История сохранённых конфигураций | Отдельная фича |
| Подсказка по размеру диска (disk free) | Tauri system-info plugin |
| Импорт существующего logcfg.xml | Парсинг XML |

---

## 7. Открытые decision points для Сергея

| # | Решение | Status | Влияние |
|---|---|---|---|
| 1 | **Manual demo Sprint 11** (cache hit rate, force refresh cooldown, regression detection) | Ожидает Сергея | Без этого `v0.11.0-internal` нельзя считать окончательно зрелым. Не блокирует Sprint 12. |
| 2 | **Push tag `v0.11.0-internal`** на origin | Ожидает явного запроса | Сейчас тег только локально (репозиторий `up-to-date` по коммитам, но тег не запушен) |
| 3 | **Sprint 10.5** (Web TJ Config Builder + SEO) timing | Когда решит Сергей | Не блокирует Sprint 12. Web-версия для SEO/lead generation. |
| 4 | **Sprint 12 scope**: какие TD из §6 интегрировать в Advanced features (Memory Leaks / Lock Wait Anatomy / Sessions Gantt / Transaction Timeline)? | Ожидает Opus + Сергея | См. §8 рекомендации. |
| 5 | **Production deploy timing** | Ожидает credentials + VDS | Это не sprint-вопрос, а оперативный — но без него Sales Sprint stop rules не закрыть. |

---

## 8. Roadmap recap (Sprint 12 onwards)

Из `OPUS_HANDOVER_SPRINT_11.md` (моя версия):

```
✅ Sprint 10   — TJ Config Builder desktop (v0.10.0-internal)
✅ Sprint 11   — AI Caching + Regression Tracking (v0.11.0-internal)
   Sprint 10.5 — Web TJ Config Builder + SEO (когда решит Сергей)
   Sprint 12   — Advanced (Memory Leaks, Lock Wait Anatomy, Sessions Gantt,
                 Transaction Timeline) + cache stats UI + regression AI summaries inline
   Sprint 13   — AI Rewriter v2 + Team Workspace
   Sprint 14   — UX Reorganization + Onboarding (pipeline-driven UI)
   Финал       — Infrastructure + Marketing + Launch
```

### 8.1 Sprint 12 — рекомендованный scope (мнение Claude как executor)

**Основной фокус (Advanced features):**

1. **Memory Leaks анализ** — детектор «утечки памяти rphost через долгие транзакции». Источник данных: ТЖ + DuckDB. Может частично использовать Sprint 11 priority_score formula.
2. **Lock Wait Anatomy** — таймлайн ожиданий блокировок с дерево cascading lock chains. UI похож на pev2 для PG, но для TLOCK/TDEADLOCK событий.
3. **Sessions Gantt** — гант-диаграмма параллельных сессий с overlays для long-running locks/transactions.
4. **Transaction Timeline** — для каждой open transaction: что внутри, сколько ждёт, какие locks держит, на какие ждёт.

**Bundled TD (из §6):**

- **TD-Sprint12-A** (AI summary inline в Regression UI) — 4–6h, complements Sprint 11 Phase F
- **TD-Sprint12-C** (cache cleanup scheduler) — 1–2h, prod readiness
- **TD-S10-Q2** (CSS design-token contract) — 1–2h, prevents future bugs

**Defer на Sprint 13+:**

- TD-Sprint12-D (jsdom test infrastructure)
- TD-Sprint12-E (cache stats UI admin-only)
- TD-Sprint12-F (real-data benchmarks)
- TD-S10-Q1 (UAC write_file_as_admin)
- TD-S10-Q3 (Playwright smoke tests)

### 8.2 Sprint 12 — гипотезы по этапам

(черновик, для оценки Opus, не финальный план)

- **Phase A — Discovery + UX research.** Анализ существующих инструментов (КИП, ЦУП, 1С:Эксперт). Сейчас в `docs/2.4-2.13 PDF` Сергей имеет учебники по этим разделам. Цель: понять, чего ждёт 1С:Эксперт от lock wait / memory leak инструментария.
- **Phase B — TJ event coverage.** TLOCK события parser (если не покрыты). TDEADLOCK extended fields. MEM events parser. Sprint 9 Phase C-7..13 уже добавил TJ-simulator scenarios — есть на чём тестировать.
- **Phase C — Backend analytics.** DuckDB queries для lock chain reconstruction + memory time-series + session lifecycle. RPC методы `locks.chain_analysis`, `memory.timeline`, `sessions.gantt`, `transactions.timeline`.
- **Phase D — Frontend UI** (3–4 новых экрана в группу «АНАЛИЗ»).
- **Phase E — AI integration** (через server cache layer от Sprint 11).
- **Phase F — Tests + ADRs + tag `v0.12.0-internal`.**

### 8.3 Sprint 13+ (стратегический горизонт)

- **AI Rewriter v2** — не только explain, а **suggest fixes**. Для SDBL запросов + для logcfg.xml + для regression hot-spots. Технический риск: AI должен генерировать корректный 1С-синтаксис (см. инсайт из §3.15 — массовые галлюцинации без RAG).
- **Team Workspace** — multi-tenant. Влияет на cache (изоляция per-tenant) и subscription model. Большая работа на cloud-стороне.
- **UX Reorganization (pipeline-driven UI)** — переосмысление flow: вместо набора экранов в Sidebar — пошаговый pipeline. Влияет на Onboarding flow и Welcome modal.
- **Launch readiness** — все Sales Sprint stop rules + first paying customer + market validation telemetry → Pro pricing iteration.

---

## 9. Стратегические side ideas (черновики, не commits)

### 9.1 IDEA_AI_1C_DEV_DESKTOP (commit `b804d00`)

Отдельный продукт — AI-IDE для разработки 1С-расширений. Базируется на инсайтах из работы над CFE `goslog-checker-1c` (Sprint side-track):
- **Доказанная ценность:** ~200× ускорение (15 минут vs неделя)
- **Рынок:** ~50–80 тыс. CFE-разработчиков в РФ
- **Защищённая ниша:** русский + 1С-specifics → Cursor/Copilot сюда не пойдут
- **Главный технический риск:** массовые галлюцинации синтаксиса 1С без RAG по эталонной конфигурации
- **Реюзаемая инфраструктура из Optimyzer:** server/ (auth + subscriptions + telemetry), cabinet/, landing/, telemetry pipeline

**Вопрос Opus:** включать ли разработку этого продукта в roadmap Optimyzer (как Module N) или выделять в отдельный repo?

### 9.2 IDEA_PUBLISH_GOSLOG_1C (commit `eee38ee`)

Handover для запуска `goslog-checker-1c.cfe` на Инфостарте. **Не относится к Optimyzer** — это side-channel monetization для другого продукта Сергея. Включил здесь только для полноты — Opus может игнорировать при планировании Sprint 12.

---

## 10. Рекомендации для Opus

### 10.1 Перед Sprint 12 promt — синхронизация с Сергеем

Получить ответы на 4 decision points (§7):
1. Manual demo Sprint 11 — Когда? Какие сценарии? Что критично проверить?
2. Push v0.11.0-internal — давать или нет?
3. Sprint 10.5 timing — до Sprint 12 или после?
4. Sprint 12 scope — все 4 Advanced features в один спринт, или сплитить?

### 10.2 При планировании Sprint 12

- **Sprint 12 — feature-heavy.** 4 новых типа аналитики (Memory Leaks / Lock Wait / Sessions Gantt / Transaction Timeline) — потенциально 8–10 phases. Если Сергей хочет быстрый delivery — сплитить на Sprint 12A (Lock Wait + Sessions Gantt) и Sprint 12B (Memory Leaks + Transaction Timeline).
- **Bundle TDs аккуратно.** Соблазн добавить 6 TD сверху — но Sprint 11 показал риск: deviation от spec случается, лучше иметь slack. Рекомендация: 3 TD максимум (A + C + S10-Q2).
- **Обнули prompt** — Sprint 12 promt не должен полагаться на TaskList из Sprint 11 (118 пунктов, многое уже неактуально). Чистый prompt с новыми Sprint 12 phases A..F.

### 10.3 Технические гайды (memory rules) для prompts

Опус когда пишет prompt — должен напомнить executor про:
- **`scripts/check-css-tokens.ps1`** есть и работает — новые компоненты в Sprint 12 должны не добавлять hardcoded цветов.
- **`npm run lint:css`** в `frontend/package.json`.
- **`server/services/ai_cache/`** — любой новый AI endpoint должен оборачиваться через cache (Sprint 11 pattern).
- **`backend/regression/`** — paт `priority_score` formula можно реюзать для других sorting задач.
- **OS keychain для секретов** (Sprint 8 B.4 PG connection password + Sales Sprint 1.5 JWT) — паттерн установлен.
- **PROMPT_VERSION pattern** для AI invalidation — все новые AI endpoints должны иметь свою константу.
- **Telemetry events** для новых UI экранов: `useTelemetryFlush` + `screen_view` + custom events (Sales Sprint 1.6).
- **CSS only `--o-*` tokens** — никаких hardcoded hex (memory rule + Sprint 10 hotfix Q2).
- **Никаких упоминаний 54-ФЗ / 152-ФЗ / GDPR / compliance / законов** в UI, docs, code comments, commits (memory rule).
- **Show raw SQL, not normalized** — в UI экранах никогда не показывать `sql_text_normalized` (со «?»). Только `sql_text` (raw) или ARG_MAX exemplar (memory rule).
- **Hide impl details** — кеш / токены / модель / latency не показывать в UI. Только результат (memory rule).

### 10.4 Long-term архитектурные вопросы

- **Multi-tenancy** — single-tier cache shared globally. При переходе на Team Workspace нужна изоляция per-tenant. Sprint 13+ decision.
- **Two-tier cache deferred** — если потребуется «cache travels с архивом» (export/share archive с встроенным cache subset) — рефактор AI flow через backend sidecar или archive_id фильтр в server.
- **AI cost monitoring** — Sprint 11 даёт cache hit rate, но не total spend. Нужен `/admin/ai-spend` endpoint и алерты. Не критично, но полезно для бюджетирования.
- **CSS техдолг** — 254 нарушения, identify-first done. Когда брать «fix-as-you-go» по 10 файлов? Sprint 12 могло бы добавить эту привычку.

---

## 11. Чек-лист для Opus при возврате к проекту

При следующем входе в проект Opus должен **в первую очередь:**

1. Прочитать **этот файл** (`docs/OPUS_HANDOVER_2026_05_29_FULL_AUDIT.md`) — single point of entry.
2. Свериться с **`docs/sales_sprint/SPRINT_11_REPORT.md`** + **`docs/OPUS_HANDOVER_SPRINT_11.md`** для деталей Sprint 11.
3. Посмотреть **`docs/DECISIONS.md`** — список 60 ADR.
4. Получить от Сергея ответы на §7 (4 decision points).
5. Согласовать Sprint 12 scope (4 Advanced features + 3 TDs?) или split (12A + 12B).
6. Написать `SPRINT_12_PROMT.md` следуя `docs/PROMPT_AUTHORING_STANDARD.md`.

**Что НЕ нужно делать:**

- Не пересчитывать TaskList от 0 — нынешний список (118 tasks, многое pending=Manual demo) — устаревший контекст, не критичный для Sprint 12.
- Не трогать tag `v0.11.0-internal` (создан, не запушен) без явного запроса Сергея.
- Не возвращать QueryAnalyzer в Sidebar — это решение Сергея (commit `46c7bc1`), не bug.

---

## Подпись

**Подготовил:** Claude Sonnet (executor role, 1M context)
**По состоянию на:** 2026-05-29 (через 3 дня после Sprint 11 closure)
**Для:** Claude Opus 4.7 (architect role) при планировании Sprint 12
**Базируется на:** прямой инспекции репозитория `D:\1C-Optimyzer` — не пересказ предыдущих handover'ов
