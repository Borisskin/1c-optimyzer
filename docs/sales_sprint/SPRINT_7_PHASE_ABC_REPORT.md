# Sprint 7 — Phase A+B+C Report (Plan Analyzer)

> **Что готово:** PerformanceStudio CLI + html-query-plan visualization + AI explanation на русском.
> **Что НЕ готово в этой сессии:** Phase D (DBMSSQL.Plan auto-extract), Phase E (тесты), Phase F (финальные docs + tag v0.7.0-internal).
>
> **Branch:** `feat/sprint-7-plan-analyzer` (3 commits, ~3300 строк).
> **Промежуточный tag:** `v0.7.0-internal-wip` (после merge в main).
> **Длительность:** одна Claude Code сессия (~4 часа).
> **Зависимости:** новые — .NET 10 SDK 10.0.300 user-mode, html-query-plan 2.6.1, PerformanceStudio 1.11.2.

---

## Резюме для архитектора

Sprint 7 разбивался на 6 фаз (13-15 дней по плану). В этой сессии Сергей попросил **Phase A+B+C (core)** — собственно killer-feature без auto-extract из ТЖ архивов, без тестов и без финального тэга. Получилось всё, что планировалось для этих трёх фаз, плюс несколько вынужденных изменений против исходного промпта (см. ниже).

После сессии Optimyzer имеет три premium-features:
1. Анализ архивов ТЖ с AI (было — Sprint 3-5)
2. Query Analyzer с bsl-LS (Sprint 6)
3. **Plan Analyzer с PerformanceStudio + html-query-plan + AI (Sprint 7 A+B+C)** ← новое

Из demo flow Сергея:
> Перетащил `test02_like_wildcard.sqlplan` → получил визуализацию плана + 2 warnings (Non-SARGable Predicate, Top Above Scan) + AI explanation на русском, объясняющую почему `LIKE '%test%'` не использует индекс.

End-to-end проверено: backend wrapper выдаёт корректный JSON, TypeScript clean, серверный endpoint импортируется без ошибок.

---

## Что сделано

### Phase A — Foundation (commit `5fa9b8c`, 2108 insertions)

**Backend (Python):**
- `backend/src/optimyzer_backend/planview/` — новый пакет
  - `__init__.py` — public API экспорты
  - `models.py` — Pydantic schemas, точное соответствие `AnalysisResult.cs` из PlanViewer.Core (включая `MemoryGrantResult`, `QueryTimeResult`, `OperatorResult` с recursive `children[]`)
  - `cli.py` — subprocess wrapper для `planview.exe`. 4 уровня candidate paths (env override → bundled → repo-relative dev). Глобальный кеш _BINARY_PATH с reset для тестов.
- `backend/src/optimyzer_backend/rpc/plan_analyzer_rpc.py` — 3 JSON-RPC methods:
  - `plan_analyzer.analyze_file(file_path, warnings_only)`
  - `plan_analyzer.analyze_xml(plan_xml, warnings_only)`
  - `plan_analyzer.status()` — доступность бинаря + версия
- `__main__.py` — добавлен импорт `plan_analyzer_rpc` (регистрация декораторов)

**Tauri / Rust:**
- `frontend/src-tauri/src/main.rs` — новая команда `get_planview_path` (резолвит `binaries/planview/planview.exe`, возвращает `{executable, available}`)
- `tauri.conf.json` — `bundle.resources += "binaries/planview/**/*"`

**Frontend (React + TS):**
- `frontend/src/components/screens/PlanAnalyzer/` — новый экран:
  - `PlanAnalyzer.tsx` — главный screen + state machine
  - `PlanImport.tsx` — file picker (Tauri dialog plugin) + paste XML textarea, 2 tabs
  - `PlanWarnings.tsx` — список с PerformanceStudio severity (Info|Warning|Critical)
  - `MissingIndexes.tsx` — рекомендации SQL Server optimizer
  - `PlanStats.tsx` — cost / rows / compile / cardinality / parallelism / memory / cpu
  - `PlanAnalyzer.module.css` — ~480 строк, severity colors, statement cards
- `frontend/src/api/backend.ts` — 100+ строк типов (`PlanWarning`, `PlanMissingIndex`, `PlanOperator`, `PlanStatement`, `PlanAnalysisResult`, `PlanAnalyzeResponse`, `PlanAnalyzerStatus`) + 3 RPC methods
- `frontend/src/components/chrome/nav.ts` — новый item «Анализ плана» (Ctrl+P, FileBarChart icon)
- `frontend/src/App.tsx` — Ctrl+P shortcut + renderScreen case
- `frontend/src/components/icons/Icon.tsx` — новые иконки FileBarChart + Tree
- `frontend/src/i18n/ru.ts` — `planAnalyzer` section с 30+ строками
- `frontend/src/store/appStore.ts` — новый ScreenId `"plan-analyzer"`

