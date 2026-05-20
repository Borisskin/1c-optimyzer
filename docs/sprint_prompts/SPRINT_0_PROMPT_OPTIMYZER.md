# Sprint 0 — Foundation для 1C-Optimyzer Module 1 (OptimyzerQL Standalone Tool)

> **Контекст:** это первый рабочий sprint после setup. Setup (создание репо, дизайн в `design/`, шаблоны docs) уже выполнен.
> **Working directory:** `D:\1C-Optimyzer\1c-optimyzer\` (либо `repo root`).
> **GitHub:** `github.com/anymasoft/1c-optimyzer`.

---

## 1. Контекст и стратегия

### Что мы строим — Module 1

**1C-Optimyzer** — продукт строится **модульно**. Sprint 0 закладывает фундамент для **Module 1: OptimyzerQL Standalone Tool**.

Module 1 — это **desktop-приложение для Windows** (потом Linux/macOS), которое:
- Принимает архив технологического журнала 1С (zip с папкой logcfg)
- Парсит ТЖ в локальную базу (DuckDB)
- Предоставляет **OptimyzerQL DSL** — declarative query language для анализа ТЖ
- Показывает результаты в Table / Chart / Timeline / Raw JSON форматах
- Позволяет сохранять/делиться/экспортировать запросы

Module 1 — **standalone**, без агентов на проде, без central server, без AI Co-pilot.

**Стратегическая роль Module 1:**
1. Самостоятельная ценность (1С:Эксперты, DBA, senior 1С-разработчики получают bessery способ анализировать ТЖ чем grep/awk)
2. Foundation для всего продукта (OptimyzerQL = универсальный язык на котором потом будут построены остальные модули)
3. Inbound marketing engine (free tier — скачал → загрузил архив → написал запрос → получил value; идеальный pull для статей на Habr/Infostart)

### Что мы строим — Sprint 0

Sprint 0 — **foundation sprint**. Vertical slice от drag-and-drop архива ТЖ до отображения первых 100 событий в Table view. **Без OptimyzerQL parser** (Sprint 1), **без всех result views** кроме Table (Sprint 2), **без полировки UI** (Sprint 3).

После Sprint 0:
- Окно приложения открывается
- TopBar / Sidebar / StatusBar отрисованы согласно дизайну
- Drag-and-drop архива ТЖ работает
- Парсер обрабатывает события базовых типов (`CALL`, `DBMSSQL`)
- События сохраняются в DuckDB
- В OQL Console — preset hardcoded query «show me first 100 events» показывает таблицу

---

## 2. Архитектурные решения (RESOLVED для Sprint 0)

### Стек технологий

**Identical to Konvey** — переиспользуем опыт и инфраструктуру:

- **Frontend:** Tauri 2 + React 18 + TypeScript + Vite + CSS Modules
- **Backend (sidecar):** Python 3.11+ via PyInstaller, JSON-RPC over stdio
- **Local storage:** DuckDB (embedded, для парсенных ТЖ событий) + SQLite (для metadata приложения: saved queries, recent files, settings)
- **Build target:** Windows MSI (Sprint 0 — dev build only; production MSI — Sprint 3)
- **No external services:** работает 100% offline, никакие API calls не требуются

### Структура проекта

```
1c-optimyzer/
├── README.md                          (уже создан)
├── .gitignore                         (уже создан)
├── design/                            (уже создан — НЕ трогать)
│   ├── 1c-optimyzer-design-v1.html
│   ├── opt/*.jsx
│   └── screenshots/*.png
├── docs/                              (уже создан — заполняется в Sprint 0)
│   ├── DECISIONS.md
│   ├── QUESTIONS.md
│   ├── ARCHITECT_NOTES.md
│   └── PROCESS.md                     (НОВЫЙ — workflow project)
├── frontend/                          (Tauri/React frontend)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tauri.conf.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── backend.ts             (JSON-RPC wrapper)
│   │   ├── components/
│   │   │   ├── chrome/                (TopBar, Sidebar, StatusBar)
│   │   │   ├── icons/                 (Icon.tsx с inline SVG)
│   │   │   ├── primitives/            (Badge, KBD, Panel, KPI, Tabs, etc.)
│   │   │   └── screens/
│   │   │       └── OQLConsole/        (Module 1 главный экран)
│   │   ├── store/                     (Zustand stores)
│   │   ├── styles/
│   │   │   └── optimyzer-design.css   (CSS-переменные из shared.jsx)
│   │   └── types/                     (TypeScript types)
│   └── src-tauri/
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       └── src/main.rs                (Rust shell + sidecar bridge)
├── backend/                           (Python sidecar)
│   ├── pyproject.toml
│   ├── src/
│   │   └── optimyzer_backend/
│   │       ├── __init__.py
│   │       ├── __main__.py            (JSON-RPC entry point)
│   │       ├── rpc/                   (RPC method handlers)
│   │       ├── models/                (Pydantic models)
│   │       ├── parsers/
│   │       │   └── tj_parser.py       (TЖ events parser)
│   │       ├── storage/
│   │       │   ├── duckdb_store.py    (DuckDB layer)
│   │       │   └── sqlite_store.py    (metadata layer)
│   │       └── archive/
│   │           └── extractor.py       (zip extraction)
│   └── tests/
│       ├── fixtures/                  (sample TЖ archives для тестов)
│       └── test_*.py
└── scripts/
    ├── check-env.ps1                  (pre-flight checks)
    ├── dev.ps1                        (run Tauri dev)
    └── build-sidecar.ps1              (PyInstaller build for production)
```

### Visual identity и UI primitives

**ВСЁ берётся из `design/opt/shared.jsx`** — этот файл фактически и есть визуальная спецификация. Извлекаем оттуда:

- **CSS-переменные** (из tailwind config + style block) → `frontend/src/styles/optimyzer-design.css`
- **Icon component** — 50+ inline SVG из object `I` → `frontend/src/components/icons/Icon.tsx`
- **TopBar / Sidebar / StatusBar** — chrome components → `frontend/src/components/chrome/`
- **Primitives** (Badge, KBD, Panel, PageHeader, KPI, Tabs, SegBtn, CodeBlock, SQLBlock, BSLBlock, Th, Td) → `frontend/src/components/primitives/`
- **Charts** (Spark, MiniBars, Donut, LineChart, Heatmap) → `frontend/src/components/charts/`
- **Animations**: pulse / slide-in / fade-in / flash → определены в CSS файле

**Конкретные значения (закладываем как CSS-переменные):**

```css
:root {
  /* Backgrounds */
  --o-bg: #FAFAFA;
  --o-panel: #FFFFFF;
  --o-subtle: #F5F5F5;
  --o-hover: #F0F0F0;
  --o-codebox-bg: #FBFBFA;
  
  /* Text */
  --o-text-1: #0A0A0A;
  --o-text-2: #525252;
  --o-text-3: #A3A3A3;
  --o-text-4: #737373;
  
  /* Accent (deep teal) */
  --o-accent: #0F766E;
  --o-accent-hover: #115E59;
  --o-accent-light: #F0FDFA;
  
  /* Semantic */
  --o-ok: #16A34A;
  --o-ok-bg: #F0FDF4;
  --o-warn: #D97706;
  --o-warn-bg: #FFFBEB;
  --o-err: #DC2626;
  --o-err-bg: #FEF2F2;
  --o-info: #2563EB;
  --o-info-bg: #EFF6FF;
  
  /* Borders */
  --o-border: #EDEDED;
  --o-border-2: #E5E5E5;
  
  /* Shadows */
  --o-shadow-panel: 0 1px 0 rgba(10,10,10,0.04), 0 1px 2px rgba(10,10,10,0.04);
  --o-shadow-pop: 0 8px 28px -8px rgba(10,10,10,0.18), 0 2px 6px rgba(10,10,10,0.06);
  
  /* Radii */
  --o-radius-sm: 3px;
  --o-radius-md: 6px;
  --o-radius-lg: 8px;
  
  /* Fonts */
  --o-font-sans: 'Inter', system-ui, sans-serif;
  --o-font-mono: 'JetBrains Mono', ui-monospace, monospace;
}
```

**Шрифты:** загружаем Inter и JetBrains Mono из Google Fonts в `index.html` (как сейчас сделано в дизайне).

### App layout grid

Точно как в дизайне:
- TopBar: 48px высоты, full width, sticky top
- Sidebar: 56px (collapsed) / 232px (expanded) ширины, full height
- StatusBar: 28px высоты, full width, sticky bottom
- Main content: остаток

CSS Grid:
```css
.app {
  display: grid;
  grid-template-columns: 56px 1fr;
  grid-template-rows: 48px 1fr 28px;
  height: 100vh;
  min-width: 1280px;
}
.app[data-sidebar="open"] { grid-template-columns: 232px 1fr; }
```

### Sidebar — interpretation для Module 1

В дизайне в Sidebar — все 18 экранов. В Module 1 — **только OptimyzerQL активен**, остальные **visible but disabled** с tooltip:

```tsx
const NAV_ITEMS_MODULE_1 = [
  { id: 'oql', enabled: true,  group: 'live',    label: 'OptimyzerQL', icon: I.Terminal },
  
  // Disabled in Module 1, available in upcoming modules:
  { id: 'dashboard',  enabled: false, group: 'live',    label: 'Operations',         tooltip: 'Module 2: Real-time monitoring' },
  { id: 'apdex',      enabled: false, group: 'live',    label: 'Apdex & SLA',        tooltip: 'Module 2: Real-time monitoring' },
  { id: 'workbench',  enabled: false, group: 'live',    label: 'Investigation',      tooltip: 'Module 3: Investigation Workbench' },
  { id: 'queries',    enabled: false, group: 'analyze', label: 'Slow Queries',       tooltip: 'Module 3' },
  { id: 'locks',      enabled: false, group: 'analyze', label: 'Locks & Deadlocks',  tooltip: 'Module 3' },
  { id: 'cluster',    enabled: false, group: 'analyze', label: 'Cluster Health',     tooltip: 'Module 2' },
  { id: 'indexes',    enabled: false, group: 'analyze', label: 'Indexes & Stats',    tooltip: 'Module 4' },
  { id: 'profiler',   enabled: false, group: 'analyze', label: 'BSL Profiler',       tooltip: 'Module 4' },
  { id: 'health',     enabled: false, group: 'config',  label: 'Health Scan',        tooltip: 'Module 5' },
  { id: 'compare',    enabled: false, group: 'config',  label: 'Compare',            tooltip: 'Module 5' },
  { id: 'predictive', enabled: false, group: 'config',  label: 'Predictive',         tooltip: 'Module 6' },
  { id: 'resolution', enabled: false, group: 'manage',  label: 'Resolution',         tooltip: 'Module 4' },
  { id: 'multibase',  enabled: false, group: 'manage',  label: 'Multi-base',         tooltip: 'Module 6' },
  // 'oql' already above
  { id: 'knowledge',  enabled: false, group: 'manage',  label: 'Knowledge Base',     tooltip: 'Module 7' },
  { id: 'alerts',     enabled: false, group: 'manage',  label: 'Alerts',             tooltip: 'Module 2' },
  { id: 'reports',    enabled: false, group: 'manage',  label: 'Reports',            tooltip: 'Module 3' },
  { id: 'mobile',     enabled: false, group: 'manage',  label: 'Mobile Companion',   tooltip: 'Module 6' },
];
```

Visual treatment disabled items:
- `opacity: 0.45`, `cursor: not-allowed`
- Hover показывает tooltip с module name + краткой подсказкой
- Click — no-op (или показать toast «Coming in Module N»)

Это **стратегически важно**: пользователь видит **всю карту продукта** при первом запуске и понимает roadmap.

### TopBar — interpretation для Module 1

В дизайне TopBar показывает:
- Логотип «1C-Optimyzer v2.7.118 · prod»
- Env selector «УТ 11.5 — Production» / «8.3.25.1394 · MS SQL 2022»
- Search bar (Cmd+K)
- Health indicator с alerts count
- Bell, AI button, User avatar

Для Module 1:
- Логотип: «1C-Optimyzer v0.1.0 · standalone» (текущая версия)
- Вместо env selector — **archive file selector**:
  - Если архив не загружен: `[ Load TZ archive… ]` button (clickable, открывает file dialog)
  - Если загружен: `[ MyArchive_20260518.zip · 142 МБ ]` dropdown (показывает recent archives, можно reload или change)
- Search bar остаётся (но в Module 1 пока пустой Command Palette с минимальным набором: file menu, recent archives, exit)
- Health indicator показывает **DuckDB status**: `[ ● Ready · 2.3M events ]` или `[ ● Parsing… 45% ]`
- Bell: disabled (alerts — Module 2)
- AI button: visible с label «Pro», disabled с tooltip «Available in Pro»
- User avatar: minimal (просто иконка settings)

### StatusBar — interpretation для Module 1

В дизайне:
```
● connected · УТ 11.5 — Production    agents 12/12 online    ● events 12,847/s        last sync 2s ago · ingest 23.4 MB/s · session 02:14:08 · v2.7.118-stable
```

Для Module 1:
```
● ready · MyArchive_20260518.zip    DuckDB: 2.3M events · 384 МБ        parsed in 1m 42s    v0.1.0-dev
```

### JSON-RPC API — Sprint 0 минимум

RPC methods для Sprint 0:

```python
# Health & info
rpc.method('ping') -> { "status": "ok", "version": "0.1.0" }
rpc.method('get_app_info') -> { backend_version, python_version, duckdb_version }

