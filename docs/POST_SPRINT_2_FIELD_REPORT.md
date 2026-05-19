# Post-Sprint 2 Field Report — Bug Fixes, Current State, Product Direction Question

> **Audience:** Claude Opus (architect)
> **Status:** Sprint 2 closed (tag `v0.2.0-internal`, см. SPRINT_2_REPORT.md). Этот документ — что произошло после демо у Сергея и какие открытые вопросы.
> **Дата:** 2026-05-19
> **Branch:** main (все патчи запушены)

---

## 1. TL;DR

После закрытия Sprint 2 Сергей запустил `start.bat`, попробовал реальные сценарии и нашёл серию production-критичных багов и UX-проблем. Все они закрыты в 7 коммитах за один день; реальные сценарии работают. Параллельно Сергей **поднял продуктовый вопрос**, на который Sprint 2 не отвечает и который нужно адресовать перед Sprint 3:

> «Как и чем это поможет, если ERP просто тормозит, и некоторые документы долго проводятся или отчёты формируются, или взаимоблокировки всё время? Может быть, часть функциональности приблизить к сервисам Гилева или к 1С:ЦУП?»

Это центральный вопрос раздела 4. Bugfixes ниже — приготовление почвы; продуктовое решение — отдельный приоритет.

---

## 2. Post-Sprint 2 patches (что было сломано / упущено)

Все коммиты на `main`, conventional commits, atomic. От старого к новому:

### 2.1 UI layout — outer scrollbar / StatusBar обрезался

**Симптом**: при maximize-окне у Сергея появлялся вертикальный скролл, подвал (StatusBar) уезжал под viewport.

**4 часа гадания, восемь промежуточных коммитов** (включая ошибочные направления: hardcoded window size — Сергей правильно отверг, "это должно работать на любых экранах"). Корень нашёлся **только** когда я поставил Playwright и измерил эмпирически.

**Root cause**: CSS Grid quirk. `.app { grid-template-rows: 48px 1fr 28px; height: 100vh }` — `1fr` track растёт по `min-content` грид-айтемов даже при `min-height: 0` на айтеме. Внутри `.app__main` сидит `.screen` с `min-height: calc(100vh - 76px)`, плюс CodeMirror editor — общая высота превышала viewport на 28px, StatusBar уезжал под край.

**Fix** ([4375aa7](../1c-optimyzer)): canonical `grid-template-rows: var(--o-topbar-h) minmax(0, 1fr) var(--o-statusbar-h)`. Плюс `min-height: 0; min-width: 0` на `.workarea`, `.editor_pane`, `.results_pane` чтобы nested flex/grid тоже respected allocated sizes.

**Verified empirically** через `frontend/layout-probe.mjs` (оставлен в репо для будущей диагностики). При 680/720/900/1080/1440 vp — main = grid 1fr точно, StatusBar inView, `bodyScrollH == viewport`.

**Урок для будущих сессий**: для UI-багов с layout — Playwright headless с 30 секунд до первой цифры; гадание по скриншотам Сергея = часы потерь.

### 2.2 Connection Error после ingestion — все запросы ломались ([551e5da](../1c-optimyzer))

**Симптом**: после загрузки архива SQL Console и все six views падали с:
```
Connection Error: Can't open a connection to same database file
with a different configuration than existing connections
```

Status bar при этом показывал «1.1 млн событий · 535.5 МБ» — то есть ingestion прошёл успешно, БД жива, но запросы не работали.

**Root cause**: `DuckDBStore.open()` создаёт connection в **read_write** (для `query_events_preset` и `get_storage_stats`) и держит его живым в `state["store"]`. `SQLExecutor` / `schema_introspection` пытались открыть тот же файл в **read_only** → DuckDB не позволяет разные configurations для одного файла в одном процессе.

**Fix**: registry активных connections в `duckdb_store.py`:
- `register_active_connection(archive_id, conn)` при `open()`
- `unregister_active_connection(archive_id)` при `close()`
- `get_active_connection(archive_id) -> conn | None`

`SQLExecutor._connect()` и `get_schema()` теперь:
- Если есть active connection → `conn.cursor()` (child connection того же parent, без config mismatch)
- Иначе → fallback к собственному read_only open (для тестов и cold archives)

Cursor закрывается owned-flag'ом, parent остаётся живым.

**Coverage**: 207 → 209 backend tests (добавлен smoke test full production flow).

### 2.3 Reattach stored archive — никогда не было ([bc0e882](../1c-optimyzer))

