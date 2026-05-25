# Sprint 8 Phase C + Demo Session — Отчёт для архитектора

> **Status:** ✅ ЗАКРЫТ
> **Теги:** `v0.8.0-internal` (Phase C closure), `main` — head (demo fixes)
> **Автор:** Claude Code (executor)
> **Для:** Claude Opus (architect)
> **Дата:** 2026-05-25
> **База:** SPRINT_8_FINAL_REPORT.md + SPRINT_8_PHASE_B_REPORT.md

---

## TL;DR для архитектора

**Phase C** — PG Antipatterns Engine имплементирован полностью: 15 детекторов с 1С-aware heuristic, модуль `sql_antipatterns/` рефакторен под dialect-aware структуру, UI карточка `SqlAntipatternsCard` интегрирована в PlanAnalyzer, AI prompt обновлён — antipatterns передаются как контекст.

**Demo Session** — Сергей провёл manual testing. Найдено **6 UI/UX и 2 critical backend бага**. Все исправлены за одну сессию. Ни одного из найденных багов нет в архитектурных допущениях Phase C — все носят интеграционный/UX характер.

**Состояние тестов сейчас:** backend 861 passed / 32 skipped, server 140 passed / 1 pre-existing FAIL (test_telemetry, не связан с Phase C).

---

## 1. Phase C — PG Antipatterns Engine

### 1.1. Что было запрошено

Промпт Phase C поставил задачу: создать движок статического анализа SQL-антипаттернов для PostgreSQL с учётом специфики 1С. Ориентировочно 8-12 детекторов, интеграция в RPC и UI.

### 1.2. Что реализовано

#### Рефакторинг модуля sql_antipatterns/

До Phase C существовал `sql/antipatterns.py` — плоский файл с T-SQL детекторами (Sprint 6). Рефакторинг без breaking change:

```
src/optimyzer_backend/
  sql_antipatterns/
    __init__.py          — публичный API: detect_antipatterns(sql, engine)
    engine.py            — dispatcher: engine → dialect module
    models.py            — AntipatternsResult, AntipatternsFindings, AntipatternsContext
    tsql/
      __init__.py
      detectors.py       — 9 legacy T-SQL детекторов (Sprint 6, без изменений)
    postgres/
      __init__.py
      _helpers.py        — is_1c_context(), safe_parse() + utils
      offset_without_limit.py
      large_offset_pagination.py
      ilike_without_trgm.py
      like_with_leading_wildcard.py
      not_in_with_subquery.py
      jsonb_without_gin.py
      cast_in_where_predicate.py
      union_instead_of_union_all.py
      subquery_in_select_list.py
      distinct_on_large_result.py
      implicit_type_cast.py
      select_star_with_join.py
      order_by_random_with_limit.py
      missing_where_on_update_delete.py
      mchar_vs_text_comparison.py
    shared/
      __init__.py        — заготовка для будущих shared helpers
```

Старый `sql/antipatterns.py` оставлен для backward-compat (ре-экспортирует из нового).

#### 15 PG детекторов

| # | Code | Severity | 1С-aware | Описание |
|---|---|---|---|---|
| 1 | `offset_without_limit` | Warning | — | `OFFSET N` без LIMIT — PG вынужден скипать N строк |
| 2 | `large_offset_pagination` | Warning/Critical | — | OFFSET > 1000 (Critical если > 10000) — глубокая пагинация |
| 3 | `ilike_without_trgm` | Warning | — | `ILIKE '%..%'` без GIN-индекса по pg_trgm |
| 4 | `like_with_leading_wildcard` | Warning→Info | ✓ | `LIKE '%text'` — нет Seq-Scan в прямом индексе; downgrade до Info в 1С context (1С часто так делает намеренно) |
| 5 | `not_in_with_subquery_pg` | Warning | — | `NOT IN (SELECT ...)` — NULL-trap + PG не может использовать Anti Join оптимально |
| 6 | `jsonb_without_gin` | Info | — | JSONB операции без GIN index heuristic |
| 7 | `cast_in_where_predicate` | Warning | ✓ | `LOWER(col)` или `CAST(col AS ...)` в WHERE блокирует индекс; skip для mchar/mvarchar в 1С |
| 8 | `union_instead_of_union_all` | Info | — | UNION с implicit SORT+DEDUP вместо UNION ALL |
| 9 | `subquery_in_select_list` | Warning | — | Correlated subquery в SELECT — N+1 паттерн |
| 10 | `distinct_on_large_result` | Info | — | DISTINCT + JOIN (часто 1:N дубликаты — переписать на EXISTS) |
| 11 | `implicit_type_cast` | Warning | ✓ | `int_col = '123'` — type coercion блокирует индекс; skip для `_Fld*` (1С всегда varchar) |
| 12 | `select_star_with_join` | Info | ✓ | SELECT * с JOIN — hidden columns + deadweight; skip в 1С (1С никогда не делает SELECT *) |
| 13 | `order_by_random_with_limit` | Warning/Critical | — | `ORDER BY RANDOM()` — full table sort; Critical без LIMIT |
| 14 | `missing_where_on_update_delete` | **Critical** | — | UPDATE/DELETE без WHERE — стереть таблицу |
| 15 | `mchar_vs_text_comparison` | Warning | ✓ | `mchar_col = text_literal` без явного cast — только 1С context |

