# Opus Handover — Sprint 1 → Sprint 2 (1C-Optimyzer)

> Передача состояния проекта в следующую сессию архитектора (Claude Opus 4.7).
> Сергей открывает эту сессию вместе с архитектором, чтобы спланировать Sprint 2.

---

## Краткий статус

**Sprint 1 = OQL Standalone Module 1 — закрыт по коду на 28/31 criteria** (acceptance gate выполняется фоновым прогоном на 12 GiB корпусе; результат — см. §6).

Что заработало:
- **Folder ingestion** (primary path, ADR-010). Drag-drop папок + кнопка «Загрузить папку с логами…».
- **Byte-weighted progress** с notifications (ADR-012). ProgressCard + StatusBar inline.
- **DuckDB Appender via Arrow** (ADR-011). 10K events/<1s, 100× ускорение Sprint 0.
- **process_role first-class column** (ADR-014) — 6 ролей case-insensitive (1cv8c/1cv8s/1cv8/ragent/rmngr/rphost).
- **OQL DSL** — Lark grammar + parameterized SQL compiler + validator + execute/validate RPC.
- **CodeMirror 6** editor с syntax highlighting, autocomplete, inline lint errors.
- **8 templates + saved queries** (SQLite-backed).
- **ru-RU UI** через `frontend/src/i18n/ru.ts` (ADR-009).
- **Synthetic generator** для тестов без 12 GiB зависимости.

Что не заработало (вне scope Sprint 1, явно deferred):
- Cancel ingestion (Sprint 2 — нужен thread-safe cancellation token).
- Chart / Timeline views функциональные (Sprint 2).
- Export CSV/JSON/XLSX (Sprint 2).
- AI Helper natural language → OQL (Sprint 2/3).
- Multi-archive sessions (Sprint 2 — Sprint 1 = simplified replace).
- PyInstaller bundling + production MSI (Sprint 3).

---

## Что архитектор должен прочитать первым делом

1. `docs/SPRINT_1_REPORT.md` — полный отчёт по фазам, метрики, DoD checklist.
2. `docs/DECISIONS.md` — теперь 14 ADR (ADR-009..014 добавлены в Sprint 1).
3. `docs/QUESTIONS.md` — Q1 (закрыт через `OPTIMYZER_REAL_FOLDER_PATH`), Q6..Q9 (закрыты в Sprint 1).
4. `docs/ARCHITECT_NOTES.md` — observations + open arch вопросы.
5. `docs/SPRINT_0_CLOSURE_NOTES.md` — обоснование архитектурных сдвигов Sprint 1.

---

## Sprint 2 scope (предлагаемый — для уточнения архитектором)

Главная цель Sprint 2 — **production polish** + **export/share + AI assist + multi-archive UX**. После Sprint 2 продукт shippable beta.

### Epics предположительные

#### 1. Result views: Chart, Timeline, Raw

Sprint 1 — placeholders. Sprint 2 — настоящие визуализации:

- **Chart** — Recharts или DuckDB → визуализация через nivo / visx. Bar / line / pie из OQL `render` hint.
- **Timeline** — горизонтальная hronology событий с zoom/pan; группировка по process_role.
- **Raw JSON** — есть в Sprint 1, но добавить syntax highlight и copy-to-clipboard.

#### 2. Export

- CSV (без zip)
- JSON (одиночный файл)
- XLSX (через openpyxl или ExcelJS — без external office)
- Buffered streaming для больших результатов (10M+ rows)
- RPC `export_query_result(archive_id, query, format) → file_path` (saves to %APPDATA%/exports/...)

#### 3. AI Helper

Natural language → OQL через Anthropic API (или OpenAI). Pro-only feature (Module 2+ branding).
- "покажи долгие dbmssql за последний час" → `events | where event_type == "DBMSSQL" and duration_ms > 1000ms | timerange last 1h | order by duration_ms desc | take 100`
- "конфликты блокировок по rphost" → `events | where event_type == "TLOCK" and role == "rphost" | order by ts desc | take 100`
- Free-tier — pin AI badge "Pro" в TopBar (уже сейчас disabled с tooltip).

#### 4. Multi-archive sessions

- Sprint 1 — simplified replace (новая загрузка заменяет архив).
- Sprint 2 — full multi-session dropdown: список открытых архивов в TopBar, switch между ними, unload через UI.
- Bonus: cleanup .duckdb файлов в `%APPDATA%/1c-optimyzer/duckdb/` через UI («Удалить с диска»).

#### 5. Cancel ingestion + thread-safe abort