**Симптом**: Сергей видел архивы в выпадающем меню («ЗАГРУЖЕННЫЕ АРХИВЫ»), но клик по ним ничего не делал. После каждого перезапуска приложения нужно было **перепарсивать ту же папку с логами 11 ГБ** — на нашем основном use case это минуты на холодной машине.

**Архитектурная дыра Sprint 1/2**: SQLite `recent_archives` хранил metadata + .duckdb на диске, но не было RPC reattach. UI всегда `setArchive` только после новой ingestion.

**Fix**: новый RPC `open_stored_archive(archive_id)`:
- Находит запись в SQLite, проверяет наличие `.duckdb` на диске
- Открывает `DuckDBStore` (он саморегистрируется в active connections registry)
- Заполняет `_ARCHIVES[archive_id]` со `status='ready'`, `progress=1.0`
- Idempotent

Frontend: `ArchivesMenu` item теперь кликабельный (button `.item_main_btn` рядом с крестиком). Orphan-архивы (без `.duckdb`) disabled. После reattach данные доступны моментально.

**Coverage**: 209 → 211 backend tests.

### 2.4 SQL Console UX — 4 проблемы за один присест ([4992a86](../1c-optimyzer))

Сергей попробовал SQL Console на реальных логах и сразу нашёл:

**(a) Подсказки колонок не работали без префикса.** `SELECT pr<cursor>` — никакого `process_role` в autocomplete. CodeMirror @codemirror/lang-sql требует знать, из какой таблицы достать колонки.

**Fix**: `defaultTable: "events"` в `makeSqlExtension`. Теперь `Ctrl+Space` (и сам по себе) предлагает `process_role`, `process_pid`, `duration_us` etc.

**(b) Нет способа узнать структуру таблицы.** Сергей: «как я смогу узнать, какие вообще поля можно выбирать?»

**Fix**: новый `SchemaPanel.tsx` — кнопка «СХЕМА · N колонок» рядом с шаблонами. Popover показывает все таблицы и колонки с типами; клик по колонке вставляет имя в editor через `EditorHandle.insertAtCursor` (forwardRef + useImperativeHandle).

**(c) Комментарии `//` не работали.** Сергей написал `//ts,` ожидая комментарий — получил Parser Error.

**Fix**: explicit `Ctrl+/` keymap → `toggleLineComment` из `@codemirror/commands`. CodeMirror знает SQL commentTokens, ставит `--` (это и есть SQL-стандарт; `//` — JS-стиль, неприменимо к DuckDB).

**(d) Граница между editor и results не двигалась.** Фиксированное `grid-template-columns: 1fr 1fr` — нельзя дать таблице больше места при длинных строках.

**Fix**: draggable splitter (6px). Ширина editor pane в процентах [18..82], сохраняется в `localStorage:optimyzer:sql:editor_pct`. Double-click → reset to 50/50. Workarea — grid с inline `gridTemplateColumns`. CodeMirror и таблица сами перерисовываются (ResizeObserver).

### 2.5 ErrorsFeed UI + text contrast + real cancel ([015ce16](../1c-optimyzer))

Три бага в одной серии:

**(a) Слишком агрессивный truncate + native title tooltip.** ErrorsFeed обрезал `context` до 60 символов JS-функцией; полный текст показывался native browser tooltip (тот «уродский системный» — серый системный, мелкий шрифт).

**Fix**: убран JS truncate; CSS `text-overflow: ellipsis` по ширине колонки (адаптивно). Клик на строку **раскрывает** под ней `<pre>` с полным контекстом в codebox-стиле (моноширинный, переносы длинных строк). Toggle через `Set<rowIndex>`.

**(b) Шрифты бледные везде.** `--o-text-2: #525252`, `--o-text-3: #a3a3a3` — meta-строки таблиц/subtitle'ы выглядели как water-marks.

**Fix**: `--o-text-2: #2f2f2f`, `--o-text-3: #5a5a5a`. Глобально, везде где CSS variables используются — стало плотнее.

**(c) Cancel ingestion был stub.** В Sprint 1/2 RPC возвращал `{ok:false, reason:"not_implemented_until_sprint_2"}`. На 11 ГБ это критично: если понимаешь что не та папка — нужно пять минут ждать или kill-таскать процесс.