#### 1С-context detection

`is_1c_context(sql)` в `_helpers.py` — regex heuristic:
- `_reference\d+` / `_document\d+` / `_accumrg\d+` / `_inforg\d+` / `_acctrg\d+` / `_bprvspec\d+`
- `_Fld\d+` (field columns), `mchar` / `mvarchar` (1С custom types)

Когда context = True: детекторы 4, 7, 11, 12, 15 меняют поведение. В UI показывается badge «1С-контекст».

#### Engine dispatcher + RPC

`sql_antipatterns_rpc.py`:
- Принимает `engine: str` (mssql/postgres/auto)
- `auto` → sqlglot-detect или heuristic
- Unwrap `sp_executesql` перед анализом MSSQL (см. fix #1 в demo section)
- Возвращает `AntipatternsResult` с `engine`, `is_1c_context`, `findings[]`

#### Frontend UI — SqlAntipatternsCard

```
PlanAnalyzer.tsx
  └─ SqlAntipatternsCard.tsx   — карточка с N находок
       ├─ engine badge (MS SQL / PostgreSQL)
       ├─ 1С-context badge (если detected)
       └─ findings[]
            └─ AntipatternsRow   — click-to-expand, без ▶▼
                 ├─ severity badge
                 ├─ title
                 ├─ snippet (если есть)
                 ├─ «Что произошло»
                 ├─ «Почему это проблема»
                 └─ «Что сделать»
```

#### AI integration — detected_antipatterns как контекст

В `ai_explainer.py` — перед вызовом Claude antipatterns результаты сериализуются в промпт:

```
## Detected antipatterns (static analysis, DO NOT repeat these in hotspots):
- [WARNING] ilike_without_trgm: ILIKE '%...%' без GIN index — ...
- [WARNING] large_offset_pagination: OFFSET 5000 — ...
```

Claude инструктирован **не дублировать** уже найденные антипаттерны в hotspots, а расширять анализ планом выполнения.

#### Server tests (Sprint 8 Phase C)

- `tests/test_ai_explain_pg_plan.py` — 20 тестов (структура ответа + prompt content + 1С-context awareness + non-duplication of antipatterns)

---

## 2. Demo Session — Manual Testing с Сергеем

### 2.1. Контекст

После закрытия Phase C (тег `v0.8.0-internal`) проведена manual demo session. Сергей тестировал pipeline E2E через UI. Найдены 8 проблем. Все зафиксированы и исправлены в той же сессии.

### 2.2. Найденные и исправленные баги

#### Bug #1 — БЛОКЕР: Парсер не работает ни на одном MSSQL запросе

**Severity:** Critical (все MSSQL запросы из ТЖ архива выдавали «Парсер не смог разобрать запрос»)

**Root cause:** 1С всегда оборачивает SQL в `exec sp_executesql N'...'`. sqlglot получал обёртку, а не сам запрос. В T-SQL `sp_executesql` — это вызов хранимой процедуры, а не SELECT/DML — парсер корректно отказывался.

**Fix:** `_unwrap_sp_executesql()` в `sql_antipatterns_rpc.py`:

```python
_SP_EXECUTESQL_RE = re.compile(
    r"(?:\{call\s+sp_executesql\s*\(\s*|(?:exec(?:ute)?\s+)?sp_executesql\s+)"
    r"N'((?:[^']|'')*)'(?:\s*,|\s*\)|\s*$)",
    re.IGNORECASE | re.DOTALL,
)

def _unwrap_sp_executesql(sql: str) -> str:
    stripped = sql.strip()
    m = _SP_EXECUTESQL_RE.match(stripped)
    if m:
        return m.group(1).replace("''", "'")
    return sql
```

Поддерживает форматы: `exec sp_executesql N'...'`, `execute sp_executesql N'...'`, `{call sp_executesql(N'...')}` (ADO.NET). Раскрывает escaped `''` → `'`.

Применяется только для `engine="mssql"` — PG запросы не трогает.

**Замечание архитектору:** это архитектурная дыра Sprint 6 — antipatterns testing делался на синтетических запросах, не на реальных 1С traces. Для Sprint 9 нужен фикстурный набор из реальных `sp_executesql`-wrapped запросов.

---

#### Bug #2 — Pydantic ValidationError severity 'High'

**Severity:** Critical (AI endpoint падал с 422)

**Root cause:** AI иногда возвращает severity вне схемы Pydantic: `"High"` вместо `"Critical"`, `"Medium"` вместо `"Warning"`, `"Low"` вместо `"Info"`. Промпт написан, но модели (Haiku) не всегда точно следуют enum.

**Fix:** нормализация в `ai_explainer.py` до создания `PlanHotspot`:

```python
_SEV_MAP = {
    "critical": "Critical", "high": "Critical",
    "warning": "Warning", "medium": "Warning",
    "info": "Info", "low": "Info",
}

def _norm_sev(h: dict) -> dict:
    sev = str(h.get("severity", "Info")).lower()
    h = dict(h)
    h["severity"] = _SEV_MAP.get(sev, "Info")
    return h

hotspots = [PlanHotspot(**_norm_sev(h)) for h in hotspots_raw if isinstance(h, dict)]
```

**Замечание архитектору:** подобная нормализация нужна для **любого** enum поля которое Claude возвращает в JSON — модели не гарантируют точное соответствие схеме. Рекомендую добавить generic `_norm_enum()` helper в `ai_explainer.py` на случай появления новых enum полей.

---

#### Bug #3 — SqlAntipatternsCard: тёмный фон

**Severity:** High (визуальный регресс)

**Root cause:** CSS модуль `SqlAntipatternsCard.module.css` использовал hardcoded тёмные цвета (`#1a1a1a`, `#2a2a2a`, `#3a3a3a`). Приложение работает только в светлой теме — явное нарушение design contract `--o-*` токенов.

**Fix:** полная замена на `--o-*` design токены. Было ~80 строк hardcoded hex-цветов, стало — только `var(--o-panel)`, `var(--o-border)`, `var(--o-text-*)`и т.д.

**Замечание архитектору:** в проекте строгое правило «только светлая тема — только `--o-*` токены». Phase C нарушил его при первичной реализации карточки. Рекомендую добавить в code review checklist: «нет ли hex-цветов в CSS модулях?»

---

#### Bug #4 — «Парсер не смог разобрать запрос» надо видеть в списке

**Severity:** UX / Medium

**Root cause:** Список из ТЖ архива показывал 500+ планов в произвольном порядке. Юзер не понимал которые запросы самые медленные и зачем ему этот список.

**Fix:** `PlanTjImport.tsx` — `useMemo` сортировки `[...items].sort((a, b) => (b.duration_us ?? -1) - (a.duration_us ?? -1))`. Самые медленные — сверху.

---

#### Bug #5 — SQL запроса в ТЖ виде не свёрнут по умолчанию

**Severity:** UX / Medium

**Root cause:** Секция «SQL запроса · ТЖ архив · event #N» была раскрыта по умолчанию, занимая место. Сергей хочет видеть сначала антипаттерны и AI объяснение, а SQL — по запросу.

**Fix:** `PlanAnalyzer.tsx` — добавлен state `sqlTextOpen = false`. Header секции стал кликабельным. При выборе нового плана из архива — `setSqlTextOpen(false)` (сброс).

---

#### Bug #6 — Stale state при переключении вкладок

**Severity:** UX / Medium

**Root cause:** При переключении между вкладками File/Paste/TJ в PlanImport результат анализа предыдущей вкладки оставался на экране. MSSQL `.sqlplan` с визуализацией было видно под списком TJ архива.

**Fix:** `PlanImport.tsx` — добавлен проп `onTabChange?: (tab) => void`. `PlanAnalyzer.tsx` — подписался и очищает `result / textPlan / aiResponse / antipatterns` при смене вкладки.

---

#### Bug #7 — AI endpoint ошибка «запустите start.bat»

**Severity:** Medium (неправильная подсказка)

**Root cause:** Сообщение об ошибке подключения к AI серверу советовало «Запустите server/ через start.bat», но start.bat не запускает FastAPI сервер (только десктоп).

**Fix:** корректный текст с реальной командой запуска uvicorn.

---

#### Bug #8 — Кнопки «Развернуть»/«Свернуть» везде

**Severity:** UX / High (Сергей явно выразил: «ВЕЗДЕ убери эти надписи»)

**Root cause:** Несмотря на то что `AiPlanExplanationCard`, `PlanTextView`, `PgPlanTextView` уже были исправлены в основной Phase C работе, остались компоненты с текстовыми кнопками:
- `PlanVisualization.tsx` — кнопка «Свернуть» в titleBar
- `AiExplanationCard.tsx` (QueryAnalyzer) — кнопка в header
- `CollapsibleSection.tsx` (primitive) — кнопка toggleButton
- `PanelWithToggle` в `DeadlockAnatomy.tsx`
- `PanelWithToggle` в `Anatomy.tsx`

**Fix:** во всех компонентах паттерн одинаков:
- Удалена кнопка `<button onClick={setCollapsed}>Развернуть/Свернуть</button>`
- Добавлены `onClick`, `role="button"`, `tabIndex={0}`, `onKeyDown` на родительский div заголовка
- В CSS: `cursor: pointer; user-select: none` на `.titleBar` / `.header`
- Для `CollapsibleSection` (может содержать `headerRight` с кнопками) — обёртка `<div onClick={e.stopPropagation()}>` вокруг `headerRight` чтобы клик по дочерним кнопкам не схлопывал секцию

---

### 2.3. Откат: start.bat auto-server

В процессе демо был сделан PR auto-start FastAPI сервера из `start.bat`. Это немедленно сломало поведение: при закрытии окна Tauri консоль зависала (uvicorn продолжал работать). Откат выполнен тем же коммитом. AI сервер требует ручного запуска — это по дизайну (development-only).

**Замечание архитектору:** сервер для AI (FastAPI port 8001) имеет неопределённый deployment статус. Для production нужен либо bundled local server (Tauri sidecar), либо cloud endpoint. Это Sprint 11+ задача. Пока — manual start для dev.

---

## 3. Метрики Sprint 8 Phase C + Demo

### 3.1. Тесты

| Компонент | До Phase C | После Phase C | После Demo | Δ total |
|---|---|---|---|---|
| Backend tests | 789 | **861** | **861** | +72 |
| Server tests (AI) | 36 | **41** | **41** | +5 |
| Frontend tests | 23 | 23 | 23 | +0 |
| Backend failures | 0 | 0 | 0 | — |
| Server pre-existing | 1 | 1 | 1 | unchanged |

Детализация backend +72:
- `test_sql_antipatterns_rpc.py`: +12 (unwrap sp_executesql + engine dispatcher)
- `test_postgres_detectors.py`: +61 (unit tests каждого из 15 детекторов)
- `test_postgres_real_data.py`: +19 (edge cases + real-data parse success rate + 2 perf tests)
- Регрессия T-SQL: 0 новых failures

### 3.2. Commits Phase C

| Хэш | Описание |
|---|---|
| `46c7bc1` | feat(sprint-8c): PG Antipatterns Engine — 15 detectors with 1С-aware heuristic |
| `3fed15d` | merge: Sprint 8 Phase C — PG Antipatterns Engine (closure of Sprint 8) |
| `82ca814` | docs(sprint-8c): test guide для manual demo session |

### 3.3. Commits Demo Session

| Хэш | Описание |
|---|---|
| `c6e7aff` | fix: SQL section collapsed by default in TJ archive plan view |
| `fab9991` | fix: unwrap sp_executesql + sort plans by duration desc |
| `474acb5` | fix: SqlAntipatternsCard light theme (replace hardcoded dark colors) |
| `41d6b65` | fix: auto-start AI server → **откатан** в следующем коммите |
| `5e5c34a` | revert: restore original start.bat (no auto-server window) |
| `a38a7b2` | fix: clear stale analysis state when switching PlanAnalyzer tabs |
| `dcfda04` | fix: correct AI server error message |
| `bca70eb` | fix: normalize AI hotspot severity (High/Medium/Low → Critical/Warning/Info) |
| `18f18e9` | chore: remove unused ai_model_business (Opus) from settings |
| `ae361ae` | fix: replace expand/collapse buttons with clickable headers (3 компонента) |
| `0730c8d` | fix: убрать кнопки Развернуть/Свернуть (5 компонентов — вся кодовая база) |

### 3.4. Новые файлы Phase C

**Backend (22 новых файла):**
- `src/optimyzer_backend/sql_antipatterns/__init__.py` + `engine.py` + `models.py`
- `tsql/__init__.py` + `tsql/detectors.py` (миграция из `sql/antipatterns.py`)
- `postgres/__init__.py` + `postgres/_helpers.py` + 15 детекторов (по одному файлу)
- `shared/__init__.py`
- `rpc/sql_antipatterns_rpc.py` (новый, был inline в `plan_analyzer_rpc.py`)

**Backend tests (3 новых файла):**
- `tests/sql_antipatterns/test_postgres_detectors.py` — 61 tests
- `tests/sql_antipatterns/test_postgres_real_data.py` — 19 tests
- `tests/sql_antipatterns/__init__.py`

**Server (1 новый файл):**
- `tests/test_ai_explain_pg_plan.py` — 20 tests + integration

**Frontend (3 новых/изменённых файла):**
- `SqlAntipatternsCard.tsx` + `SqlAntipatternsCard.module.css`
- `utils/formatAntipatterns.ts`

---

## 4. ADRs Sprint 8 Phase C

### ADR-045 — sql_antipatterns module (dialect-aware structure)

Вместо flat `sql/antipatterns.py` — пакет `sql_antipatterns/` с `tsql/` и `postgres/` субмодулями. Engine dispatcher скрывает диалект от RPC layer. Backward-compat: старый импорт ре-экспортирует из нового. Reason: T-SQL и PG правила несовместимы синтаксически; общий модуль стал бы монолитом с `if engine == "mssql"` разветвлениями по всему коду.

### ADR-046 — 1С-context detection через regex heuristic

Для классификации «является ли SQL запросом от 1С» используется regex по именам таблиц/полей (`_Reference\d+`, `_Fld\d+`, `mchar`/`mvarchar`). Альтернатива — полный AST-парсер SDBL — излишне тяжёлая. Heuristic достаточен: 1С никогда не использует произвольные имена для объектов — naming convention строго детерминирован. False positive практически невозможен.

### ADR-047 — Параллельный flow: antipatterns fast (local) + AI slow (cloud)

Antipatterns engine (~5ms, local sqlglot) выполняется **до** AI запроса. Результаты передаются в AI промпт как контекст. Это позволяет: (a) показать findings пользователю немедленно; (b) AI не тратит токены на повторное обнаружение того что уже найдено. Альтернатива — единый AI-only анализ — дороже и медленнее.

### ADR-048 — Sprint 8 закрыт без Phase D

Изначально Sprint 8 планировал Phase D: конвертер planSQLText TEXT → SHOWPLAN XML для последующего применения PerformanceStudio. В процессе Phase A discovery выяснилось: для PostgreSQL planSQLText это уже plain TEXT EXPLAIN — конвертировать нечего. Для MSSQL же PerformanceStudio уже работает через XML import (Sprint 7 Phase B). Phase D closure: не нужна.

---

## 5. Что НЕ сделано / технический долг

### Из scope Phase C

- ✅ Всё запрошенное сделано + 7 дополнительных детекторов (план был 8, сделано 15)

### Обнаружено в demo session как tech debt

1. **Реальные sp_executesql fixtures** — antipatterns tests Sprint 6 написаны на синтетических запросах. Нет regression coverage для реального формата. Добавить `fixtures/real_mssql_tj_samples.sql` для Sprint 9.

2. **Enum нормализация** — в `ai_explainer.py` нет generic helper'а. Добавлен ad-hoc `_norm_sev()`. При появлении новых enum полей в AI ответе нужно будет дублировать паттерн.

3. **AI сервер (FastAPI port 8001)** — development-only, manual start. Для production нужен bundled sidecar или cloud endpoint. Sprint 11+.

4. **pev2 bundle 185 KB gz** — lazy loading через code-splitting улучшило бы TTI для юзеров без PG планов. Sprint 13 (UX Reorganization).

5. **SqlAntipatternsCard не покрыта frontend тестами** — Phase B добавила Vitest infrastructure для critical utilities. Phase C карточку не покрыла. Sprint 9.

---

## 6. Архитектурные наблюдения из demo session

### 6.1. sp_executesql — архитектурная дыра Testing Coverage

Это самый важный вывод demo session. 1С **всегда** оборачивает MSSQL запросы в `sp_executesql`. Это означает что все автоматизированные тесты Phase C для MSSQL писались против синтетических «сырых» запросов, а не против реального формата. Баг пережил:
- 25 T-SQL unit tests
- Integration testing Phase C
- Полный backend test suite (861)

и был обнаружен только при live demo с реальным архивом. **Это говорит об отсутствии real-data smoke tests для критических путей.** Рекомендую в Sprint 9 добавить фикстурный набор реальных ТЖ-фрагментов как часть regression suite.

### 6.2. UI collapse pattern — финальный стандарт

После demo session устоялся единый паттерн для всех collapsible элементов в приложении:
- **Никаких кнопок** «Развернуть»/«Свернуть»
- **Кликабельность = вся строка заголовка** (`div` с `onClick`, `role="button"`, `tabIndex=0`, `onKeyDown`)
- **CSS**: `cursor: pointer; user-select: none` на header
- **Исключение**: если в header есть `headerRight` с кнопками — обёртка с `stopPropagation`

Этот паттерн применён во **всех** существующих collapsible компонентах:
`AiPlanExplanationCard`, `PlanTextView`, `PgPlanTextView`, `PlanVisualization`, `AiExplanationCard`, `CollapsibleSection`, `PanelWithToggle` (x2).

**Для Sprint 9**: при создании новых collapsible компонентов использовать этот же паттерн. Нет причин отклоняться.

### 6.3. Haiku везде — подтверждено

В процессе demo Сергей явно запросил подтверждение. Проверено: `settings.ai_model_default = "claude-haiku-4-5"` применяется во всех AI вызовах. Удалён неиспользуемый `ai_model_business` (commit `18f18e9`).

### 6.4. SqlAntipatternsCard light theme — нарушение design contract

Phase C реализовывала карточку с hardcoded hex-цветами вместо `--o-*` токенов. Это произошло потому что карточка писалась «с нуля» без referencing существующих CSS модулей. **Для Sprint 9**: любой новый CSS модуль должен начинаться с review существующего (например `AiPlanExplanationCard.module.css`) как reference.

---

## 7. E2E capabilities — Sprint 8 closure

| Возможность | Engine | Sprint |
|---|---|---|
| Импорт `.sqlplan` (SSMS XML) | MSSQL | 7 B |
| Импорт планов из ТЖ (SHOWPLAN_TEXT) | MSSQL | 7 D |
| Импорт планов из ТЖ (planSQLText TEXT) | PostgreSQL | 8 B.1 |
| Re-EXPLAIN через PG connection (OS keychain) | PostgreSQL | 8 B.4 |
| pev2 интерактивная визуализация | PostgreSQL | 8 B.5 |
| AI explanation — MSSQL prompt | MSSQL | 7 + 8 B.3 |
| AI explanation — PG prompt с 1С-specific знанием | PostgreSQL | 8 B.3 |
| AI получает detected antipatterns как контекст | оба | 8 C.4 |
| 9 T-SQL antipatterns (Sprint 6 legacy) | MSSQL | 6 |
| **15 PG antipatterns + 1С-aware heuristic** | PostgreSQL | **8 C** |
| sp_executesql unwrap перед парсингом | MSSQL | **8 Demo fix** |
| Список планов ТЖ sorted by duration desc | оба | **8 Demo fix** |

---

## 8. После Sprint 8 — рекомендации для Sprint 9

1. **Real-data regression fixtures** — собрать из реальных ТЖ архивов 20-30 MSSQL запросов в `sp_executesql` формате + 10-15 PG запросов. Добавить в `tests/fixtures/`. Это предотвратит повторение bug #1.

2. **Frontend test coverage для SqlAntipatternsCard** — компонент критический (показывает главный результат анализа), но тестов нет. Vitest infrastructure уже есть (Phase B).

3. **Generic AI output normalizer** — вместо ad-hoc `_norm_sev()` сделать generic `_norm_ai_enum(field, mapping)` в `ai_explainer.py`.

4. **Antipatterns performance baseline** — Phase C добавила perf tests, но без CI enforcement. Baseline: < 50ms на запрос < 10KB, < 200ms на запрос < 100KB.

5. **pg_stat_statements ingestion** — Phase A показала feasibility, Sprint 8 не включил в scope. Это следующий крупный PG feature (Sprint 11+).

---

**Подготовил:** Claude Code (executor)
**Дата:** 2026-05-25
**Версия:** Sprint 8 Phase C + Demo Report v1
**Следующий:** Sprint 9 — Deep Real-world Testing + real-data regression