- threading.Event-based cancellation token, проброс в FolderSource.discover() и parser loop.
- UI кнопка «Отменить» в ProgressCard становится active.
- При cancel — partial DuckDB cleanup, toast «Загрузка отменена».

#### 6. Performance tuning

- Multiprocessing для parser (один процесс на файл, объединение через Manager). 12 GiB → < 5 минут.
- DuckDB `PRAGMA threads = N` для bulk insert.
- Возможно — Arrow Table chunking стримом (Arrow IPC stream) вместо buffer-then-register.

#### 7. UX polish

- Подсказки в Editor: hover на column name → tooltip "Метка времени, TIMESTAMP".
- Saved queries: переименование inline (без window.prompt — proper dialog).
- ProgressCard: ETA вычисление по rate (events/sec).
- DocsPanel (slide-in справа) — реальная документация OQL с примерами.

#### 8. SQL preview panel

- В OQL Console — collapsible panel "Compiled SQL" — показывает result.sql_compiled.
- Полезно для debugging и обучения пользователей.

### Acceptance gate Sprint 2

- Все 18 sidebar items с тооltipами (без 404).
- 12 GiB корпус загружается за < 5 минут (от 10+ минут в Sprint 1).
- Export CSV работает на 1M rows без OOM.
- AI Helper отвечает на 5 типовых вопросов корректным OQL.
- Cancel ingestion работает + partial cleanup на cancel.
- Multi-archive: открыто 2 архива одновременно, можно переключаться.

### Risks / unknowns для Sprint 2

- Anthropic API requires API key + billing. Опция: ввод ключа в Settings; tooltip "Add API key in Settings" если не настроен.
- Multiprocessing на Windows + Python: cold-start overhead на pool init. Возможно лучше использовать `concurrent.futures.ProcessPoolExecutor` с initializer.
- Cancellation token нужно протащить через Lark/Arrow конверсию — не тривиально.

---

## Что архитектор уже знает про проект (не нужно re-explain)

- **Стек:** Tauri 2 + React/TS + Python sidecar + DuckDB + SQLite + pyarrow + lark. ADR-001.
- **Модульная стратегия:** Module 1 = OQL Standalone, Module 2+ = real-time agents. ADR-005.
- **CSS Modules** (не Tailwind) в production app. ADR-002.
- **Светлая тема, 1280px min-width.** ADR-004.
- **Conventional commits, русский в docs/code-comments, английский в identifiers.** ADR-007, ADR-008.
- **ru-RU UI = hardcoded в i18n/ru.ts** (ADR-009).
- **Folder ingestion only в UI; ZIP — backend-only** (ADR-010).
- **DuckDB Appender = Arrow Table batches via conn.register** (ADR-011).
- **Streaming parser + byte-weighted progress notifications** (ADR-012).
- **Tauri 2 native drag-drop API + classify_path command** (ADR-013).
- **process_role first-class column** (ADR-014).
- **Real-data acceptance gate = `OPTIMYZER_REAL_FOLDER_PATH` env var** + auto-load из `.env.test` в conftest.py.

---

## Структура репо (для быстрой ориентации)