**Fix**: cooperative cancel через `threading.Event` в `state["cancel_event"]`. `_run_ingestion` проверяет между файлами + каждые 5000 событий внутри файла. Срабатывание → `_IngestionCancelled` → `status='cancelled'`, `store.close()`, `DuckDBStore.delete_db_file()`, progress event `'cancelled'`. **Никакого partial .duckdb на диске.**

Frontend: кнопка «Отменить» в `ProgressCard` теперь активна (была всегда disabled с tooltip "Доступно в Sprint 2"). `window.confirm` перед отправкой. `ProgressPhase` расширен `'cancelled'`. `App.tsx` при `phase=='cancelled'` делает `setArchive(null)`.

**Coverage**: 210 backend tests. Cancel test реально стопит running ingestion на 200 файлах × 50 событий, проверяет что .duckdb удалён.

### 2.6 Итоговая статистика этих патчей

| Метрика | До | После |
|---|---|---|
| backend tests | 183 + 15 env | 210 + 15 env |
| frontend modules | 815 | 817 |
| commits на main | + Sprint 2 closed | + 7 hotfix commits |
| Регрессий | — | 0 (все 210 tests passed после каждого коммита) |

---

## 3. Полный обзор текущей функциональности (state of the product)

Что **в продукте сейчас**, не дублируя SPRINT_2_REPORT.md, а с фокусом на «что пользователь видит и может делать».

### 3.1 Ingestion

- **Источник**: папка с TJ (рекурсивный обход) — основной use case; .zip как legacy entrypoint.
- **Парсинг**: streaming, формат `mm:ss.usec-dur_us,EventType,level,key=value,...` с balanced quotes для multi-line значений. 13 known event types (CALL, SCALL, DBMSSQL, EXCP, TLOCK, TDEADLOCK, CONN, SDBL, MEM, LEAKS, ATTN, QERR, неизвестные). process_role/process_pid из имени родительской папки (`rphost_28220`).
- **Хранилище**: DuckDB per archive в `%APPDATA%/1c-optimyzer/duckdb/<archive_id>.duckdb`. Single `events` table с 19 колонками + 7 индексов.
- **Метаданные**: SQLite `metadata.sqlite` — `recent_archives` (для reattach), `saved_queries`, `settings`.
- **Progress**: push notifications в UI (discovering / parsing / indexing / done / error / cancelled), throttled 250ms.
- **Cancel**: cooperative, graceful, удаление partial .duckdb (новое после Sprint 2).
- **Reattach**: клик по архиву в выпадающем меню моментально подключает .duckdb из истории (новое после Sprint 2).
- **Delete**: на отдельный архив (× кнопка) и «Очистить всё» в footer dropdown'а.

### 3.2 SQL Engine

- **Validator** (ADR-019 layer 1): regex после strip strings/comments; allow SELECT + WITH only; block 22 DDL/DML/admin keywords; reject multi-statement.
- **Executor** (ADR-019 layer 2): cursor от живого read_write store **или** fallback read_only open. Per-query connection (через cursor). Statement timeout 30s, row limit 10k, truncation flag.
- **Schema introspection**: returns `{table: [{name, type}]}` для autocomplete/docs.
- **CodeMirror editor**: DuckDB-flavoured dialect, schema-based autocomplete (с `defaultTable: events`), `Ctrl+/` toggle comment, `Ctrl+Enter` run.
- **Templates library**: 13 шаблонов по категориям (performance / locks / errors / memory / stats), все проходят validator.
- **Saved queries**: localStorage + SQLite mirror.

### 3.3 Pre-built views (6 экранов)

| View | Что считает | Filters работают |
|---|---|---|
| Slow Queries | top DBMSSQL agg by sql_text_hash, sortable by total/avg/max/count | ✅ |
| Locks Timeline | TLOCK / TDEADLOCK по auto-bucket (minute/hour/day) | ✅ |
| Process Roles | DonutChart + per-role metrics; **click slice → filter by role** | ✅ |
| Duration Histogram | 7 buckets <1ms..>60s, log-Y, percent | ✅ |
| Errors Feed | EXCP/TDEADLOCK/TLOCK feed; expand-on-click (новое) | ✅ + type-select |
| Activity Heatmap | 7×24 day×hour; metric switchable; **click cell → filter time range** | ✅ |

Все 6 views отрабатывают <3s на 1.09M events archive.

### 3.4 Cross-filtering (Phase E, ADR-017)

`CrossFilters` в Zustand: `time_from`, `time_to`, `process_role`, `event_type`, `source_view`. Постоянная `FilterBar` сверху каждого view с active chips и click-to-remove. Process Roles donut и Activity Heatmap имеют **click-to-filter** drill-down.

