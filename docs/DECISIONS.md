# Architectural Decisions (ADR) — 1C-Optimyzer

> Все принципиальные архитектурные решения проекта.
> Формат: ADR-N — заголовок · status · context · decision · consequences.

---

## ADR-001 — Технологический стек (Tauri 2 + React/TS + Python sidecar)

**Status:** Accepted (Sprint 0)

**Context.** Module 1 — desktop-приложение для Windows, потом Linux/macOS. Требования: offline-only, нулевые зависимости у пользователя, премиальный UI, парсинг ТЖ + DSL-исполнение, embedded analytical DB. У владельца есть опыт работы с Tauri/React/Python на Konvey.

**Decision.** Frontend — Tauri 2 + React 18 + TypeScript + Vite + CSS Modules + Zustand. Backend — Python 3.11+ sidecar (PyInstaller single-file exe в production, dev-mode через `python -m optimyzer_backend`). Связь — JSON-RPC 2.0 over stdio, проксируется через Rust shell (`tauri::command rpc_call` → child process). DB — DuckDB embedded для парсенных событий, SQLite для app metadata.

**Consequences.** + Тот же стек, что у Konvey — нулевой обучающий cost. + Tauri даёт MSI с минимальным размером и быстрым стартом. + Python sidecar — pydantic + duckdb уже зрелые библиотеки. − PyInstaller single-file exe начнёт работать с задержкой (cold start ~1–2s), но Sprint 0 это допустимо. − Связь через stdio удобна, но не годится для streaming чанков >1 МБ; для Module 1 не нужно.

---

## ADR-002 — CSS Modules вместо Tailwind для production app

**Status:** Accepted (Sprint 0)

**Context.** Дизайн-концепт в `design/opt/*.jsx` использует Tailwind через CDN — это нормально для preview, но в production это означало бы дополнительный bundle и runtime overhead.

**Decision.** Production-app использует CSS Modules + один глобальный файл с design tokens (`styles/optimyzer-design.css`). Все стили — через `*.module.css` файлы рядом с компонентами. Inline `style={{...}}` запрещён.

**Consequences.** + Чёткое разделение токенов и компонентных стилей. + Никакого runtime overhead. − Требует больше boilerplate vs Tailwind (нужно писать `styles.btn` вместо `className="h-7 px-2 ..."`). Приемлемо.

---

## ADR-003 — DuckDB per-archive, SQLite для metadata

**Status:** Accepted (Sprint 0)

**Context.** Одно приложение может загружать разные архивы ТЖ. События каждого архива нужно изолировать (чтобы запросы не пересекались), но также нужно хранить app-уровень metadata (recent archives, settings).

**Decision.** Один DuckDB-файл на архив в `%APPDATA%\1c-optimyzer\duckdb\<archive_id>.duckdb` (создаётся при `load_archive`, удаляется по `unload_archive`). Один SQLite-файл `metadata.sqlite` для recent_archives и settings.

**Consequences.** + Каждый архив самодостаточен; можно перенести/удалить отдельно. + DuckDB native analytical engine — Sprint 1 OQL → SQL компилируется тривиально. − Размер на диске = сумма всех загруженных архивов; нужен UI для cleanup в Sprint 2.

---

## ADR-004 — App grid 1280px min-width, светлая тема primary

**Status:** Accepted (Sprint 0)

**Context.** Дизайн заточен на 1С:Экспертов работающих на desktop с мониторами 1440+px. Тёмная тема в дизайне не реализована.

**Decision.** Минимальная ширина окна — 1280px (`min-width: 1280px` в `.app`, `minWidth: 1280` в `tauri.conf.json`). Светлая тема primary; тёмная отложена на Module 2+.

**Consequences.** + Не тратим Sprint 0 на theming. − Не поддерживаются ноутбуки с экраном 1024px. Приемлемо для целевой аудитории.

---

## ADR-005 — Modular release strategy (Module 1 → 2+)

**Status:** Accepted (Sprint 0, рекапитуляция стратегического решения)

**Context.** Видение продукта — APM-стек из 18+ экранов. Big-bang релиз — несколько кварталов работы без validation; пользователь может не получить никакой ценности до самого конца.

**Decision.** Последовательный modular release. Module 1 = OptimyzerQL Standalone Tool (анализ архивов ТЖ через DSL) — самостоятельный продукт. Module 2+ — real-time agents, central server, live monitoring, AI Co-pilot — добавляются после validation Module 1. В UI Sidebar все 18 экранов уже видны, но отключены до соответствующих модулей (с tooltip "Module N").

