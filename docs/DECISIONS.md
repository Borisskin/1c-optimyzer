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


---

## ADR-022 — Курс 1С:Эксперт как canonical roadmap reference

**Status:** Accepted (Sprint 3)

**Context.** До Sprint 3 product scope определялся ситуативно — что просит Сергей, что выглядит логичным расширением. Это работало в Sprint 0-2 (минимальный продукт + 6 views), но к Sprint 3 появилась нужда в чётком критерии "что включаем / что не включаем" — иначе scope бесконечно растёт.

**Decision.** Программа курса 1С:Эксперт по технологическим вопросам (УЦ № 1, фирма 1С) принимается как **canonical roadmap reference**. Mapping каждой фичи на пункты программы зафиксирован в [`docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md`](./FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md) и обновляется при каждом sprint closure.

**Правила:**
1. Каждая новая фича должна явно mapping'оваться на пункт(ы) программы курса.
2. Целевое покрытие Module 1 — ~40-45% программы (analytical/diagnostic part).
3. Stop-list (явный отказ): continuous monitoring, DBA tools, test generation, hardware monitoring, organizational consulting — не делаем в Module 1.

**Consequences.** + Чёткий scope: нет scope creep. + Позиционирование: «1С:Эксперт-в-коробке для middle-программиста 1С». + Self-validation: каждая фича — проверяемая по carнал курса. − Не закрываем 55-60% курса (organizational + Module 2+ + DBA-only). Это осознанный отказ.

---

## ADR-023 — Explainer hybrid architecture (rule + AI)

**Status:** Accepted (Sprint 3 Phase E+F)

**Context.** Sprint 3 ставит цель «1С:Эксперт-в-коробке для middle-программиста». UI должен **объяснять** что произошло, не просто показывать данные. Два подхода:

- **Pure rule-based**: каталог правил с готовыми текстами. Детерминизм, no cost, но ограниченное покрытие edge cases.
- **Pure AI**: запрос к LLM на каждое объяснение. Гибкость, но latency 3-15 сек, 1915, риск галлюцинаций.

**Decision.** Hybrid:

- **Rule engine** (Phase E) — markdown файлы в `backend/explainers/*.md` с YAML frontmatter. Pattern matcher (==/>=/contains/matches regex). Identifies pattern → возвращает готовый текст. Запускается **мгновенно** на любом anatomy view.
- **AI explainer** (Phase F) — Claude API call в background. Использует rule body как контекст (передаётся в system prompt). Возвращает conversational explanation на русском за 3-15 сек. Кеш в SQLite (per archive_id+kind+target_id).
- **UX**: rule показывается сразу при открытии, AI приходит fire-and-forget через несколько секунд и заменяет rule body.

**Consequences.** + Best UX: пользователь видит explanation **сразу**, AI улучшает качество асинхронно. + Контроль расходов: AI кеш = повторный просмотр без cost. + Расширяемость: новые rules — markdown PR, без релиза backend. + Graceful degradation: без API ключа работает только rule-based. − Усложнение: 2 explainer'а вместо 1; UI должен handle оба состояния.

---

## ADR-024 — Backend-only AI calls

**Status:** Accepted (Sprint 3 Phase F)

**Context.** AI explainer требует Claude API key. Два варианта:
- Ключ в frontend (.env Vite-side) — простая интеграция, fetch напрямую с api.anthropic.com.
- Ключ в backend (Python sidecar) — все API calls через RPC, frontend никогда не видит ключ.

**Decision.** Ключ **только** в backend. Frontend вызывает `explainer_ai` RPC, backend читает `ANTHROPIC_API_KEY` из env и делает HTTP call.

**Rationale.**
- Security: ключ не embedding'уется в Tauri bundle, не виден в DevTools, не уходит к пользователю.
- Hosting flexibility: если потом захостим backend в NL/EU с пользователями в РФ — ключ остаётся на нашей стороне, не у пользователя.
- Audit: все AI calls идут через одну точку (`explainer/claude_client.py`) → проще логирование, rate limiting, switch на другую LLM.

**Consequences.** + Безопасность ключа. + Возможность future hosted-edition без architectural rework. − Лишний RPC roundtrip (но он на background flow — UX не страдает).


---

## ADR-025 — BSL Language Server **не** используется в Sprint 4 (pivot на native-only)

**Status:** Accepted (Sprint 4 Phase 0)