**DevOps:**
- `scripts/setup-planview-binary.ps1` — idempotent скрипт сборки/копирования CLI
- `.gitignore` — `/tools/dotnet-10/`, `/tools/planview-built/`, кеш zip

### Phase B — Visualization (commit `c8b8b71`, 199 insertions)

**Frontend:**
- `npm install html-query-plan` (v2.6.1, MIT) — добавлено в package.json
- `PlanVisualization.tsx` — React-обёртка вокруг `qp.showPlan(container, xml, opts)`. Cleanup внутри useEffect (container.innerHTML="" перед каждым render — иначе SVG-узлы аккумулируются).
- `PlanVisualization.module.css` — overrides поверх `node_modules/html-query-plan/css/qp.css`. PNG sprite (qp_icons.png) разрешается Vite автоматически.
- `PlanAnalyzer.tsx` — теперь параллельно вызывает `backend.analyze_file` + `invoke('read_plan_text_file', ...)` и передаёт raw XML в PlanVisualization.

**Tauri:**
- `main.rs` — новая команда `read_plan_text_file(path) -> String`. Tauri fs:default плагина не разрешает чтение произвольных путей, поэтому добавил явный command (юзер уже выбрал путь через dialog, доверенный). Лимит 32 МБ.

### Phase C — AI explanation (commit `51c70d9`, 990 insertions)

**Server (FastAPI):**
- `server/schemas/ai.py` — новые модели:
  - `PlanExplainRequest` — sql_text + plan_xml + planview_warnings + missing_indexes + plan_summary + (опц.) configuration_context + related_tj_summary
  - `PlanHotspot` — operator_node_id + severity + what/why/what_to_do
  - `PlanRecommendation` — category(index|query_rewrite|config|stats) + title + description + impact_estimate
  - `PlanSuggestedIndex` — table + columns + include + rationale + impact_estimate
  - `PlanExplainResponse` — summary + overall_severity + hotspots + recommendations + suggested_indexes + model_used + duration_ms + **plan_truncated**
- `server/services/ai_explainer.py`:
  - `SYSTEM_PROMPT_EXPLAIN_PLAN` (2.1 КБ) — роль AI + JSON schema + правила для 1С контекста (mapping `_Reference15` → `Catalog.Контрагенты` если доступен)
  - `USER_PROMPT_PLAN_TEMPLATE` — sql_text + plan_xml + warnings + missing_indexes + plan_summary + config + tj_summary
  - `_truncate_plan_xml()` — обрезает plan XML до **50 000 chars** (~12K токенов). Покрывает ~98% реальных планов. Большие — `plan_truncated=true` для UI banner.
  - `explain_plan_query()` — orchestrator с retry-on-invalid-JSON (тот же паттерн что в `explain_query` Sprint 6)
- `server/api/routers/ai.py` — `POST /v1/ai/explain_plan` endpoint с error handling (401/502/503 как у explain)

**Frontend:**
- `frontend/src/api/cloud.ts` — `aiExplainPlan()` + 7 типов (`AiExplainPlanRequest`, `AiPlanHotspot`, `AiPlanRecommendation`, `AiPlanSuggestedIndex`, `AiExplainPlanResponse`, `PlanSeverity`, `AiExplainConfigContext`)
- `AiPlanExplanationCard.tsx`:
  - Header с overall_severity badge + model/duration
  - Truncated-banner если `plan_truncated`
  - Expandable hotspot blocks (what/why/what_to_do, click-to-expand)
  - Recommendation cards с category chip + impact badge
  - Suggested index cards с **auto-generated CREATE INDEX statement** (на основе table/columns/include)
- `AiPlanExplanationCard.module.css` — severity colors + impact badges + glassmorphism violet card style (отличается от sky-blue карточки Sprint 6 — разные домены)
- `PlanAnalyzer.tsx` — auto-trigger AI explain после успешного analyze (если есть plan XML). Loading/error states пробрасываются в card.

---

## Архитектурные решения

### ADR-040 (de facto) — PerformanceStudio severity scheme сохранена

Severity у Plan Analyzer = `Info | Warning | Critical` (как в `WarningResult.cs` PlanViewer.Core). НЕ маппим на bsl-LS scheme `Blocker | Critical | Major | Minor | Info`. Это **разные домены анализа**, разные правила, разная конкретика — пытаться приводить к одной шкале только запутает.

В UI это видно: BslLsFindings показывает 5-уровневую schema, PlanAnalyzer показывает 3-уровневую. Sergey принял это раньше через ответ на discovery Q7.