**Consequences.** + Максимальная скорость до launch (Module 1 ≈ 3–5 спринтов). + Каждый Module даёт ценность сам по себе. + Пользователь видит roadmap при первом запуске. − Требует дисциплины НЕ скатываться в фичи следующего модуля. Sprint 0 это явно фиксирует в коде (см. `frontend/src/components/chrome/nav.ts`).

---

## ADR-006 — TJ-парсер: lexer на regex, multi-line через look-ahead

**Status:** Accepted (Sprint 0)

**Context.** ТЖ — текстовый формат с переменными по содержимому событиями. Каждое событие — одна или несколько строк; начинается с `<mm>:<ss>.<usec>-<duration_us>,<Type>,<level>,...`. Значения могут содержать запятые/переносы (Sql='...'). Имя файла кодирует `YYMMDDHH`.

**Decision.** Lexer — простой regex для head + state-machine для kv-fields со значениями в кавычках (одинарных или двойных, с double-quote escape). Multi-line — look-ahead: следующая строка считается продолжением, если НЕ совпадает с head-pattern.

**Consequences.** + Работает на synthetic fixtures (29 тестов passing). + Корректно обрабатывает unknown event types (без падения, складывая поля в `extra` JSON). − Не parallel — single-threaded. Sprint 2 рассмотрим. − Acceptance gate на real-data — open (Q1 в QUESTIONS.md).

---

## ADR-007 — Conventional commits, один коммит = одна логическая единица

**Status:** Accepted (project-wide rule, унаследовано от Konvey)