**Context.** Sprint 4 promt планировал интегрировать [`1c-syntax/bsl-language-server`](https://github.com/1c-syntax/bsl-language-server) как Java sidecar для анализа SDBL-запросов. STOP RULE промта явно допускал pivot: «если выяснится что BSL LS не работает с standalone SDBL — переориентироваться только на native rules».

**Решение.** Sprint 4 реализует **native-only** Query Analyzer без интеграции с BSL Language Server.

**Обоснование** (см. [BSL_LS_GAP_ANALYSIS.md](BSL_LS_GAP_ANALYSIS.md) для деталей):

1. BSL Language Server создан для языка **BSL** (`Процедура Х() Конец`) — синтаксис модулей конфигурации.
2. **SDBL** (`ВЫБРАТЬ ... ИЗ ...`) — отдельный embedded язык внутри строковых литералов BSL.
3. Sprint 4 Query Analyzer работает с **standalone SDBL** (юзер вставляет голый текст).
4. Обёртка SDBL в фейковый BSL вызывает offset drift диагностик + проблемы с параметрами + 1-3 сек стартап оверхеда (превышает DoD «< 5 сек per query»).
5. Native rules engine на regex покрывает весь target list 12 правил методики ЦУП 2.13.4 без зависимости от Java + .jar.

**Архитектурное наследие.** `backend/src/optimyzer_backend/query_analyzer/bsl_ls_client.py` — thin stub с зарезервированным API (`available`, `analyze_query`). `Aggregator._merge_and_dedupe` уже умеет приоритизировать native над BSL LS findings. Sprint 5+ может включить интеграцию без переделки контракта.

**Consequences.** + Простота: нет Java зависимости, нет 100+ MB jar в installer, нет degraded mode UI. + Стабильность: regex matcher детерминирован, Java subprocess может зависнуть/упасть. + Скорость: native engine < 0.1 сек на типичный запрос vs 1-3 сек BSL LS startup. + Полное покрытие: 13 native rules покрывают всё target list ЦУП 2.13.4. − Не получаем 100+ BSL LS диагностик для BSL модулей — но это Sprint 7+ scope (MCP BSL Atlas), не Sprint 4.

---

## ADR-026 — GPL-3.0 safety: BSL LS лицензия не блокирует Sprint 4

**Status:** Accepted (Sprint 4 Phase 0)

**Context.** `bsl-language-server` распространяется под **GPL-3.0**. GPL-3.0 — copyleft, требует: если ваш код связан (linked) с GPL кодом — ваш код тоже должен быть GPL.

**Решение.** Sprint 4 **не использует** BSL LS (см. ADR-025), поэтому **GPL-3.0 контаминация не применяется**. Наш код может оставаться под любой удобной лицензией (Apache-2.0 / MIT / proprietary — owner decides).

**Если бы использовали** (для справки на будущее):
- Subprocess invocation (`java -jar bsl-language-server.jar ...`) **не** считается linking → наш код **не** становится GPL.
- НЕ bundle `.jar` в наш installer — пользователь сам качает с GitHub releases.
- Это soft separation, юридически чистая.

**Consequences.** + Sprint 4: полная свобода в выборе лицензии. + Sprint 5+ (если включаем BSL LS): subprocess approach подтверждён как безопасный. − ничего.

---

## ADR-027 — Solution Generator архитектурно зарезервирован под Sprint 8

**Status:** Accepted (Sprint 4 Phase F)

**Context.** Sprint 8-9 в roadmap планирует **AI-генератор готовых обработок 1С** (.epf) под конкретную базу через MCP BSL Atlas. Sprint 4 нужен placeholder в API чтобы Sprint 8 не пересматривал контракт.

**Решение.** В Sprint 4 создан `backend/src/optimyzer_backend/query_analyzer/solution_generator.py` — класс `SolutionGenerator` с методом `generate_solution(finding_id, base_context) → dict`. В Sprint 4 всегда возвращает `{ok: False, status_code: 501, error: "Sprint 8"}`. RPC `query_analyzer.generate_solution` зарегистрирован. Frontend кнопка "Сгенерировать решение" **не рендерится** (мы знаем что backend всегда 501).

В `Finding` dataclass добавлено опциональное поле `solution_template_id: str | None = None` — placeholder для Sprint 8.

**Consequences.** + Sprint 8 включает функционал без изменения contract'а / API / frontend hooks. + Документирует roadmap зависимость в коде, не только в docs. − Crystal dead code в Sprint 4 (минимальный — 30 строк).

---

## ADR-028 — Native rules engine как complement к explainer/

**Status:** Accepted (Sprint 4 Phase B)

**Context.** Sprint 3 уже имеет rule engine (`backend/src/optimyzer_backend/explainer/`) для anatomy views (deadlock / slow_op / lock / exception). Возникает вопрос: использовать ли тот же engine для SDBL-запросов, или сделать отдельный?

**Решение.** Сделан **отдельный** `query_analyzer/native_rules.py` engine с собственным `NativeRule` dataclass и `analyze(query_text, rules)` функцией.

**Обоснование.**

- Explainer rules матчат **feature dict** (`{event_type: 'TDEADLOCK', regions_count: 1}`) — это классификация события.
- Query analyzer rules матчат **regex patterns** против исходного текста запроса — это статический анализ кода.
- Разная семантика → разные dataclasses (`Rule` vs `NativeRule`), разные matchers (pattern matcher vs regex finditer), разные результаты (`RuleMatch` vs `Finding` с line/col ranges).

**Что переиспользуется:**
- YAML subset parser `_parse_yaml_subset` из `explainer.rule_loader` — для парсинга frontmatter.
- ClaudeClient pattern — `_load_dotenv_once` reused в `ai_rewriter.py` через delegate.
- SQLite cache pattern — `QueryRewriteCache` использует тот же файл `data/explainer_cache.db`, отдельная таблица `query_rewrite_cache`.

**Consequences.** + Каждый engine оптимизирован под свою задачу. + Нет coupling — изменения в Sprint 5+ explainer не ломают query analyzer. + Меньше surface area для bugs. − Минорное дублирование boilerplate (frontmatter parsing, rule loading).

---

## ADR-029 — Configuration metadata persistence в отдельном SQLite файле

**Status:** Accepted (Sprint 5 Phase A)

**Context.** Sprint 5 индексирует XML выгрузку конфигурации 1С — справочники, документы, регистры, реквизиты, измерения. Объём данных: типовая БП 3.0 = 1647 объектов, ~5-10 МБ в SQLite. Нужно где-то хранить так, чтобы (а) индекс не пересчитывался при каждом запуске tool, (б) не путалось с другими persistent данными, (в) можно было удалить без последствий для остального tool'а.

**Решение.** Отдельный SQLite файл `backend/data/config_metadata.db`, **не** объединять с существующим `backend/data/explainer_cache.db` (Sprint 4 query rewriter cache).

Структура схемы:
- `objects (full_name PK, kind_ru, name, synonym_ru, register_type)`
- `attributes (object_full_name FK, attribute_kind, section_name, name, type_repr, ord)` — атрибуты + измерения + ресурсы + ts-атрибуты в одной таблице, разделение по `attribute_kind`
- `tabular_sections (object_full_name FK, name, ord)`
- `enum_values (object_full_name FK, value_name, ord)`
- `meta (key PK, value)` — `source_hash` для invalidation, `source_path`, `indexed_at`, `config_name/synonym/vendor/version`, `schema_version`

Hash-based invalidation: при `index_configuration(path)` вычисляется sha256 от (имя + размер + mtime) всех `.xml` файлов в папке. Если хеш совпадает с `meta.source_hash` — return `already_indexed`. Иначе truncate всех таблиц и пере-парсинг.

**Обоснование разделения от `explainer_cache.db`:**
- Разная семантика: cache есть всегда (даже без подключённой конфигурации), а configuration_metadata подключается опционально.
- Разные жизненные циклы: cache очищается через UI кнопку «Очистить кеш AI», конфигурация — через `configuration.disconnect`.
- Разные владельцы: cache принадлежит explainer/, configuration_metadata — новый пакет.
- Безопасность: пользователь может удалить файл конфигурации не боясь потерять кеш AI ответов.

**Consequences.** + Изоляция доменов. + Можно удалять config_metadata.db не теряя AI cache. + Sprint 6+ может расширить схему (например, добавить таблицы для модулей и SDBL литералов) не трогая explainer. − Два отдельных SQLite файла вместо одного (минорный disk overhead). − В CI / production надо помнить про оба файла при backup.

---

## ADR-030 — Парсинг XML выгрузки только через стандартную Python библиотеку

**Status:** Accepted (Sprint 5 Phase A)

**Context.** Phase 0 discovery показал что формат XML выгрузки 1С — стандартный, с фиксированным набором namespace'ов (`http://v8.1c.ru/8.3/MDClasses`, `http://v8.1c.ru/8.1/data/core`, и т.п.) и единообразной структурой `MetaDataObject/<тип>/Properties` + `ChildObjects`. Возникает вопрос: использовать ли `lxml` / `xmltodict` / другие внешние библиотеки, или хватит `xml.etree.ElementTree`.

**Решение.** Использовать **только `xml.etree.ElementTree`** из стандартной библиотеки Python. Никаких `lxml`, `xmltodict`, `defusedxml` или других зависимостей.

**Обоснование:**
1. **Меньше зависимостей в installer** — `lxml` тянет libxml2, на Windows может быть проблема с сборкой.
2. **Скорость достаточна** — на real БП 3.0 (1647 объектов, ~5286 XML файлов) парсинг с ET занимает 10 секунд. Это в 3 раза меньше требования DoD #28 (< 30s).
3. **Стандартная библиотека стабильна** — ET API не меняется между версиями Python, нет deprecation сюрпризов.
4. **Безопасность XXE** — выгрузка 1С это **trusted local file** (пришла из Конфигуратора пользователя), а не network input. XXE-атаки не релевантны.

Trade-off: `ET.parse` менее удобен (нужно работать с namespaced tags через `{ns}tag`). Решено через helper `_localname(tag)` который возвращает local name без namespace.

**Consequences.** + Нулевые внешние зависимости. + Гарантированная совместимость с любым Python 3.10+. + Простая сборка. − Чуть более verbose код (но это локализовано в `parser.py`).

---

## ADR-031 — Semantic rules как extension существующего native_rules engine

**Status:** Accepted (Sprint 5 Phase B)

**Context.** Sprint 4 создал `query_analyzer/native_rules.py` с regex-based matcher и `NativeRule` dataclass. Sprint 5 добавляет семантическую валидацию — проверку запроса против структуры конфигурации через `ConfigurationMetadataStore`. Возникает вопрос: делать новый отдельный engine (`SemanticRule` класс + `analyze_semantic`), или расширить existing native engine.

**Решение.** Расширить existing engine. К `NativeRule` добавлены два опциональных поля:
- `requires: list[str] = []` — список требований к контексту. `["configuration_metadata"]` означает что rule запускается только при подключённом store.
- `check_name: str | None = None` — имя функции-чекера в `SEMANTIC_CHECKS` registry. `None` → обычное regex-правило (Sprint 4 поведение).

В `analyze(query_text, rules, config_store=None)`:
- Если rule.requires содержит `"configuration_metadata"` и `config_store=None` или `not is_indexed()` → **silent skip** (не false positive, не warning).
- Если rule.category == "semantic" → вызывается `run_semantic_check(query_text, rule, store)` который диспатчит в `SEMANTIC_CHECKS[rule.check_name]`.
- Остальные rules работают как раньше (Sprint 4).

**Обоснование extension vs replacement:**
1. **Одна точка вызова** — `aggregator.QueryAnalyzer.analyze()` не разрастается на два пути.
2. **Загрузка через тот же loader** — `load_native_rules()` уже умеет парсить frontmatter с любыми полями (`requires`, `check_name` просто пробрасываются).
3. **Дедупликация работает одинаково** — `_merge_and_dedupe` не отличает источник.
4. **Sprint 4 поведение полностью сохранено** — обратной несовместимости нет, все 13 синтаксических rules работают как раньше.

**Silent skip rationale.** Альтернатива была — показывать warning «Не могу проверить, подключите конфигурацию» на каждом запросе если store=None. Решено отказаться: это раздражает пользователя при каждом «Анализировать», навязывает фичу. Вместо этого глобальный badge статуса в UI — discoverable без noise.

**Consequences.** + Минимальное расширение existing code. + Sprint 4 rules не сломаны. + Один engine, один loader, один dispatcher — меньше surface для bugs. + Sprint 6+ может добавить новые categories (например, "performance_semantic") тем же механизмом. − `NativeRule` теперь не строго "native" — имя класса немного misleading, но менять его было бы breaking change.

---

## ADR-032 — Golden test suite формат: plain files (.sdbl + .expected.json)

**Status:** Accepted (Sprint 5 Phase E)

**Context.** Sprint 5 закладывает regression baseline через 30+ эталонных запросов. Нужен формат хранения cases. Варианты:
1. Pytest classes с inline-строками SDBL и assertions.
2. Pickle / shelve / другой бинарный формат.
3. Plain text files: `query.sdbl` + `expected.json` в отдельных папках на каждый case.

**Решение.** Вариант 3 — plain files. Каждый case в отдельной папке вида `tests/golden/queries/{category}/NN_short_name/`:
- `query.sdbl` — UTF-8 текст реального SDBL запроса
- `expected.json` — `{"findings": [...], "requires_configuration": bool, "notes": str}`

Runner `test_golden_suite.py` собирает все папки через `_collect_golden_cases()` и параметризует pytest:
```python
@pytest.mark.parametrize("category, name, query_file, expected_file", _collect_golden_cases())
def test_golden_case(...): ...
```

**Обоснование:**
1. **Читаемость** — любой человек (даже не разработчик) может открыть `query.sdbl` и сразу понять что тестируется. Pickle / shelve этого не дают.
2. **Git diff читаемый** — добавление нового case = два новых файла, изменение запроса = понятный textual diff. Pickle блобы не имеют meaningful diff.
3. **Простота расширения** — добавить case = создать папку. Не нужно править Python код, не нужно понимать pytest fixtures.
4. **Cross-tool** — кейсы можно открыть в любом IDE / редакторе, использовать grep, копировать в issue tracker.
5. **Категории как папки** — `positive/`, `negative/`, `edge_cases/`, `semantic/`, `real_world/` (зарезервировано под Sprint 6). Pytest легко фильтрует через id substring.

**Consequences.** + Низкий порог входа для добавления regression case. + Git history meaningful. + Можно поделиться отдельным case (просто папкой). − Чуть больше файлов в репо (70 файлов для 35 cases). − Pytest `_collect_golden_cases()` бежит по файловой системе при каждом collection — но это <50ms на 35 кейсов.

---

## ADR-033 — bsl-language-server как primary SDBL analyzer

**Status:** Accepted (Sprint 6, 2026-05-24)

**Context.** Sprint 4-5 построил собственный regex-based + semantic rules валидатор SDBL. К Sprint 5 закрылась картина: regex фундаментально ограничен (нет scope tracking подзапросов, type chasing, virtual tables). False positives на типовых конфах — UX-killing. QueryAnalyzer спрятан из Sidebar до Sprint 6. См. OPENSOURCE_RESEARCH_REPORT.md.

**Decision.** Полная интеграция **bsl-language-server v0.29.0** (LGPL-3.0) как primary источника SDBL диагностик. Наш Sprint 4-5 regex-валидатор остаётся как secondary (свёрнут в `<details>` legacy section).

**Consequences.** + 19 production-grade SDBL rules из коробки. + Полная MDO type resolution через их Configuration модель. + Активное сообщество (1c-syntax). + LGPL-3.0 разрешает linking — наш код остаётся проприетарным. − Bundle size +265 MB (JRE 21 + JAR). − Java dependency в стеке. − JVM cold-start ~5-7 сек.

---

## ADR-034 — WebSocket sidecar architecture (vs CLI per-request)

**Status:** Accepted (Sprint 6, 2026-05-24)

**Context.** bsl-language-server поддерживает analyze (CLI), lsp (stdio), websocket (Tomcat) режимы. CLI per-request = cold-start 5-7s × каждый analyze — катастрофа UX. LSP stdio сложнее интегрировать с Python (asyncio + threading bridge).

**Decision.** **WebSocket sidecar с lazy-start.** JVM запускается при ПЕРВОМ обращении к QueryAnalyzer, живёт до выхода backend'а. Auto-restart at crash, max 3 retry.

**Consequences.** + Latency после warmup ~250-700ms (acceptable для interactive UX). + Юзеры не использующие фичу не платят memory cost. − 300-400 MB RAM постоянно когда активен. Реализация: `backend/src/optimyzer_backend/bsl_ls/{lifecycle,client,runtime}.py`.

---

## ADR-035 — Cloud AI orchestration через `/v1/ai/explain`

**Status:** Accepted (Sprint 6, 2026-05-24)

**Context.** AI explanation поверх bsl-LS диагностик — premium feature. Можно вызывать Anthropic API напрямую из desktop ИЛИ через наш cloud backend.

**Decision.** **Через cloud backend** (`api.optimyzer.pro/v1/ai/explain`). В Sprint 6 — minimal без auth/caching, Phase 1 INFRA добавит JWT + cache + soft caps + multi-model routing.

**Consequences.** + API key защищён на сервере. + Centralized caching для всех юзеров (Phase 1). + Multi-model routing (Sonnet Pro vs Opus Business). + Fine-tuning prompts без релиза desktop. + A/B тесты промптов. − Требуется интернет (но без него bsl-LS findings всё равно работают). − +50-100ms HTTPS round-trip (приемлемо при 2-4s Claude latency).

---

## ADR-036 — Bundled JRE 21 vs jlink vs GraalVM Native

**Status:** Accepted (Sprint 6, 2026-05-24)

**Context.** bsl-language-server требует JDK 21+ runtime. Options: bundled JRE (~150MB), jlink стрипнутая (~50MB), GraalVM Native (~80MB), system JRE.

**Decision.** **Bundled полная Eclipse Temurin JRE 21** (~150 MB). Не jlink (риск missing modules в edge cases), не GraalVM (research показал что bsl-LS не имеет native-image config — 2-3 недельный отдельный проект). Не system JRE (80% юзеров 1С не имеют установленной Java).

**Consequences.** + Гарантия запуска на любой Windows 11 без preinstalled Java. + Premium product = no compromises on reliability. − Installer вырастает с 50 MB до ~250 MB (acceptable trade-off). − Memory footprint при работе +300-400 MB. Future: возможно вернёмся к jlink (Sprint 8+) при стабильности.

---

## ADR-037 — PerformanceStudio CLI собираем из source, не используем pre-built

**Status:** Accepted (Sprint 7 Phase A, 2026-05-24)

**Context.** Erik Darling Data PerformanceStudio (MIT) даёт 30 правил анализа SQL Server execution planов. На GitHub releases есть только source code — нет pre-built CLI бинаря для Windows. План Opus предполагал просто скачать готовый. Реальность: пришлось собирать.

**Decision.** **Build from source локально** через `dotnet publish -c Release -r win-x64 --self-contained` при первой установке. .NET 10 SDK поставлен в `tools/dotnet-10/` (user-mode, не загрязняет глобальную систему). Скрипт `scripts/setup-planview-binary.ps1` автоматизирует процесс. Результат — `frontend/src-tauri/binaries/planview/planview.exe` (~96 MB self-contained).

**Consequences.** + Мы контролируем версию (привязаны к v1.11.2 hashed commit). + Можем патчить (TD-Sprint8-A — object cycle bug). + Self-contained — нет dep на system .NET. − Setup time +5-10 минут при first install (build SDK на машине разработчика, не пользователя — Tauri bundle уже содержит готовый exe). − Bundle вырос с ожидаемых 30 MB до 96 MB (self-contained runtime). Альтернатива (framework-dependent) требовала бы .NET 10 install у пользователя → не приемлемо.

---

## ADR-038 — Text format planSQLText: lite view + AI, без XML конверсии

**Status:** Accepted (Sprint 7 Phase D, 2026-05-24)

**Context.** 1С пишет планы в DBMSSQL события ТЖ как **текст** (SHOWPLAN_TEXT output), а не XML. PerformanceStudio CLI и html-query-plan v2.6.1 оба требуют XML на входе. Опции для text format в UI: (A) конвертировать text → XML и пропускать через стандартный pipeline, (B) lite view — только PlanTextView + AI, без visualization и без warnings.

**Decision.** **(B) lite view в Sprint 7.** Конвертация text → XML сложная (operator tree depth >10, 1С-specific extensions, нет известных OSS конвертеров) — выносится в TD-Sprint8-B для Sprint 8 research spike. В Sprint 7 для text плана: `PlanTextView.tsx` (`<pre>` блок с monospace + `white-space: pre` + horizontal scroll) + `AiPlanExplanationCard` (новый `plan_format: "text"` параметр).

**Consequences.** + Простое MVP — text impport работает в день D.1. + AI понимает SHOWPLAN_TEXT отлично (Claude обучен на SQL Server документации). + Не блокируется на исследовании конвертера. − text plans не имеют SSMS-style визуализации (юзер видит только текст). − PerformanceStudio rules не работают (но они в любом случае дают мало value на упрощённом text plan). − Юзер должен понимать что это «lite»; для full functionality — экспорт того же запроса как .sqlplan из SSMS. UI banner в PlanTextView объясняет ограничение.

---

## ADR-039 — Plan Analyzer как отдельный screen, не интеграция в QueryAnalyzer

**Status:** Accepted (Sprint 7 Phase A, 2026-05-24)

**Context.** QueryAnalyzer (Sprint 6) анализирует SDBL код 1С → 19 диагностик от bsl-LS + AI explanation. Опции для Plan Analyzer (Sprint 7): (A) интегрировать как «View execution plan» tab в QueryAnalyzer, (B) отдельный screen в Sidebar (Ctrl+P).

**Decision.** **(B) отдельный screen.** Источники input разные (SDBL код vs .sqlplan файл), pipeline анализа разный (bsl-LS+sqlglot vs PerformanceStudio+html-query-plan), AI prompt разный, output structure разный. Интеграция дала бы confusing UX («введите SDBL... или может .sqlplan?»).

**Consequences.** + Чистая separation of concerns. + Каждый screen optimized под свой use case. + Можно показывать в Sidebar как отдельный шорткат — юзер видит что Optimyzer = много анализаторов. − Дублирование некоторых UI patterns (severity chips, AI card layout) — частично решено через shared components. + Будущие cross-screen integrations (например «View execution plan» button в QueryAnalyzer для outputs Top SQL) делаются явно через router navigation, не через embedded tabs.

---

## ADR-040 — PerformanceStudio severity (Critical/Warning/Info) сохраняем как есть

**Status:** Accepted (Sprint 7 Phase A, 2026-05-24)

**Context.** PerformanceStudio использует scheme {Critical, Warning, Info}. bsl-language-server использует scheme {Blocker, Critical, Major, Minor, Info}. AI explanation использует {Critical, High, Medium, Low} для impact_estimate. Опции: (A) унифицировать всё в одну схему, (B) сохранить per-domain.

**Decision.** **(B) per-domain.** PerformanceStudio severity отображаются как есть (Critical/Warning/Info chips). bsl-LS severities как есть. AI impact_estimate как есть.

**Consequences.** + Доверяем downstream tool — не делаем lossy mapping. + Severity имеет специфический смысл в каждом домене (PerfStudio Critical = «high estimated cost impact», bsl-LS Critical = «гарантированно бажный SDBL»). + UI рендерит native colors каждой схемы — нет confusion с маппингом. − Юзер видит 3 разных severity scheme в разных screens (но Sergey не считает это проблемой — screens используются раздельно). Альтернатива (унификация) — потеря semantic precision; не делаем.

---

## ADR-041 — Один PlanAnalyzer screen для обоих движков, не separate PgPlanAnalyzer

**Status:** Accepted (Sprint 8 Phase B, 2026-05-25)

**Context.** Phase A discovery подтвердил что 1С пишет PG planы в ТЖ как `DBPOSTGRS` events (отдельно от `DBMSSQL`). При обсуждении Phase B рассматривалось создание отдельного screen `PgPlanAnalyzer/`. Однако у real юзеров архив ТЖ часто содержит **и** MSSQL **и** PG events одновременно (migration в процессе, или multi-database setup), и переключение между двумя screens — плохой UX.

**Decision.** Existing `PlanAnalyzer` screen (Sprint 7) расширяется на **универсальный** для обоих движков. UI автоматически detect формат через `detectPlanEngine()` util + использует engine field из RPC ответа (DBMSSQL → "mssql", DBPOSTGRS → "postgres"). Внутренний state хранит `engine: "mssql" | "postgres"` и conditional rendering выбирает правильный view (PlanTextView/PlanVisualization для MSSQL, PgPlanTextView/Pev2PlanVisualization для PG).

**Consequences.** + Один screen для всего — юзер не переключает контекст между двумя tools. + Архивы со смешанным content (DBMSSQL + DBPOSTGRS) работают seamless — engine badge на каждой row + filter toggle для удобства. + Меньше дублирования UI кода (одна dispatcher logic, два specialized view component'а). − PlanAnalyzer.tsx стал сложнее (added state + branching), но это контролируемое усложнение — все условия explicit, нет magic. Альтернатива (две screens) — потеря context при switching, дублирование import/AI/Settings infrastructure.

---

## ADR-042 — pev2 интегрирован через Web Component wrapper (Vue defineCustomElement), не Vue-in-React и не iframe

**Status:** Accepted (Sprint 8 Phase B, 2026-05-25)

**Context.** pev2 (Plan Explorer V2) — Vue 3 компонент от Dalibo Labs. Нужно встроить его в React frontend. Опции:
- (A) **Vue-in-React** — full Vue runtime в React app, через `vue` + ручной mount/unmount, сложный lifecycle
- (B) **iframe** — pev2 как standalone HTML в iframe, communication через postMessage
- (C) **Web Component wrapper** — `defineCustomElement(Plan)` → registers `<pev2-plan>` custom element, React видит обычный HTML

**Decision.** **(C) Web Component wrapper.** Создан `frontend/src/components/vendors/pev2-wrapper/index.ts` с `ensurePev2Registered()` (idempotent), React wrapper `Pev2PlanVisualization.tsx` рендерит `<pev2-plan plan-source={...} plan-query={...} />`. JSX namespace augmentation в `src/types/pev2-jsx.d.ts` даёт TypeScript-safe props.

**Consequences.** + Чистая abstraction — React не знает что внутри Vue. + pev2 CSS автоматически inject'ится в shadow DOM (через `shadowRoot: true`) — нет style leakage в основной app. + Bundle overhead контролируемый: vue (~30 KB gz), pev2 (~150 KB gz), CSS (~5 KB gz). + Web Component переживёт React Strict Mode / HMR (ensurePev2Registered идемпотентно). − Shadow DOM усложняет debugging (но Chrome DevTools хорошо это handles). Альтернатива (iframe) добавила бы 200ms cold start + проблемы с window.parent communication; альтернатива (Vue-in-React) увеличивала бы coupling и risk of lifecycle bugs.

---

## ADR-043 — Re-EXPLAIN для интерактивной визуализации — opt-in feature через PG connection в Settings

**Status:** Accepted (Sprint 8 Phase B, 2026-05-25)

**Context.** PG planы в ТЖ — это **только** текстовый формат (`EXPLAIN ANALYZE TEXT`). pev2 требует **JSON** формат (`EXPLAIN (FORMAT JSON, ANALYZE)`). Опции получения JSON:
- (A) **Always-on PG connection** — Optimyzer обязательно требует PG creds при импорте плана; без этого не работает
- (B) **Opt-in PG connection** — юзер настраивает в Settings; без этого работает текстовый план + AI (Path A)
- (C) **Self-written TEXT → JSON converter** — парсим текст в Python, восстанавливаем JSON структуру

**Decision.** **(B) Opt-in.** Path A (TEXT + AI) — default flow, всегда работает без подключения к PG. Path B (re-EXPLAIN → JSON → pev2) — premium feature, требует юзер настроил read-only PG connection в Settings.

**Consequences.** + Базовый сценарий (TEXT + AI) даёт value с первого момента — без онбординга на PG. + Премиум UX для тех кто готов настроить connection (платящие customers / power users). + Безопасность: re-EXPLAIN запускается через специально настроенного юзера (read-only рекомендация в docs); safety check блокирует DML/DDL до connect. − Юзеры без PG access (security-restricted environments) видят меньше функциональности — но base scenario работает. Альтернатива (A) сделала бы инструмент бесполезным для security-restricted сред. Альтернатива (C) — 2 недели разработки парсера + риск багов в conversion (TEXT и JSON форматы PG не 1-к-1).

---

## ADR-044 — Password PG connections — в OS keychain через keyring (Python), не в SQLite plain

**Status:** Accepted (Sprint 8 Phase B, 2026-05-25)

**Context.** Юзер вводит PG password в Settings UI для opt-in re-EXPLAIN feature. Куда хранить? Опции:
- (A) **Plaintext в SQLite metadata** — простейший вариант; password виден любому кто прочитает файл
- (B) **Encrypted в SQLite** — Optimyzer encrypt'ит при save, decrypt'ит при use; нужен local key
- (C) **OS keychain** — через Python `keyring` library; password хранится в Windows Credential Manager / macOS Keychain / Linux secret service

**Decision.** **(C) OS keychain.** SQLite хранит только metadata (host/port/database/username) + uniquely-generated `password_keychain_key`. Сам password сохраняется через `keyring.set_password("1c-optimyzer-pg", key, password)`. При delete connection — `keyring.delete_password()` тоже вызывается.

**Consequences.** + Используем стандартный OS mechanism — пользователь может ревьюить/удалять через Credential Manager на Windows. + Backups / shared disks не leak пароль (SQLite файл не содержит plaintext). + Нет magic local encryption key который сам уязвим (как было бы в варианте B). + Cross-platform support (Windows/macOS/Linux) бесплатно через keyring abstraction. − На Linux нужен secret service daemon (gnome-keyring / KWallet); для headless server scenarios это требует setup. Для production desktop app — стандартный setup. − Нельзя экспортировать настройки между машинами как простой файл (но это и не требуется — каждый юзер настраивает локально).

---

## ADR-045 — sql_antipatterns module (новый, рядом с sql/), dialect-aware structure

**Status:** Accepted (Sprint 8 Phase C, 2026-05-25)

**Context.** Sprint 6 реализовал 9 T-SQL antipatterns в одном файле `backend/src/optimyzer_backend/sql/antipatterns.py`. Phase C нужно добавить 15 PG детекторов + dispatcher по engine. Опции структуры:
- (A) Дописывать в существующий `sql/antipatterns.py` — файл разросся бы > 1000 строк, MSSQL и PG код перемешан
- (B) Переименовать `sql/` → `sql_antipatterns/` (как предложил архитектор в Phase C промте) — но `sql/` содержит ещё anatomy.py, validator.py, executor.py, deadlock_anatomy.py и т.д., которые не имеют отношения к antipatterns
- (C) Создать новый параллельный модуль `sql_antipatterns/` с подпапками `tsql/`, `postgres/`, `shared/` + backward-compat shim в `sql/antipatterns.py`

**Decision.** **(C)** — новый модуль `sql_antipatterns/` с dialect-based структурой. Существующий `sql/antipatterns.py` остаётся как тонкий shim который делегирует в новый engine с `engine="mssql"`. Это сохраняет backward compat для Sprint 6 imports + чистая новая структура.

**Consequences.** + Чистое разделение: `tsql/detectors.py` (9 T-SQL правил), `postgres/<detector>.py` (15 PG правил по файлу), `shared/` (заготовка для общих helpers), `engine.py` (dispatcher), `models.py` (SqlAntipattern + TSqlAntipattern alias). + Sprint 6 код продолжает работать через shim (25 legacy tests pass без изменений). + Каждый PG детектор в своём файле — легко расширять / тестировать индивидуально. − Один уровень indirection (shim) для Sprint 6 кода — минимальная стоимость в обмен на zero-risk migration.

---

## ADR-046 — 1С-context detection через regex heuristic (не proper parser)

**Status:** Accepted (Sprint 8 Phase C, 2026-05-25)

**Context.** Некоторые PG антипаттерны имеют другую интерпретацию в 1С-контексте: `_Description::mchar = '1'::mchar` — это нормально для 1С (extension типы), но в чистом PG это redundant cast. Нужен механизм определить — это 1С-генерируемый SQL или нет. Опции:
- (A) Proper парсер бинаризации 1С таблиц — точно, но дорого и требует mapping configuration metadata
- (B) Regex heuristic — быстро, false positive rate ~5%, но достаточно для большинства случаев
- (C) Phase A configuration_context (если подключён) — accurate, но 90% юзеров не подключают конфу

**Decision.** **(B) regex heuristic** + optional override через `force_1c_context` параметр. Pattern: `_(reference|document|accumrg|...)\d+` для таблиц, `(::|AS )(mchar|mvarchar|fulleq)` для типов. Если хоть один matched → `is_1c_context=True`.

**Consequences.** + Быстро (~1ms на запрос) — не блокирует engine. + Работает без подключённой конфигурации (90% юзеров). + Можно override через RPC параметр для тестов / explicit control. − False positive если SQL случайно содержит таблицу с похожим именем (`_my_seq42`) — но шанс реально малый. − False negative для редких 1С таблиц с custom prefix — но эти кейсы можно расширять regex по мере обнаружения.

---

## ADR-047 — Параллельный flow antipatterns + AI: local fast + cloud slow

**Status:** Accepted (Sprint 8 Phase C, 2026-05-25)

**Context.** В PlanAnalyzer есть два источника анализа SQL: (1) AI cloud explanation (Claude Sonnet 4.5, 5-20 секунд), (2) local sqlglot antipatterns engine (< 100ms). Возможные UX:
- (A) Sequential: сначала antipatterns, потом AI — UX медленный (юзер ждёт оба)
- (B) Parallel: оба запускаются одновременно — antipatterns показываются мгновенно, AI приходит позже
- (C) On-demand: antipatterns тоже по кнопке как AI — лишний клик

**Decision.** **(B) Parallel.** При импорте плана сразу запускается `backend.sqlAntipatternsDetect(sql, engine)` (быстро, локально). AI остаётся на кнопке (квота / токены / latency). При нажатии кнопки AI получает уже найденные antipatterns в `detected_antipatterns` поле request — Claude использует их как context и НЕ дублирует в hotspots.

**Consequences.** + Юзер сразу видит обнаруженные антипаттерны (визуальный feedback). + AI explanation качественнее — Claude фокусируется на специфике плана, не повторяет то что уже видно. + Меньше токенов в AI response (нет повторов). − Дополнительный API call к backend при импорте плана — но это локально, < 100ms. − Frontend dependency: antipatterns должны успеть до AI request — но AI на кнопке, так что race не возможен.

---

## ADR-048 — Sprint 8 закрыт без Phase D (planSQLText XML конвертер не нужен)

**Status:** Accepted (Sprint 8 Phase C closure, 2026-05-25)

**Context.** В Phase A был draft Phase D: «конвертировать planSQLText TEXT в SHOWPLAN_XML формат чтобы использовать existing PerformanceStudio CLI». После реализации Phase B стало понятно:
- PG planSQLText — всегда **TEXT** или **JSON** (от PG EXPLAIN), не XML
- pev2 нативно работает с JSON (через re-EXPLAIN) — даёт visual без conversion
- PerformanceStudio CLI заточен под MSSQL XML — конвертация PG TEXT туда — это потеря semantic information

**Decision.** Phase D **отменён**. Закрываем Sprint 8 тремя фазами (A + B + C) с тегом `v0.8.0-internal`. Для PG visual analysis используем (1) `PgPlanTextView` для TEXT format, (2) `Pev2PlanVisualization` после re-EXPLAIN для JSON. PerformanceStudio CLI остаётся только для MSSQL.

**Consequences.** + Не тратим 1-2 недели на conversion который ничего не даёт. + Архитектура чище: каждый формат идёт через свой родной view. + Phase C может включать всё что было в Phase D scope (PG antipatterns engine был в обоих изначально). − Pev2 требует JSON (т.е. либо re-EXPLAIN, либо юзер вставляет EXPLAIN FORMAT JSON output) — для чистого TEXT мы остаёмся с line-by-line render. Это acceptable trade-off.

---

## ADR-049 — Real-world fixture strategy: synthetic + extracted, не реальные дампы

**Status:** Accepted (Sprint 9 Phase A, 2026-05-25)

**Context.** Для regression-тестов нужны реальные SQL запросы. Опции:
- (A) Дамп реальных запросов из production ТЖ клиента — риск утечки данных (PII в значениях параметров)
- (B) Извлечение из тестовой базы Test1CProf (localhost:2541) — безопасно, но объём мал (< 30 запросов)
- (C) Синтетические запросы по образцу реальных 1С-паттернов + извлечённые pg_stat_statements из pgBase — полное покрытие без PII

**Decision.** **(C)** — гибридный подход. MSSQL: 32 синтетических запроса в sp_executesql обёртке, покрывают 8 основных антипаттернов 1С. PG: 12 извлечённых + 22 синтетических = 34 total. Все запросы работают на типовых 1С-именах таблиц (`_Reference15`, `_Document70`, `_AccumRg5000`) без реальных значений бизнес-параметров.

**Consequences.** + Нет риска утечки данных клиента. + Fixtures воспроизводимы и детерминированы. + Охватывают все ключевые антипаттерны (SELECT *, LIKE %, NOT IN, cross join, implicit convert). + Синтетические запросы проще параметризовать для новых тест-кейсов. − Не ловят специфические баги на очень нестандартных SQL которые иногда генерирует 1С Platform (можно добавить отдельно по мере нахождения).

---

## ADR-050 — normalize_ai_enum: generic helper вместо ad-hoc per-field проверок

**Status:** Accepted (Sprint 9 Phase D, 2026-05-25)

**Context.** AI (Claude) иногда возвращает нестандартные значения enum: "High" вместо "Critical", "Moderate" вместо "Warning", "Low" вместо "Info". Sprint 7-8 обрабатывал это через ad-hoc условия в `_norm_sev()`. По мере роста числа полей (hotspot.severity, recommendation.impact_estimate, suggested_index.impact_estimate, overall_severity) дублирование росло.

**Decision.** Единый `normalize_ai_enum(value, mapping, default, field_name)` в `server/services/ai_explainer.py`. Принимает mapping `dict[str, str]` с canonical + alias keys в lowercase. Логгирует предупреждение если значение неизвестно. Два готовых mapping: `SEVERITY_MAPPING` (Critical/Warning/Info + алиасы), `IMPACT_MAPPING` (Critical/High/Medium/Low + алиасы). Тесты: 30+ кейсов в `tests/test_ai_normalize.py`.

**Consequences.** + Один код path для всей AI enum нормализации — легко добавлять алиасы. + Logging неизвестных значений позволяет мониторить AI enum drift. + 30+ тестов документируют все алиасы. − Чуть больше indirection — минимальная стоимость (helper простой).

---

## ADR-051 — tj-simulator: 7 новых сценариев через тот же worker-shell паттерн

**Status:** Accepted (Sprint 9 Phase C, 2026-05-25)

**Context.** Sprint 9 Phase C расширяет tj-simulator 7 новыми сценариями. Вопрос реализации: добавить в существующую обработку или создать отдельную.

**Decision.** Расширяем существующую обработку `МоделированиеТЖ.epf`. Новые сценарии разделены на два типа: (1) параллельные блокировочные сценарии (TDEADLOCK X-X, chain, длинная транзакция) — через тот же `WScript.Shell 1cv8c.exe /Execute` паттерн; (2) однопоточные сценарии (Memory, N+1, Heavy SDBL, PG-паттерны) — выполняются в текущей сессии через `РеквизитФормыВЗначение("Объект")` wrapper. Обе группы добавлены в новый визуальный блок "Дополнительные сценарии (Sprint 9)".

**Consequences.** + Переиспользуем проверенный worker паттерн (тот же механизм TLOCK/TDEADLOCK). + Нет новых зависимостей и новых EPF файлов. + Расширение расширения `ВоркерыТЖ` новыми background-task методами. − Форма становится длиннее (13 кнопок vs 6) — решено группировкой в отдельный UsualGroup. Сценарии 9-12 (Memory/N+1/SDBL/PG) не нуждаются в параллельных сессиях и не генерируют TLOCK/TDEADLOCK — они генерируют только DBMSSQL события, что достаточно для testing antipatterns detection.

---

## ADR-053 — logcfg.xml generation: download-only, no Apply locally

**Status:** Accepted (Sprint 10, 2026-05-25)

**Context.** Экран TJ Config Builder генерирует logcfg.xml. Два варианта доставки: (a) скачать файл и положить самостоятельно; (b) "Apply locally" — автоматически записать файл в C:\Users\...\AppData\Local\1C\1cv8\conf\logcfg.xml. Вариант (b) требует Tauri `fs` plugin с правами записи + UAC на Windows + правильного определения пути для каждой версии 1С.

**Decision.** Download-only. Файл генерируется в памяти как Blob (`application/xml`) и отдаётся браузеру через `URL.createObjectURL`. Пользователь кладёт файл в нужную папку сам. Инструкции по расположению файла — в документации.

**Consequences.** + Нет зависимости от Tauri fs plugin, + нет UAC headaches, + работает в любом WebView, + пользователь явно контролирует размещение файла. − Лишний ручной шаг (положить файл). Mitigation: документация с пошаговой инструкцией, в будущем Sprint 11+ можно добавить Apply locally как отдельную опцию.

---

## ADR-054 — xmlSerializer: pure TypeScript без XML-библиотек

**Status:** Accepted (Sprint 10, 2026-05-25)

**Context.** Для генерации logcfg.xml нужен сериализатор. Варианты: (a) сторонняя XML-библиотека (xmlbuilder2, fast-xml-parser); (b) DOMParser/XMLSerializer браузера; (c) pure TypeScript template-строки.

**Decision.** Pure TypeScript `xmlSerializer.ts` — строковая генерация через шаблоны с `escapeXml()` для спецсимволов. Структура logcfg.xml фиксированная и малая (≈20 строк XML), полноценная XML-библиотека избыточна. `escapeXml()` корректно обрабатывает `&`, `<`, `>`, `"`, `'`.

**Consequences.** + Нет npm-зависимостей, + bundle size 0 добавляется, + 21 unit-тест покрывает все edge cases, + полный контроль над форматом XML. − Ручное поддержание при изменении схемы logcfg.xml. Mitigation: тесты фиксируют ожидаемый XML формат.

---

## ADR-055 — LogcfgConfig: структурированная модель через все слои

**Status:** Accepted (Sprint 10, 2026-05-25)

**Context.** AI endpoint получает запрос и должен вернуть конфигурацию ТЖ. Варианты: (a) AI возвращает raw XML строку; (b) AI возвращает структурированный JSON (LogcfgConfig).

**Decision.** Структурированный JSON через все слои: Pydantic `LogcfgConfig` на сервере, TypeScript `LogcfgConfig` на фронтенде. AI prompt инструктирует вернуть JSON по схеме. `xmlSerializer.ts` финально трансформирует в XML только при скачивании.

**Consequences.** + AI JSON проще валидировать (Pydantic strict), + фронтенд получает типизированный объект, + UI может редактировать конфиг после AI (GraphicalBuilderTab), + retry logic при invalid JSON прост. − Усложняет AI prompt. Mitigation: чёткие примеры в prompt, фильтрация неизвестных событий.

---

## ADR-056 — detect_platform: multi-strategy с explicit confidence

**Status:** Accepted (Sprint 10, 2026-05-25)

**Context.** Экран конструктора показывает версию 1С в badge для информирования пользователя. Нужен backend RPC `logcfg.detect_platform`. Версия влияет на некоторые настройки (TTIMEOUT появился в 8.3.17).

**Decision.** Три стратегии с явным полем `confidence`:
1. **Folder scan** → `confidence="high"`: сканирует стандартные пути установки, возвращает наибольший semver.
2. **TCP probe localhost:1541** → `confidence="medium"`: порт rphost агента; если открыт — 1С запущен, версию берём из folders или дефолт.
3. **Fallback 8.3.24** → `confidence="low"`: safe default для отображения.

UI показывает badge только если версия определена. При `confidence="low"` добавляет «(предположительно)».

**Consequences.** + Работает без admin priv (только чтение FS), + без WMI/registry (которые требуют особых прав), + graceful при нестандартной установке, + UI не блокируется (вызов best-effort при mount). − При установке 1С в нестандартную папку — fallback. Mitigation: в будущем добавить Settings поле «Путь к установке 1С».

---

## ADR-052 — CSS design token lint: identify-first, fix-as-you-go

**Status:** Accepted (Sprint 9 Phase D, 2026-05-25)

**Context.** Sprint 9 добавляет lint-скрипт `scripts/check-css-tokens.ps1` для обнаружения hardcoded hex-цветов в CSS modules. При первом прогоне обнаружено 254 нарушения в 32 файлах — весь legacy CSS написан до введения `--o-*` design token системы.

**Decision.** Lint запускается (и интегрирован в `npm run lint:css`) но **не блокирует CI** на текущем этапе. Существующие 254 нарушения — известный технический долг. Правило: **новые файлы** и **новые правки CSS** должны использовать только `var(--o-*)`. Whitelist разрешает #000/#fff/transparent и определения самих token'ов (`--o-*: #hex`). Полная миграция существующего CSS — отдельный рефакторинг-спринт.

**Consequences.** + Lint работает и выявляет нарушения — tooling готов. + Не блокирует разработку пока legacy CSS не мигрирован. + Документирует 254 нарушения как known tech debt. − Без blocking enforcement новые нарушения могут проскользнуть — это trade-off между скоростью разработки и качеством. Mitigation: code review + linkreview на CSS changes.