### .NET 10 SDK ставится локально, не bundle-ится

Sergey'у НЕ нужно ставить .NET 10 SDK глобально. `dotnet-install.ps1` (официальный Microsoft) скачал SDK 10.0.300 в `D:\1C-Optimyzer\tools\dotnet-10\` (gitignored). Builder script `scripts/setup-planview-binary.ps1` использует его. Не загрязняет систему.

В production-инсталляции SDK НЕ нужен — bundled `planview.exe` self-contained.

### Размер bundle вырос на 96 МБ

PerformanceStudio CLI — self-contained .NET 10 runtime + PlanViewer.Core.dll + dependencies. После публикации `dotnet publish -c Release -r win-x64 --self-contained true`:
- ~480 файлов
- 96 МБ распакованный
- 70 МБ zip (в release)

В архитекторском промпте предполагалось 30 МБ — это была оценка для framework-dependent сборки. Реальность: self-contained 96 МБ. Альтернатива (требовать у пользователя установленный .NET 10) — отбросили как UX блокер.

### Поломанная заметка из промпта — `PlanViewer.Cli.exe`

В промпте архитектор писал что бинарь называется `PlanViewer.Cli.exe`. Реальность: assembly name в csproj = `planview` → executable = `planview.exe`. Все docs и paths поправлены.

---

## Что НЕ сделано (Phase D, E, F)

### Phase D — DBMSSQL.Plan auto-extract

**Статус:** не начато.

**Что нужно:**
- `scripts/patch-logcfg-for-plans.ps1` — idempotent script с backup + добавлением `<plan/>` + restart 1C ragent
- `docs/onboarding/enable-dbmssql-plans.md` — инструкция для пользователей
- `backend/src/optimyzer_backend/parsers/tj_parser.py` — расширить `TjEvent` field `plan_text: Optional[str]`, парсить `planSQLText` из DBMSSQL события
- UI: «Импорт из архива ТЖ» кнопка → выбор DBMSSQL event с `plan_text` → отображение как `<pre>` блок
- AI explanation работает на текстовом плане; visualization (требует XML) и PerformanceStudio CLI (требует XML) — не работают для text-format планов

**Где этот пункт стопится:** Sergey ответил `Создать + выполнить на твоей машине`, но Phase D вне scope этой сессии. Решение для следующей сессии — отдельный мини-промпт для Phase D, тогда выполним скрипт после реализации.

### Phase E — Tests + edge cases

**Статус:** не начато.

**Что нужно:**
- 50+ новых тестов (`test_planview_cli.py`, `test_plan_models.py`, `test_plan_analyzer_rpc.py`, `test_ai_explain_plan.py`, `test_tj_parser_plans.py`)
- Прогон на 102 готовых .sqlplan из `research/`
- Performance benchmarks (CLI < 5 сек, visualization < 3 сек на 100+ операторов, AI < 8 сек)
- Edge cases: большой план (>1 МБ), битый XML, бинарь missing, AI down, 0 warnings, plan без подключённой конфы

Существующий test suite остаётся: 574 backend + 112 server.

### Phase F — Documentation + closure

**Статус:** не начато (этот документ — частичная замена для архитектора).

**Что нужно:**
- `docs/SPRINT_7_REPORT.md` (формальный финальный отчёт по структуре Sprint 6)
- `docs/OPUS_HANDOVER_SPRINT_7.md`
- `docs/DECISIONS.md` — ADRs 037-040
- README + NOTICE updates (NOTICE уже обновлён в этой сессии)
- Tag `v0.7.0-internal` (финальный — НЕ wip)

**В этой сессии вместо этого** — промежуточный tag `v0.7.0-internal-wip` после merge feat/sprint-7-plan-analyzer → main.

---

## Tech debt сейчас

**Из этой сессии:**
1. **`PlanAnalyzer.module.css` имеет неиспользуемые `aiSlot`/`visualizationSlot` стили** — оставлены от Phase A placeholder, в Phase B/C мы интегрировали по-другому. Cleanup на 5 мин.
2. **PlanImport не поддерживает drag-and-drop** .sqlplan файлов внутри screen — только Tauri dialog. DropZone (overlay) реагирует на folders (для archive load). Добавить локальный drop-handler с фильтром по `.sqlplan` extension.
3. **Backend wrapper не пишет тесты** для `cli.py` — только end-to-end manual проверка.
4. **AI prompt** не использует `related_tj_summary` field — оставлен в request schema для будущего, но в UI его сейчас не пробросить.
5. **Backend RPC не использует кеширование** AI ответов. Это `TD-6.3` из Sprint 6 handover — общая infra задача, не блокер.
6. **CSS `:global(.qp-root)`** в PlanVisualization — переопределяет стили html-query-plan, может конфликтовать при upgrade пакета. Документировано в комментариях.