# Archive lifecycle
rpc.method('load_archive', path: str) -> { archive_id, size_bytes, file_count, status: "loading" }
rpc.method('get_archive_status', archive_id: str) -> { status: "loading|parsing|ready|error", progress: 0..1, events_parsed, errors: [...] }
rpc.method('list_recent_archives') -> [{ path, loaded_at, events_count, size_bytes }]
rpc.method('unload_archive', archive_id: str) -> { ok: true }

# Events query (Sprint 0 — primitive, no OQL yet)
rpc.method('query_events_preset', archive_id: str, preset: "first_100" | "longest" | "deadlocks") -> {
    columns: [{ name, type }],
    rows: [[...]],
    total_count: int,
    truncated: bool,
}

# DuckDB stats
rpc.method('get_storage_stats', archive_id: str) -> {
    events_count: int,
    db_size_bytes: int,
    parsing_speed_eps: float,  # events per second
    archive_metadata: { source_dir, recorded_period, ... }
}
```

В Sprint 1 добавим:
```python
rpc.method('execute_oql_query', archive_id: str, query: str) -> { columns, rows, ... }
rpc.method('validate_oql_query', query: str) -> { valid: bool, errors: [...] }
rpc.method('list_saved_queries') -> [...]
rpc.method('save_query', name, content, ...) -> { id }
```

### DuckDB схема — Sprint 0 минимум

```sql
CREATE TABLE events (
    -- Primary identification
    id BIGINT PRIMARY KEY,
    archive_id VARCHAR NOT NULL,
    
    -- Time
    ts TIMESTAMP NOT NULL,
    duration_us BIGINT,   -- microseconds (TЖ native precision)
    
    -- Event classification
    event_type VARCHAR NOT NULL,  -- 'CALL', 'SCALL', 'DBMSSQL', 'EXCP', 'TLOCK', 'TDEADLOCK', 'MEM', etc.
    
    -- Context (most events have these)
    session_id INT,
    user_name VARCHAR,
    context VARCHAR,         -- 'Документ.РеализацияТоваровУслуг.Модуль...'
    process VARCHAR,         -- 'rphost', 'rmngr', 'ragent'
    process_pid INT,
    
    -- Database (for DBMSSQL events)
    sql_text TEXT,
    sql_text_normalized TEXT,
    sql_text_hash VARCHAR(64),
    rows_read BIGINT,
    rows_modified BIGINT,
    
    -- Other typed fields (JSON for flexibility in Sprint 0)
    extra JSON,
    
    -- Source tracking
    source_file VARCHAR,
    source_line_start INT
);