**Decision.** Все коммиты — conventional: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`. Один коммит = одна логическая единица работы. Никаких "wip" megacommits. См. git history Sprint 0 как reference.

---

## ADR-008 — Документация на русском, code identifiers на английском

**Status:** Accepted (project-wide rule)

**Decision.** README, ADR, QUESTIONS, ARCHITECT_NOTES, code comments — на русском. Имена функций/классов/переменных — на английском. Pydantic-поля и DuckDB-колонки — на английском.

**Consequences.** + Внутренняя команда на русском, документация легче пишется и читается. + Code identifiers — стандарт индустрии, не вызывает trouble при поиске в Stack Overflow / документации DuckDB/Tauri.

---

## ADR-009 — UI Language Policy: hardcoded ru-RU

**Status:** Accepted (Sprint 1)

**Context.** Дизайн-концепт `design/opt/*.jsx` написан на английском как визуальная спецификация. Целевая аудитория Module 1 — русскоязычные 1С-эксперты и DBA. Подключать i18n framework (react-i18next/lingui) ради одного locale — избыточно для standalone-tool.

**Decision.** Все UI strings — на русском, hardcoded в `frontend/src/i18n/ru.ts` как hierarchical const tree. Дополнительный helper `format()` для подстановки `{placeholders}`. Дизайн-файлы `design/opt/*.jsx` остаются английскими как visual reference (см. `design/README.md`).

**Consequences.** + Минимум boilerplate. + Compile-time проверка ключей через TypeScript. − Если в Module 2+ появится международная аудитория, потребуется миграция на i18n framework. Структура `t.section.key` совместима с типовыми API (i18next ожидает дотированные ключи, миграция тривиальна).

---

## ADR-010 — Folder ingestion = primary (и единственный в UI) источник Module 1

**Status:** Accepted (Sprint 1)

**Context.** Discovery 2026-05-18 показал: реальные пользователи держат ТЖ как структуру папок (`rphost_NNNN/YYMMDDHH.log`), а не zip-архивы. Никто не пакует логи специально перед анализом. Поддержка ZIP в UI = лишний UX-шаг (распаковать → распарсить) на 12 GiB.

**Decision.** UI Module 1 показывает одну кнопку «Загрузить папку с логами…» и принимает drag-and-drop **только папок** (файлы отклоняются с toast). Backend RPC `load_archive(zip_path)` остаётся как deprecated entry для:
- backwards compat с Sprint 0 тестовыми fixtures;
- возможного импорта от техподдержки 1С (если пользовательский запрос).

В Sprint 1 ZIP не появляется в UI ни в каком виде.

**Consequences.** + Чистый UX: один способ загрузки. + Рабочий код Sprint 0 не выбрасывается. + Backend остаётся гибким для будущего. − Пользователь, получивший логи в ZIP, должен распаковать вручную (30 секунд через 7-Zip).

---

## ADR-011 — DuckDB Appender API: Arrow Table batches

**Status:** Accepted (Sprint 1)

**Context.** Sprint 0 использовал `executemany` для bulk insert. На 100K событий это занимало 50+ секунд на Windows — каждая строка идёт отдельной транзакцией. Для 12 GiB корпуса (потенциально 100M+ событий) это нереализуемо.

DuckDB Python 1.5.2 не предоставляет row-by-row Appender API. Native bulk-path — через registered Arrow Table или DataFrame.

**Decision.** `AppenderHandle` оборачивает buffered batches (default 10K rows) → Arrow Table → `conn.register("_appender_batch", table)` + `INSERT INTO events SELECT * FROM _appender_batch`. Indexes создаются ПОСЛЕ полного bulk insert через `create_indexes()`. PRIMARY KEY на `id` снят (uniqueness гарантирована Python-логикой; constraint check замедляет вставку).

Backend dependency: `pyarrow>=15`.

**Consequences.** + 10K events в <1 сек (100× ускорение vs executemany). + Контекстный менеджер с автоматическим flush и cleanup. + Buffer drop при exception (partial state guard — следующий ingest не упирается в PK-конфликт). − Дополнительная dependency `pyarrow` (~80 МБ в bundle). − ID uniqueness теперь только в коде, не в DB; компромисс ради скорости.

---

## ADR-012 — Streaming parser с byte-weighted progress

**Status:** Accepted (Sprint 1)

**Context.** Discovery показал highly skewed distribution: 87% всего объёма (12 GiB) в одном rphost-файле (10.23 GiB). File-count progress даст ложное «27/28 готово = 96%», после чего ingest подвиснет на 5–10 минут.

**Decision.** Парсер работает построчно через buffered `Path.open(buffering=1 MiB)` + line iterator (`iter_raw_events_lines`). Прогресс репортится в **байтах** через JSON-RPC notifications (без id) с polynomial throttle (250 ms = ~4 emit/sec). Sidecar Rust routit notifications через Tauri event `rpc-notification:progress`, frontend подписан и обновляет ProgressCard + StatusBar inline.

**Consequences.** + Honest UX: пользователь видит реальный progress по байтам. + Streaming не загружает 10 GiB в память — peak RSS << 500 МБ (sanity-check в acceptance gate). − Cancellation token не реализован в Sprint 1 (кнопка «Отменить» disabled с tooltip «Sprint 2»). − Throttle мешает unit-тестам — обходится `force=True` или `throttle_ms=0`.

---

## ADR-013 — Tauri 2 native drag-drop API

**Status:** Accepted (Sprint 1)

**Context.** Sprint 0 DropZone использовал DOM listeners (`window.addEventListener("drop", ...)`). В Tauri 2 webview перехватывает file-drag events и эмитит их через свой канал; DOM drop не получает path к файлу/папке. Это был известный bug Sprint 0 (drag-drop ничего не делал).

**Decision.** `tauri.conf.json` → `windows[].dragDropEnabled: true`. DropZone подписан на `tauri://drag-enter`/`tauri://drag-over`/`tauri://drag-leave`/`tauri://drag-drop` events. На drop вызывается Tauri command `classify_path(path)` → `{kind: "folder" | "file" | "missing"}`; при `folder` — `load_directory(path)`, при `file` — toast «Перетащите папку, не файл», при `missing` — toast «Папка не найдена».

**Consequences.** + Drag-drop работает корректно. + Чёткое разграничение валидных таргетов. − DOM-listeners в коде остаются неактивны (для drop-events), но не мешают. Их сохранение лишает refactor этой части — не критично.

---

## ADR-014 — process_role как first-class column

**Status:** Accepted (Sprint 1)

**Context.** Discovery показал 6 типов процессов 1С (rphost, rmngr, ragent, 1cv8c, 1cv8s, 1cv8). Эти роли определяются по имени родительской папки (case-insensitive regex `^(1cv8c|1cv8s|1cv8|ragent|rmngr|rphost)_(\d+)$`) и являются значимой dimension для OQL-фильтров (`where role == "rphost"`).

**Decision.** В schema DuckDB `events` добавлен столбец `process_role VARCHAR` + индекс `idx_events_role`. `process_pid` теперь хранит pid из имени папки (NNNN часть), не OSThread из event. OSThread попадает в `extra` JSON. ParsedEvent dataclass получает `process_role: str = "unknown"`. OQL compiler разрешает алиас `role` → `process_role` и `pid` → `process_pid`.

Регистр имени папки приводится к lowercase в результате (1CV8C_NNNN → role="1cv8c").

**Consequences.** + Естественный OQL для типичных вопросов: «покажи дедлоки только в rphost», «summarize by role». + Streamlined schema. − Backwards-incompatible: Sprint 0 значения `process_pid` (из OSThread) другие в новой схеме (из folder). Sprint 0 тесты переписаны или адаптированы.

---

## ADR-015 — Удаление OQL DSL, переход на raw SQL

**Status:** Accepted (Sprint 2)

**Context.** Sprint 1 поставил OptimyzerQL DSL как декларативный язык запросов поверх ТЖ. После закрытия Sprint 1 и стратегического re-evaluation (см. `PROJECT_REACTIVATION_SPRINT_2.md`) выяснилось: OQL имел смысл только как public brand language ("DataDog query language for 1C"), а Module 1 переориентируется на personal/portfolio tool. SQL знают все 1С-эксперты, OQL — никто.

**Decision.** Удалить пакет `optimyzer_backend/oql/` целиком, `rpc/oql_rpc.py`, CodeMirror OQL extensions, OQL-coupled tests. Saved queries RPC-методы переехать в `handlers.py` (они не OQL-specific). Lark dependency удалена. SQL Console и backend SQL Engine приходят в Phase B.

**Consequences.** + Простой стек: один язык, известный целевой аудитории. + Maintenance одного языка вместо двух. + −197 tests (OQL tests) компенсируются +43 SQL Engine + 8 views + 17 templates + 5 comparison в Sprint 2. − Saved queries из Sprint 1 (если есть) становятся unusable до ручного перевода на SQL; решено принять (single-user tool).

---

## ADR-016 — Pre-built Views as Primary UX

**Status:** Accepted (Sprint 2)

**Context.** SQL editor — power-user-инструмент; 80% типичных вопросов performance-engineer'а (медленные запросы / locks / errors / roles / activity) решаются готовыми views без необходимости писать SQL. Demo сценарий "загрузил архив за 4 часа prod-нагрузки, вот Top 20 slow queries, вот deadlocks" должен быть drag-drop + clicks.

**Decision.** Шесть pre-built investigation views: Top Slow Queries / Locks Timeline / Process Roles / Duration Histogram / Errors Feed / Activity Heatmap. Каждая — отдельный sidebar item + backend SQL aggregation в `sql/views.py`. SQL Console — secondary tab для custom queries.

**Consequences.** + Demo-ready без обучения. + Power-users всё ещё имеют SQL Console. − Pre-built views — additional code surface для maintenance.

---

## ADR-017 — Cross-Filtering поверх views

**Status:** Accepted (Sprint 2)

**Context.** Главная боль 1С performance-engineer'а — найти **корреляции**: spike в lock conflicts ↔ slow queries в этот же момент ↔ memory growth. Изолированные views не дают эту картину; пользователь не должен вручную копировать time range между табами.

**Decision.** `CrossFilters` state в Zustand (time_range, process_role, event_type, source_view). FilterBar в каждом view показывает active filters как chips. Click-to-filter interactions: DonutChart slice в Process Roles → set process_role; HeatmapChart cell в Activity → set time_range. Все views subscribe на filters и re-fetch при изменениях через `useView` hook.

**Consequences.** + Investigation workbench → user может drilling down. + Lazy evaluation: только active view re-fetch'ится при switch фильтра. − Two-way mapping иногда требует heuristics (Activity heatmap → week-relative из current date).

---

## ADR-018 — Multi-archive Comparison

**Status:** Accepted (Sprint 2)

**Context.** Killer-фича для portfolio: "релизнули новую версию УТ, провалилась производительность, сравни до/после". Конкурентов с event-level diff на нашем уровне детализации нет (1С:ЦКК делает comparison на агрегатах).

**Decision.** Comparison не требует special slot tracking в backend — просто принимает два `archive_id` уже загруженных в `_ARCHIVES`. `compare_summary` возвращает 6 high-level metrics с delta/delta_percent. `compare_slow_queries` partition'ит результат на in_both / only_a / only_b / regressed (avg ≥ +50%) / improved (avg ≤ -30%). Side-by-side UI с tabs (Summary + Slow Queries Diff).

**Consequences.** + Direct answer на release-regression вопрос без SQL. + Side effect: testable self-comparison (archive vs itself → delta=0 everywhere). − Memory: две DuckDB connections одновременно (~2x RAM); acceptable на dev-машине 16+GB. − Only Slow Queries diff в Sprint 2; Errors/Roles/Histogram diff отложены на Sprint 3 если будет нужно.

---

## ADR-019 — Read-Only SQL Execution (Defense in Depth)

**Status:** Accepted (Sprint 2)

**Context.** SQL Console позволяет пользователю выполнять arbitrary SQL. Tool — analytical, не data manipulation. Случайный `DELETE FROM events` пользователем должен быть невозможен.

**Decision.** Два защитных слоя:
1. **SQL Validator** (`sql/validator.py`) на parse stage: regex-проверка по списку blocked keywords (INSERT/UPDATE/DELETE/MERGE/TRUNCATE/CREATE/DROP/ALTER/GRANT/REVOKE/ATTACH/DETACH/COPY/PRAGMA/CALL/EXECUTE/VACUUM/...) после strip strings/comments. Только SELECT/WITH allowed на top level. Multi-statement (`;`-separated) запрещён.
2. **Read-only DuckDB connection** (`SQLExecutor`) в `sql/executor.py`: `duckdb.connect(path, read_only=True)`. Даже если validator пропустит что-то — DuckDB сам отклонит write.

**Consequences.** + Two-layer защита: validator должен не пропустить, и connection должен не пропустить. + `INSERT/UPDATE/DELETE` блокируются на двух уровнях (validator → connection). − Read-only connection не позволяет создавать temp tables в SQL Console (acceptable trade-off — CTE достаточно для аналитики).

---

## ADR-020 — Prompt Authoring Standard (`/goal` template)

**Status:** Accepted (post-Sprint 2, applies to Sprint 3+)

**Context.** Sprint 0-2 promt'ы были semi-structured (epics + DoD, без явных STOP RULES и VERIFY секций). Это дало три повторяющиеся проблемы видные из транскриптов Claude Code:
- **Scope creep**: Sprint 1 расширился с 8 до 11 phases mid-implementation (Phase A0, расширенная C, отдельная J)
- **Open-ended questions**: Q1-Q5 в Sprint 1 QUESTIONS.md без ranked options, что теряло темп
- **Отсутствие rollback для destructive operations**: Sprint 2 Phase A (удаление OQL) выполнено без явного rollback-плана в promt'е

**Decision.** Принять `/goal` 8-section template как обязательный формат для всех sprint promt'ов начиная со Sprint 3. Шаблон зафиксирован в [`docs/PROMPT_AUTHORING_STANDARD.md`](./PROMPT_AUTHORING_STANDARD.md):

| Секция | Назначение |
|---|---|
| GOAL | Что делаем — одно предложение |
| CONTEXT | Откуда задача, какие предыдущие решения релевантны |
| CONSTRAINTS | Технические/политические ограничения |
| PRIORITY | Что важнее при trade-offs |
| PLAN | Детальный план phases |
| DONE WHEN | Acceptance criteria |
| VERIFY | Как проверить + **rollback план для destructive operations** |
| OUTPUT | Что попадает в репо (commits, docs, tests) |
| STOP RULES | Явные запреты — copy-paste из universal список |

Universal STOP RULES (копируются дословно в каждый promt):
- При неоднозначности → ranked options (2-4 варианта), не open-ended вопросы
- Не расширять scope (смежные задачи → TODO.md, не в текущий sprint)
- No time estimates в reports
- Light theme only, dark theme forbidden
- Не модифицировать `design/opt/*.jsx`
- Destructive ops → показывать rollback план (git stash / branch)
- Conventional commits обязательны
- Real-data acceptance gate — блокирующее условие

**Consequences.** + Дисциплинированный scope: STOP RULE «не расширять scope после достижения GOAL» прямо запрещает Sprint 1-style scope drift. + Pragmatic decisions: ranked options ускоряют обмен с владельцем. + Rollback safety: VERIFY с rollback планом обязателен для destructive phases. − Minor authoring overhead (8 sections vs free-form). − Sprint 0-2 promt'ы остаются как historical artefacts; ретроактивная переписка не делается.