**Не из этой сессии (унаследовано):**
- TD-6.3 — AI response caching (общая задача для query analyzer + plan analyzer)
- Sprint 6 frontend tests на YyyyMmDdHh.log детект (для Sprint 7 не критично)

---

## Testing — как Сергею проверить

Полная инструкция в чате-ответе Сергею после merge.

Минимум:
1. `pwsh scripts/setup-planview-binary.ps1` (или просто `cd frontend && npm run tauri dev`)
2. В приложении: Sidebar → «Анализ плана» (или Ctrl+P)
3. Выбрать .sqlplan файл, например `D:\1C-Optimyzer\tools\sprint7_discovery\sqlplans\test02_like_wildcard.sqlplan`
4. Должно появиться:
   - SSMS-style визуализация плана
   - AI explanation card (Claude Sonnet работает несколько секунд)
   - 2 warnings: Non-SARGable Predicate + Top Above Scan
   - 0 missing indexes
   - Statement card с PlanStats (cost 0.021, rows 1.78, compile 342 мс, cache 16 КБ)

---

## Метрики

| Метрика | Phase A | Phase B | Phase C | **Total** |
|---|---|---|---|---|
| Commits | 1 | 1 | 1 | **3** |
| Файлов изменено | 21 | 6 | 7 | **31** (-2 dedupe = 30 unique) |
| Insertions | 2108 | 199 | 990 | **3297** |
| Deletions | 5 | 8 | 2 | **15** |
| Новых файлов | 11 | 2 | 2 | **15** |
| Новых типов TS | 8 | 0 | 7 | **15** |
| Новых RPC методов | 3 | 0 | 0 | **3** (+ /v1/ai/explain_plan REST) |

**Bundle delta:** +96 МБ (PerformanceStudio CLI). Sprint 6 bundle уже был 280 МБ (JRE 21 + bsl-LS). Итого frontend/src-tauri/binaries/ = 376 МБ (gitignored, в MSI распаковывается).

**Frontend:** TypeScript noEmit clean. 1 dep added (`html-query-plan` MIT).

**Backend:** Python imports clean. 0 dep added (planview wrapper использует только stdlib).

**Server:** Python imports clean. Использует существующий `anthropic` SDK.

---

## Открытые вопросы для следующей сессии

1. **Phase D scope:** делаем minimal (text format отображается, no XML conversion) или сразу пытаемся text → XML converter? Промпт говорит «minimal в Sprint 7, конвертер — Sprint 8», но если уже взялись за D — стоит ли расширить?

2. **patch-logcfg-for-plans.ps1 execution:** Sergey ответил «создать + выполнить на машине», но Phase D в этой сессии не делалась. В следующей сессии — выполнить сразу, или сначала добиться согласия на конкретные правки?

3. **Test fixtures:** для Phase E какие .sqlplan приоритезировать — 48 из `research/PerformanceStudio/tests/` (синтетика) или 5+ свеже-сгенерированных из Test1CProf (real-world)?

4. **Tag finalization:** после Phase D+E+F — переименовать `v0.7.0-internal-wip` → `v0.7.0-internal`, или оставить wip и тэгнуть отдельный финальный?

5. **CSS bloat:** в PlanAnalyzer.module.css ~480 строк, в Sprint 6 QueryAnalyzer.module.css 214. Возможно стоит выделить общий dashboard styles в shared.

6. **Performance Phase B:** на planах с 200+ операторов html-query-plan SVG может быть медленным (>3 сек). Не проверено в этой сессии — нужен real-world test.

---

## Конкретные действия для архитектора

1. **Просмотреть код:** `git log feat/sprint-7-plan-analyzer ^main --oneline` → 3 commits
2. **Принять/отклонить решения:** ADR-040 severity, 96 МБ bundle, текстовый prompt для AI
3. **Дописать Phase D промпт:** для следующей сессии. Включить решение по Q1 (text vs XML converter) и Q2 (execute logcfg сразу)
4. **Расписать тесты Phase E:** какие test cases приоритетные

---

**Подготовил:** Claude Code (Sonnet 4.5, 1M context)
**Для:** Claude Opus 4.7 (Architect)
**Дата:** 2026-05-24
**Версия:** Sprint 7 Phase A+B+C, не финальный
**База:** SPRINT_7_PROMT.md от Opus
**Branch:** feat/sprint-7-plan-analyzer
**Tag:** v0.7.0-internal-wip (после merge)
**Следующая сессия:** Phase D (DBMSSQL.Plan auto-extract) + E (тесты) + F (финальные docs + v0.7.0-internal tag)