CREATE INDEX idx_events_archive ON events(archive_id);
CREATE INDEX idx_events_ts ON events(archive_id, ts);
CREATE INDEX idx_events_type ON events(archive_id, event_type);
CREATE INDEX idx_events_duration ON events(archive_id, duration_us DESC);
CREATE INDEX idx_events_sql_hash ON events(archive_id, sql_text_hash);
```

В Sprint 1+ добавим отдельные таблицы для specialized event types (deadlocks с lock graph, query plans).

### Технологический журнал — формат, что парсим в Sprint 0

ТЖ — текстовый формат, каждый event на одной или нескольких строках. Формат:

```
<minute_offset>:<seconds>.<microseconds>-<duration_us>,<event_type>,<level>,<key1>=<value1>,<key2>=<value2>,...
```

Пример:
```
32:14.402023-8124000,DBMSSQL,5,process=rphost,p:processName=erp,OSThread=12340,t:clientID=14,Sql='SELECT ...',Context='Документ.Реализация.Модуль.ОбработкаПроведения'
```

Сложности:
- Многострочные events (когда `Sql` содержит newlines)
- Escape characters в values
- Имя файла содержит **timestamp до минуты**: `26051718.log` = 2026-05-17 18:00 (год-месяц-день-час)
- Минуты + секунды берутся из event prefix
- TЖ собирается в папки по PID процесса

**Для Sprint 0 — парсим базовые event types:**
- `CALL` — server call (главный type для analyzer)
- `SCALL` — server call duration
- `DBMSSQL` — SQL execution (главный type для query analyzer)
- `EXCP` — exception
- `TLOCK` — managed lock conflict
- `TDEADLOCK` — deadlock

Остальные типы (MEM, LEAKS, ATTN, и т.д.) — parser должен **не падать** на них, но не обязательно полностью парсить (можно сохранить в `extra` JSON).

### Hard Constraints (project memory)

- **Всё на русском**: документация, ADR, code comments — на русском; code identifiers — на английском
- **Никаких сроковых оценок** в reports / docs (только scope / complexity / dependencies)
- **Никаких external API calls** в Module 1 (полностью offline tool)
- **Никаких dependency на 1С платформу** (Module 1 работает с архивами ТЖ как с текстовыми файлами, не требует установленного 1С)
- **Real-data testing как mandatory gate** для каждого спринта начиная со Sprint 0 (acceptance gate = парсер не падает на реальном архиве ТЖ)
- **Светлая тема как primary** (тёмная — отложена на Module 2+)
- **Min-width окна 1280px** (desktop-only design)

---

## 3. Epics — что строим в Sprint 0

### Epic A: Базовая инфраструктура (frontend + backend scaffold)

**A1. Frontend scaffold (Tauri 2 + React/TS):**
- `npm create tauri-app` или manual setup
- TypeScript strict mode
- Vite для bundling
- React 18 + React DOM
- Zustand для state management
- CSS Modules (НЕ Tailwind в production app — Tailwind остался только в design preview)

**A2. Python backend scaffold:**
- `pyproject.toml` с poetry или venv + pip
- Python 3.11+
- Dependencies: `pydantic>=2`, `duckdb`, `lxml`, `aiofiles`
- `__main__.py` с JSON-RPC entry point (паттерн из Konvey)
- pytest для тестов

**A3. JSON-RPC bridge:**
- Rust в `src-tauri/src/main.rs` запускает Python sidecar как child process
- Stdin/stdout общение JSON-RPC 2.0 protocol
- Frontend `src/api/backend.ts` — wrapper над Tauri invoke

**A4. Scripts:**
- `scripts/check-env.ps1` — проверяет Node, Python venv, Rust, MSVC
- `scripts/dev.ps1` — запускает Tauri dev mode с auto-reload sidecar

**A5. Vertical slice проверка:**
- `npm run tauri dev` открывает окно
- Окно показывает «1C-Optimyzer v0.1.0» с одной кнопкой «Ping backend»
- Click на кнопку — RPC `ping` returns `{ status: "ok" }`, frontend показывает toast
- Это **минимальный E2E test** того что frontend ↔ backend связь работает

### Epic B: Visual identity — design system

**B1. CSS-переменные:**
- Извлечь все CSS variables из `design/opt/shared.jsx` (color palette, fonts, shadows, radii)
- Создать `frontend/src/styles/optimyzer-design.css` с этими переменными
- Загрузить Inter и JetBrains Mono из Google Fonts в `index.html`

**B2. Icon system:**
- Извлечь все ~50 inline SVG из `I` object в `shared.jsx`
- Создать `frontend/src/components/icons/Icon.tsx` с такой же сигнатурой:
  ```tsx
  type IconName = 'Activity' | 'Gauge' | 'Search' | ... ;
  type IconProps = { name: IconName; size?: number; sw?: number; className?: string };
  export function Icon({ name, size=16, sw=1.6, className }: IconProps) { ... }
  ```
- Использовать `<Icon name="Search" />` как стандартный pattern

**B3. UI primitives:**
- `Badge` (tone: ok | warn | err | info | teal | mute | ink)
- `KBD` (keyboard shortcut display)
- `Sev` (severity dot)
- `Panel` (panel container с title/sub/right)
- `PageHeader` (с breadcrumbs, title, sub, right, KPIs)
- `KPI` (label/value/sub display)
- `Tabs` (tabs strip с icons и counts)
- `SegBtn` / `SegGroup` (segmented buttons)
- `Th` / `Td` (table primitives)

Все эти компоненты — буквально портируются 1:1 из `shared.jsx` (там React, у нас TypeScript). 

**B4. Charts:**
- `Spark` (sparkline)
- `MiniBars` (mini bar chart)
- `Donut` (donut chart)
- `LineChart` (line chart с axis)
- `Heatmap` (7x24 heatmap)

Простые SVG-based реализации, как в `shared.jsx`. Никаких сторонних chart-libraries.

**B5. Code blocks:**
- `CodeBlock` (generic mono pre)
- `SQLBlock` (с syntax highlighting — keywords, RU keywords, numbers, strings, table aliases, 1C `_Fld` columns)
- `BSLBlock` (с BSL keyword highlighting)

Portировать функции `hlSQL` и render логику из `shared.jsx`.

### Epic C: App shell (chrome components)

**C1. TopBar (`components/chrome/TopBar.tsx`):**
- Logo + version (`1C-Optimyzer v0.1.0 · standalone`)
- Archive selector / loader button (см. Module 1 interpretation выше)
- Search bar (Command Palette trigger Cmd+K)
- DuckDB status indicator
- Bell (disabled, tooltip «Module 2»)
- AI button (disabled with «Pro» label)
- Settings dropdown (минимальный — Preferences, About)

**C2. Sidebar (`components/chrome/Sidebar.tsx`):**
- 18 navigation items с 4 groups (LIVE / ANALYZE / CONFIG / MANAGE)
- Module 1: только `oql` enabled, остальные disabled (`opacity: 0.45`, tooltip)
- Collapse/expand toggle (56px → 232px)
- Active state: teal left border + teal background tint

**C3. StatusBar (`components/chrome/StatusBar.tsx`):**
- Connection/ready indicator (зелёная точка)
- Current archive name + size
- DuckDB stats (events count, db size)
- Parsing time / progress
- Version string

**C4. App layout (`App.tsx`):**
- CSS Grid layout (см. выше)
- Routing: Zustand store с `currentScreen: 'oql'` (только oql активен в Module 1)
- При выборе disabled item — toast «Coming in Module N»

**C5. Command Palette:**
- Cmd+K / Ctrl+K trigger
- Modal overlay с search input
- В Module 1 — минимальный набор команд:
  - `Open archive…` (file dialog)
  - `Recent archives` (list)
  - `About`
  - `Quit`
- Fuzzy filter (простой substring match для Sprint 0)

### Epic D: Archive loading & extraction

**D1. File picker UI:**
- В TopBar: click на «Load TZ archive…» → открывается Tauri file dialog (filter: `*.zip`)
- Drag-and-drop поддержка: вся область приложения принимает dropped file
- При drop — отображается overlay «Drop archive here»

**D2. Backend: archive extraction (`backend/archive/extractor.py`):**
- Validate zip integrity
- Extract в temp directory (`%TEMP%\1c-optimyzer\archives\<archive_id>\`)
- archive_id = uuid4
- Возвращает структуру: список папок (`rphost_xxxx`, `rmngr`, etc.), их файлы (.log)
- Streaming извлечение (не загружать весь zip в memory) — `zipfile` модуль Python

**D3. UI: archive loading progress:**
- После выбора файла — TopBar показывает spinner + «Extracting…»
- StatusBar обновляется: `Extracting MyArchive.zip… 23%`
- По завершении extraction — переход к parsing (Epic E)

### Epic E: TЖ parser (subset)

**E1. Lexer/parser для TЖ событий (`backend/parsers/tj_parser.py`):**
- Stream-парсинг каждого `.log` файла
- Event boundary detection: новая строка с pattern `^\d{2}:\d{2}\.\d{6}-` = начало нового event
- Multi-line events: всё до следующего event prefix = тело текущего event
- Извлечение minute/seconds/microseconds + duration
- Имя файла → year/month/day/hour (`YYMMDDHH.log`)
- Combined timestamp = year/month/day/hour + minute + seconds + microseconds (UTC)

**E2. Event type parsers (specific):**
- **CALL** event: extract `process`, `p:processName`, `Context`, `Sdbl`, `Memory`, `MemoryPeak`, `InBytes`, `OutBytes`
- **DBMSSQL** event: extract `Sql`, `Rows`, `RowsAffected`, `Context`, `Plan` (если есть), `dbms`, `dbpid`
- **EXCP** event: extract `Exception`, `Descr`, `Context`
- **TLOCK** event: extract `Granted`, `Wait`, `Regions`, `Locks`
- **TDEADLOCK** event: extract `DeadlockConnectionIntersections`
- Остальные events: сохранять `event_type` + raw text в `extra` JSON

**E3. SQL normalization (для DBMSSQL events):**
- Заменить параметры/литералы на placeholders
- Нормализованный hash для дедупликации запросов
- Простая реализация: regex для `?`, `@PN`, numeric/string literals
- Это поможет в Sprint 1+ когда OQL будет делать `summarize by sql_normalized`

**E4. Insert в DuckDB:**
- Batch inserts (1000-10000 events per batch для performance)
- `INSERT INTO events VALUES (...), (...), ...` либо DuckDB native `Appender` API
- Progress reporting каждые N events back to frontend

**E5. Parser tests:**
- `test_parser_basic_events.py`: synthetic CALL + DBMSSQL events parse correctly
- `test_parser_multiline_sql.py`: SQL с переносами строк парсится корректно
- `test_parser_unknown_event.py`: unknown event type не падает parser, сохраняется в extra
- `test_parser_file_timestamp.py`: timestamp combined правильно из filename + event prefix
- **Acceptance test:** `test_parser_real_archive.py` на **реальном архиве ТЖ** (заложить как `@pytest.mark.skip("requires owner-provided fixture")` — Сергей предоставит после Sprint 0)

### Epic F: DuckDB storage

**F1. DuckDB setup (`backend/storage/duckdb_store.py`):**
- Embedded DuckDB instance per archive (database file: `%APPDATA%\1c-optimyzer\duckdb\<archive_id>.duckdb`)
- Connection pool / context manager
- Schema initialization (CREATE TABLE events с indexes — см. выше)

**F2. Insert performance:**
- Использовать DuckDB `Appender` API для bulk inserts
- Batch size 10 000 events
- Progress reporting back to frontend

**F3. Preset queries (для Sprint 0, до полного OQL):**
- `first_100`: `SELECT * FROM events ORDER BY ts LIMIT 100`
- `longest`: `SELECT * FROM events WHERE duration_us IS NOT NULL ORDER BY duration_us DESC LIMIT 100`
- `deadlocks`: `SELECT * FROM events WHERE event_type = 'TDEADLOCK' ORDER BY ts LIMIT 100`

Хардкод этих query в `backend/rpc/events_rpc.py`. Sprint 1 заменит на parser OQL.

**F4. SQLite metadata store (`backend/storage/sqlite_store.py`):**
- App-level metadata (не per-archive):
  - Recent archives list (path, loaded_at, archive_id, events_count, size)
  - Settings (window size, sidebar state, theme)
- DB path: `%APPDATA%\1c-optimyzer\metadata.sqlite`

### Epic G: OQL Console screen (минимальная версия для Sprint 0)

Это **главный экран Module 1**. В Sprint 0 — минимальная заглушка, без OQL parser.

**G1. Layout (`components/screens/OQLConsole/OQLConsole.tsx`):**
- Соответствует структуре в `design/opt/optimyzerql.jsx`
- PageHeader: breadcrumbs `Manage > OptimyzerQL Console`, title с badge `free tier`
- Right actions: Templates / Docs / Share / Run (Cmd+Enter)
- Main area: split-pane `grid-cols-[1fr_1fr]`:
  - **Left pane (Editor)** — Sprint 0: простой `<textarea>` (CodeMirror — в Sprint 1)
  - **Right pane (Results)** — Sprint 0: только Table view
- Bottom bar: templates list (в Sprint 0 — preset queries как кликабельные buttons)
- Docs panel: collapsible (в Sprint 0 — static content из shared.jsx DocsPanel)

**G2. Empty state (когда archive не загружен):**
- Editor показывает placeholder: «Load a TZ archive to start querying»
- Results pane показывает empty state с большой кнопкой «Load TZ archive…»

**G3. Loaded state (когда archive parsed):**
- Editor — textarea с дефолтным контентом (read-only в Sprint 0):
  ```
  // OptimyzerQL — Sprint 1 feature
  // Sprint 0 supports preset queries only
  // Click a template below to run
  ```
- Results показывает selected preset query results

**G4. Templates bar (bottom):**
- 3 кликабельных pseudo-templates:
  - `[ First 100 events ]` → RPC `query_events_preset('first_100')`
  - `[ Longest 100 events ]` → RPC `query_events_preset('longest')`
  - `[ Deadlocks ]` → RPC `query_events_preset('deadlocks')`
- При click — Results pane обновляется с возвращёнными данными

**G5. Results Table view:**
- Использует `Th` / `Td` primitives
- Columns: dynamic, на основе response (`columns` array)
- Sorting не обязательно в Sprint 0 (Sprint 2)
- Pagination: показываем `total_count` + `truncated` flag

**G6. Run button:**
- В Sprint 0 — disabled (OQL ещё не реализован)
- Tooltip: «OQL execution — Sprint 1»

---

## 4. Что НЕ делаем в Sprint 0

- OptimyzerQL parser / interpreter (Sprint 1)
- Syntax highlighting в editor (Sprint 1, через CodeMirror)
- Autocomplete (Sprint 1)
- Templates library (Sprint 1)
- Chart / Timeline / Raw views (Sprint 2)
- Export CSV / JSON (Sprint 2)
- AI Helper (Module 2 или paid tier, точно НЕ в Sprint 0/1)
- Saved queries (Sprint 2)
- Other 17 screens (Sidebar показывает, но disabled — Module 2+)
- Production .msi installer (Sprint 3)
- Onboarding flow / Welcome screen (Sprint 3)
- AI Chat panel (Module 2+, в Sprint 0 — visible но disabled)
- Performance tuning при больших архивах >10 GB (Sprint 2)
- Linux / macOS builds (после первого MVP launch)
- Темная тема (Module 2+)

---

## 5. Definition of Done — Sprint 0

| # | Critierion | How verified |
|---|---|---|
| 1 | `npm run tauri dev` запускает приложение, окно открывается | manual check |
| 2 | TopBar / Sidebar / StatusBar отрисованы согласно дизайну | visual diff vs `design/opt/dashboard.jsx` (для chrome) |
| 3 | Sidebar collapse/expand работает | manual |
| 4 | Disabled items в Sidebar показывают tooltip с module name | manual |
| 5 | Command Palette (Cmd+K) открывается с минимальным набором команд | manual |
| 6 | Backend Python sidecar запускается, RPC `ping` работает | manual + unit test |
| 7 | Drag-and-drop zip архива работает | manual |
| 8 | Backend разархивирует zip в temp dir без ошибок | unit + integration test |
| 9 | Parser обрабатывает CALL/DBMSSQL/EXCP/TLOCK/TDEADLOCK events на synthetic fixture | pytest |
| 10 | Parser НЕ падает на unknown event types | pytest |
| 11 | DuckDB схема создаётся, events инсертятся batch'ами | pytest |
| 12 | Frontend получает progress updates во время parsing | manual |
| 13 | OQL Console screen отрисован согласно `design/opt/optimyzerql.jsx` (Layout 1:1) | visual diff |
| 14 | Preset queries (`first_100`, `longest`, `deadlocks`) возвращают данные в Table view | manual + integration test |
| 15 | StatusBar показывает реальные DuckDB stats (events count, db size) | manual |
| 16 | pytest >= 25 tests passing (parser, archive extraction, storage) | CI / local run |
| 17 | Conventional commits (feat:, fix:, chore:, docs:, test:) | git log |
| 18 | SPRINT_0_REPORT.md и обновлённый ARCHITECT_NOTES.md созданы | files exist |
| 19 | **Real-data acceptance test:** parser обрабатывает реальный архив ТЖ от владельца без exceptions, >95% events успешно парсятся (acceptance gate) | manual + log |

**Real-data acceptance gate** (пункт 19) — обязательное условие закрытия Sprint 0. Если ещё нет архива ТЖ от владельца — это **blocking question** который оформляется в QUESTIONS.md и обсуждается до начала разработки.

---

## 6. Workflow

1. Прочитай этот promt полностью
2. Создай ветку `feat/sprint-0-foundation`
3. **Перед началом написания кода** — открой `QUESTIONS.md` и добавь Q1 «Реальный архив ТЖ для acceptance testing — когда и где получим?»
4. Выполняй epics последовательно: A → B → C → D → E → F → G
5. После каждого epic — `git commit -m "feat(<scope>): <message>"`
6. После каждого major commit — push в ветку
7. После завершения всех epics:
   - Создай `SPRINT_0_REPORT.md` в `docs/`
   - Обнови `docs/ARCHITECT_NOTES.md` с findings и observations
   - Обнови `docs/DECISIONS.md` с реальными ADR (-001 stack, -002 storage, -003 layout, -004 design system source, -005 module strategy)
   - PR / merge в `main`
   - Подготовь `OPUS_HANDOVER_SPRINT_0.md` (как у Konvey) для следующей сессии архитектора

---

## 7. Структура отчёта (`SPRINT_0_REPORT.md`)

```markdown
# Sprint 0 Report — 1C-Optimyzer Foundation