### 3.5 Multi-archive comparison (Phase G, ADR-018)

- `compare_summary` — 6 high-level metrics с delta% и delta_abs
- `compare_slow_queries` — partition by sql_text_hash на `in_both / only_a / only_b / regressed (≥+50% avg) / improved (≤-30% avg)`
- UI: two pickers (orphans отфильтрованы, same-on-both prevented), Tabs Summary/Slow Queries, color-coded deltas

### 3.6 Export

CSV / TSV / JSON через Tauri save dialog. Все 6 views + Errors Feed (с filter applied) + Heatmap (с metric). CSV cells quoted при наличии sep/quote/newline. XLSX — deferred (открытие CSV в Excel покрывает).

### 3.7 UX-уровень

- Sidebar: SQL Console + 6 views + comparison enabled; disabled с tooltip «Доступно в будущих обновлениях» для остальных.
- Keyboard shortcuts: `Ctrl/Cmd + 1..8` quick switch.
- Drag-and-drop: DropZone overlay на drop папки.
- Progress card: animated counters, явная cancel-кнопка с confirm.
- Empty/loading/error states стандартизованы через `ChartShell` + `useView` hook.
- Resizable splitter в SQL Console с localStorage persistence.

---

## 4. Открытый вопрос Сергея — direction question

Сергей сформулировал то, что в Sprint 2 plan не обсуждалось:

> «Сейчас я не очень понимаю, как и чем мне это поможет, если ERP просто тормозит, и некоторые документы долго проводятся или отчёты формируются, или взаимоблокировки все время. Может быть, часть функциональности приблизить к сервисам Гилева или к 1С:ЦУП?»

Это валидное беспокойство владельца продукта, и ответ на него определяет Sprint 3.

### 4.1 Чем мы НЕ являемся (relative to ecosystem)

**Гилев** (gilev.ru / Test1C / APDEX):
- APDEX-style оценка пользовательского опыта по бизнес-операциям
- Тренды по дням/неделям, регламентные отчёты для управления
- Методологии (book + courses) — позиционирование как «измерение качества обслуживания»

**1С:ЦУП** (Центр Управления Производительностью):
- Continuous monitoring с push'ами и алертами
- Привязка SQL/блокировок к конкретным **сценариям** (документ X, отчёт Y)
- Регламентные отчёты с распределением времени на: пользователь, документ, операция, СУБД vs сервер 1С
- Корпоративный продукт (тысячи руб./мес), интегрируется в инфраструктуру

**Мы сейчас**:
- Post-mortem forensics над уже собранным TJ архивом (cold investigation)
- SQL-первый интерфейс — для тех, кто понимает структуру TJ событий
- Local desktop tool, не сервис, не платформа

### 4.2 Реальные сценарии Сергея → как мы их закрываем сейчас

Сергей дал три типичных юзкейса:

**(A) «ERP просто тормозит»** — широкая жалоба. Куда смотреть?

| Сейчас можем | Чего не хватает |
|---|---|
| Activity Heatmap покажет когда нагрузка пиковая | Не показывает **что** тормозит, только volume of events |
| Process Roles → видно перекос на rphost/rphost64 | Не разнесено по бизнес-операциям |
| Duration Histogram — % событий в каждом bucket'е | Не группировка по «что это было» |
| Slow Queries — топ SQL по total time | Это только SQL; CALL/SCALL contexts не суммируются |

**Чего реально нужно**: «Top slow user-facing operations» — group by clean `context` (CALL/SCALL where context is set), показать `SUM(total_call_duration)` с children SQL.

**(B) «Документ долго проводится»** — drill-down вопрос: какой именно документ, какие SQL.

| Сейчас можем | Чего не хватает |
|---|---|
| FTS-like через SQL: `WHERE context LIKE '%StandardDocumentsPosting%'` | Не интерактивно; нужно знать имя документа в TJ |
| Slow Queries покажет тяжёлые SQL | Не привязаны к конкретному документу/transaction |
| Errors Feed покажет EXCP если документ упал | Не корреляция «вокруг этой EXCP было X событий» |

**Чего реально нужно**: «Document anatomy» view — выбираешь documenttype/operation, видишь timeline всех событий с `process_pid + session_id` группировкой, distribution по event_type, top SQL внутри.

**(C) «Взаимоблокировки всё время»** — это уже близко к нашему Locks Timeline.