```
1c-optimyzer/
├── README.md
├── start.bat                          ← PyCharm: .\start.bat
├── .env.test                          ← gitignored, OPTIMYZER_REAL_FOLDER_PATH
├── .env.test.example                  ← template
├── design/
│   ├── README.md                      ← English reference policy (ADR-009)
│   ├── 1c-optimyzer-design-v1.html
│   ├── opt/                           ← 19 JSX-файлов: дизайн-reference
│   └── screenshots/
├── docs/
│   ├── DECISIONS.md                   ← 14 ADRs
│   ├── QUESTIONS.md
│   ├── ARCHITECT_NOTES.md
│   ├── SPRINT_0_REPORT.md
│   ├── SPRINT_0_CLOSURE_NOTES.md
│   ├── SPRINT_1_REPORT.md             ← этот спринт
│   ├── OPUS_HANDOVER_SPRINT_0.md
│   ├── OPUS_HANDOVER_SPRINT_1.md      ← этот файл
│   └── LOGS_INSPECTION.md             ← discovery 2026-05-18
├── backend/                           # Python sidecar
│   ├── pyproject.toml                 ← +pyarrow, +lark
│   ├── src/optimyzer_backend/
│   │   ├── __main__.py
│   │   ├── ingest/                    ⭐ NEW Sprint 1
│   │   │   ├── source.py              (LogSource ABC, LogFile, IngestProgress)
│   │   │   ├── folder_source.py
│   │   │   ├── zip_source.py          (legacy, backwards compat)
│   │   │   ├── log_detector.py
│   │   │   ├── process_role_extractor.py
│   │   │   ├── encoding_detector.py
│   │   │   └── progress_reporter.py
│   │   ├── oql/                       ⭐ NEW Sprint 1
│   │   │   ├── grammar.lark
│   │   │   ├── ast.py
│   │   │   ├── parser.py
│   │   │   ├── compiler.py
│   │   │   ├── validator.py
│   │   │   └── templates.py
│   │   ├── archive/extractor.py       (legacy alias на ingest.zip_source)
│   │   ├── parsers/tj_parser.py       (+process_role, +streaming variant)
│   │   ├── storage/
│   │   │   ├── duckdb_store.py        (+AppenderHandle, +process_role schema)
│   │   │   └── sqlite_store.py        (+saved_queries table)
│   │   ├── rpc/
│   │   │   ├── dispatcher.py
│   │   │   ├── handlers.py            (refactor: async ingestion + load_directory)
│   │   │   └── oql_rpc.py             ⭐ NEW Sprint 1
│   │   ├── models/...
│   │   └── scripts/inspect_logs.py    (discovery script from pre-Sprint 1)
│   └── tests/                         ← 197 passing + 5 acceptance env-gated
├── frontend/
│   ├── package.json                   ← +codemirror packages
│   ├── src-tauri/
│   │   ├── tauri.conf.json            (+dragDropEnabled)
│   │   ├── icons/icon.ico
│   │   └── src/
│   │       ├── main.rs                (+classify_path command)
│   │       └── sidecar.rs             (notifications routing)
│   └── src/
│       ├── main.tsx, App.tsx          (+onProgress subscription)
│       ├── i18n/ru.ts                 ⭐ NEW Sprint 1
│       ├── codemirror/                ⭐ NEW Sprint 1
│       │   ├── oql-language.ts
│       │   ├── oql-theme.ts
│       │   ├── oql-autocomplete.ts
│       │   ├── oql-linter.ts
│       │   └── index.ts
│       ├── api/backend.ts             (+loadDirectory, +executeOqlQuery, +onProgress, ...)
│       ├── store/appStore.ts          (+ingest, +progressCardMinimized)
│       ├── styles/optimyzer-design.css
│       ├── components/
│       │   ├── icons/Icon.tsx
│       │   ├── primitives/
│       │   ├── charts/
│       │   ├── chrome/{TopBar,Sidebar,StatusBar}.tsx (ru-RU)
│       │   ├── overlays/
│       │   │   ├── CommandPalette.tsx (ru-RU)
│       │   │   ├── DropZone.tsx       (Tauri 2 native API)
│       │   │   ├── ProgressCard.tsx   ⭐ NEW Sprint 1
│       │   │   └── Toasts.tsx
│       │   └── screens/OQLConsole/
│       │       ├── OQLConsole.tsx     (rewired w/ Editor)
│       │       ├── Editor.tsx         ⭐ NEW Sprint 1
│       │       ├── TemplatesBar.tsx   ⭐ NEW Sprint 1
│       │       └── SavedQueriesMenu.tsx ⭐ NEW Sprint 1
└── scripts/...
```

---

## Git state

- Ветка: `feat/sprint-1-ingest-and-oql` (от `feat/sprint-0-foundation`).
- Базовая ветка: `main` (Sprint 0 PR pending merge → потом этот спринт mergeable).
- Коммиты Sprint 1 (chronological):
  - `0b47a19` chore(sprint1): pre-sprint setup — .env.test scaffold
  - `37276b5` feat(sprint1/locale): ru-RU localization (Phase A)
  - `c009122` feat(sprint1/ingest): folder ingestion layer (Phase B)
  - `c392436` feat(sprint1/storage): DuckDB Appender + process_role schema (Phase E)
  - `ca33b0f` feat(sprint1/progress): byte-weighted progress + load_directory RPC (Phase C)
  - `9c9f844` feat(sprint1/dragdrop): Tauri 2 native drag-drop API (Phase D)
  - `6d9ef32` feat(sprint1/oql): OQL DSL parser, compiler, validator, RPC (Phase F)
  - `f880457` feat(sprint1/oql-ui): templates, saved queries, CodeMirror editor (Phases G+H+I)
- Финальный коммит Sprint 1 — этот handover + acceptance gate + Phase K — будет создан после результата ingest.

---

## Готов к Sprint 2

Архитектор может приступать к проектированию Sprint 2 prompt'а сразу после прочтения этой передачи. Никаких blocking-вопросов — есть только эпики и risks выше.

После закрытия acceptance gate (12 GiB ingest finishes без exceptions) и manual smoke (drag-drop + OQL query end-to-end в окне Tauri) — Sprint 1 закрывается, PR открывается, можно начинать Sprint 2.