## TL;DR
[2-3 предложения: что сделано, что заработало end-to-end, ключевые observations]

## Что сделано (по эпикам)

### Epic A: Базовая инфраструктура
- [...]
- Commits: [hash...]

### Epic B: Visual identity
- [...]

[... и т.д. для всех epics ...]

## Проблемы и решения

[Какие технические проблемы встретились, как решены]

## Acceptance criteria checklist

| # | Criterion | Done? | Notes |
|---|---|---|---|
| 1 | ... | ✅ | ... |
| 19 | Real-data acceptance | ⚠️/✅/❌ | [details] |

## Открытые вопросы для архитектора

- Q1: ...
- Q2: ...

## Метрики

- Lines of code (frontend / backend): X / Y
- Tests count: Z (pytest) + W (vitest, если есть)
- Build time: ...
- App startup time: ...
- TJ archive parsing speed: ... events/sec на N MB архиве

## URLs последних коммитов

- main: <sha>
- branch: <sha>

## Следующий шаг

Sprint 1 design — архитектор начинает работу над OptimyzerQL parser, syntax highlighting, autocomplete, templates library.
```

---

## 8. Открытые вопросы которые могут возникнуть

(Эти вопросы исполнитель добавляет в QUESTIONS.md по мере появления.)

**Q1: Реальный архив ТЖ для acceptance testing.**
Где взять real-world архив? Owner возможно предоставит из своих рабочих систем или попросит у коллег. Без real-data acceptance pass Sprint 0 не закрывается.

**Q2: Размер архивов в production use cases.**
ТЖ может быть от ~100 МБ за час нагрузочной системы до многих ГБ за день. Какой target performance? Sprint 0 — без оптимизаций (закрываем correctness, не speed). Sprint 2 — performance tuning.

**Q3: Кодировка ТЖ.**
ТЖ обычно в UTF-8, но на старых системах может быть Windows-1251 или OEM. Auto-detect или ask user? Sprint 0 — assume UTF-8 с fallback warning.

**Q4: Versioning платформы 1С vs формат ТЖ.**
ТЖ-формат относительно стабилен, но events могут отличаться между 8.3.18 и 8.3.25. Какие версии платформы поддерживаем? Sprint 0 — последние 5-6 минорных (8.3.20+).

**Q5: Конфликт паролей / credentials в ТЖ.**
ТЖ может содержать SQL queries с паролями (хотя обычно `Sql` уже sanitized платформой). Полная sanitization — extra work для Sprint 0 или Sprint 2?

---

## 9. Замечания для Claude Code

- **Берегите architectural соответствие дизайну**. Дизайн в `design/opt/` — это **визуальная спецификация**. Не отклоняйтесь без явного разрешения архитектора.
- **Икл-формат для extractor** — если zip extraction отказывает на больших архивах, рассматривайте streaming через `zipfile.ZipFile.open()` для каждого внутреннего файла, не `extractall()`.
- **Не пытайтесь сразу оптимизировать парсер.** В Sprint 0 — correctness first, speed second. Если на real archive parsing >5 минут — это OK для Sprint 0.
- **DuckDB indexes — после bulk insert**, не до. Это стандартная оптимизация (CREATE TABLE → COPY/INSERT → CREATE INDEX), даёт 5-10x speedup на bulk loads.
- **Tauri sidecar bridge** — рекомендую следовать паттерну из Konvey (json-rpc-py + sidecar exe). Не изобретать своё.
- **CSS Modules vs Tailwind для production app** — используем **CSS Modules**, не Tailwind. Tailwind остался только в design preview HTML. Это **архитектурное решение** (ADR-002).
- **Никаких `style={{...}}`** inline в production code — это правило из Konvey, переносим.

---

## 10. Готов к работе

Прочти этот promt полностью. Задай любые предварительные вопросы (через QUESTIONS.md или сообщение Сергею для архитектора).

Когда вопросы прояснены — стартуй с Epic A. Удачи. Module 1 — это **первый MVP** продукта, и Sprint 0 — это его фундамент. Главное правило: соответствие дизайну + чистая архитектура. Performance / polish — потом.