| Сейчас можем | Чего не хватает |
|---|---|
| Locks Timeline — distribution по time buckets | Не показывает **кто vs кто** |
| Errors Feed → TDEADLOCK раскрыть → context (новое) | Не graph «таблица A ↔ таблица B» |
| Можно SQL'ом написать `SELECT extra FROM events WHERE event_type='TDEADLOCK'` | Нет интерактивной деконструкции lock chains |

**Чего реально нужно**: «Deadlock anatomy» — для каждого TDEADLOCK показать ±N секунд событий вокруг, выделить участвующие process_pid, lock resources из `extra` JSON.

### 4.3 Что у нас УЖЕ есть как сырьё

Это критично: технологический журнал — это **очень богатый источник**, мы пока используем малую часть.

**Поля events table** (всё уже парсится и хранится):
- `ts`, `event_type`, `process_role`, `process_pid`, `session_id`, `user_name`
- `context` — **строка с указанием формы/модуля/процедуры** (вот тут бизнес-смысл!)
- `process` — `rphost-28220` идентификатор
- `duration_us` — длительность
- `sql_text`, `sql_text_normalized`, `sql_text_hash` — только для DBMSSQL
- `rows_read`, `rows_modified`
- `extra` (JSON) — всё остальное: OSThread, lock granules, error texts, etc.
- `source_file`, `source_line_start`

**Что отсюда можно извлечь без новой схемы**:
1. Бизнес-операции — regex `^(\w+)\.(\w+)\.(Форма|Модуль|МодульМенеджера)` по `context` → выделяет имя документа/обработки/отчёта.
2. Call chains — `process_pid + session_id + ts window` группирует events одной user action.
3. SQL → context binding — DBMSSQL событий обычно нет своего context, но рядом по времени есть CALL/SCALL с context — можно матчить.
4. Lock resources — `extra.Locks` или `extra.Granules` содержит таблицы/индексы (DuckDB JSON extract).

**Чего НЕТ в TJ**:
- Wall-clock duration «user видит» — TJ не пишет client RTT
- Memory peaks по операциям — есть `MEM` events но они per-process, не per-action
- CPU per-action — нет
- Connection pool stats — нет

### 4.4 Возможные направления (что предлагаю обсудить)

**Direction A — Stay analytics-first, deepen correlation**
Цель: оставаться offline forensics tool, но усилить связки event_type'ов и добавить «бизнес-операционный layer» поверх существующей схемы.

Что добавить:
- **Top business operations** view — group by стрипанному `context`, where event_type in `('CALL', 'SCALL')` AND `context IS NOT NULL`, top by `SUM(duration_us)`. Дополнительно показывает «inner SQL» для каждой операции (DBMSSQL events within same `process_pid` ± 1 sec).
- **Document anatomy** drill-down — выбор операции → timeline + breakdown SQL/locks/exceptions.
- **Deadlock anatomy** view — для каждого TDEADLOCK выводит lock graph из `extra` + участников ± N секунд.
- **Lock heatmap** — group by `extra.Locks` resource name × hour.

Pro: использует уже собранные данные, не требует архитектурных перемен, добавляет огромную бизнес-ценность.
Con: остаёмся cold forensics — не закрываем «realtime monitoring» need.

**Direction B — APDEX / SLA layer (приблизиться к Гилеву)**
Цель: давать управленческие отчёты «качество обслуживания», а не только разработческие.

Что добавить:
- Группировка operations с пользовательскими тегами (SAT/T/F пороги Apdex)
- Per-user / per-operation trend tables — day-over-day deltas
- «Health score» dashboard с APDEX-like single number
- Export PDF/email weekly reports

Pro: новая аудитория — менеджеры производительности 1С, а не только техлиды.
Con: нужна персистенция baselines, тренды требуют **много** архивов (>30 days), сейчас single-archive workflow.

**Direction C — Continuous monitoring (приблизиться к ЦУП)**
Цель: live-tail TJ, push alerts, dashboards.

Что добавить:
- File watcher на `logCfg.xml`-расположение, incremental ingest
- Threshold engine: «если deadlocks > N/час → alert»
- Email/Telegram delivery
- Long-term archive (rolling window 30/90 days)

Pro: рынок другой (DevOps/SRE для 1С), но и техническая сложность другая.
Con: требует daemon-режима / service install, далеко от текущего "desktop tool" позиционирования.

**Direction D — Hybrid: Direction A + selected pieces of B**
Цель: оставаться local forensics tool, но добавить минимальную persistence для trend/Apdex.

Что:
- Direction A в полном объёме
- Multi-archive comparison расширить до N архивов (не только 2) → tracks trends
- Persistent operation taxonomy: пользователь помечает операции (документ X, отчёт Y), сохраняется в SQLite, переиспользуется между архивами
- Simple Apdex view с настраиваемыми T-thresholds per operation

Pro: realistic для одного человека-разработчика без облачной infra.
Con: B-features нужны, но мы их не делаем «во всю».

### 4.5 Прагматичный приоритет (моя рекомендация)

Перед Sprint 3 — **обязательно** Direction A (3 новые views на сырых данных, без архитектурных изменений). Это превращает продукт из «SQL-консоль к TJ» в реальный investigation tool.

```
P0 (Direction A, ~1-2 недели):
  ✓ Top Business Operations view
  ✓ Document/Operation Anatomy drill-down
  ✓ Deadlock Anatomy view

P1 (если есть запас, ~1 неделя):
  ✓ Lock Heatmap by resource
  ✓ N-archive trend (N>2 в comparison)

P2 (Direction D, Sprint 4+):
  ✓ Operation taxonomy persistence
  ✓ Apdex-like view
```

Direction C (continuous monitoring) — отдельная дискуссия, скорее всего отдельный продукт / Pro tier.

---

## 5. Вопросы для архитектора (нужны решения)

**Q1.** Согласен с приоритетом Direction A? Или другое направление (B/C/D) ближе к видению продукта?

**Q2.** «Top Business Operations» — какой regex/heuristic для нормализации `context` правильнее?
Примеры из TJ:
- `ВнешняяОбработка.StandardDocumentsPosting.Форма.MainForm.Форма : 546 : Result = DoPortionPostAtServer(...)`
- `Документ.РеализацияТоваровУслуг.МодульОбъекта : 123 : ...`
- `Отчёт.ОборотноСальдоваяВедомость.МодульМенеджера : ...`

Стандартизуем до `Тип.Имя.Сущность` (отбрасывая `: line : statement`)?

**Q3.** Document/Operation Anatomy drill-down — какой UX лучше?
- (a) Modal dialog поверх Slow Queries (1 click → детали)
- (b) Отдельный экран `/anatomy/<event_id>` (URL-friendly, shareable)
- (c) Slide-in drawer справа (deferred в Sprint 2 — пора?)

**Q4.** Deadlock anatomy — что доставать из `extra` JSON? Сейчас json_extract работает, но мы не знаем какие именно поля 1С пишет для разных версий платформы (8.3.20+ vs 8.3.24). Нужна разведка `extra` schema по реальным архивам Сергея — это можно сделать на новой сессии как «field study».

**Q5.** Multi-archive expansion (N>2 для trends) — нужны или Direction D подождёт? Текущее ограничение «два slot'а» — UX choice, не технический. Зависит от того, насколько Direction B приоритетен.

**Q6.** Marketing/positioning question (вне технического scope, но важно): нужно решить, как мы себя называем относительно Гилева/ЦУП. Я бы предложил:
- НЕ конкурировать с ЦУП на enterprise рынке (другой класс)
- НЕ конкурировать с Гилевым на методологическом фронте (он экосистема + книги + курсы)
- Позиционирование: **«investigation workbench для разработчика/админа 1С — открой папку TJ, найди источник торможения за минуты»**. Local-first, fast, free or freemium, SQL под капотом для power users.

**Q7.** Demo recording (DoD #25 Sprint 2) — Сергей пока не записал. После Direction A фичей recording будет существенно более убедительным. Откладываем до P0 close или сейчас?

---

## 6. Что я ещё не знаю (information gaps)

- Реальная schema `extra` JSON в production TJ архивах Сергея (нужно посмотреть)
- Распределение event_types в его архиве 11 ГБ (% DBMSSQL / CALL / TLOCK / EXCP)
- Какие документы / операции Сергей в реальности расследует (можно собрать примеры)
- Performance budgets новых views на 11+ GB архивах (нужен env-gated test pass)

---

**Подготовил:** Claude Code (в Cursor / Tauri-app workflow с Сергеем)
**Для:** Claude Opus 4.7 (архитектор)
**Связанные документы:** SPRINT_2_REPORT.md, DECISIONS.md (ADR-015..019), PROMPT_AUTHORING_STANDARD.md
