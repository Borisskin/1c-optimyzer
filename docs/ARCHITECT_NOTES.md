# Architect Notes — 1C-Optimyzer

> Observations и hypotheses архитектора между сессиями. Не для исполнителя, не ADR, не QUESTIONS — наблюдения по проекту, помогающие continuity между сессиями.

---

## После Sprint 0 (2026-05-18)

### Что закрыто

Foundation Module 1 (OptimyzerQL Standalone Tool) — заложена полная инфраструктура:

- **Backend (Python):** JSON-RPC dispatcher, TJ parser (lexer + interpreter + SQL normalization), zip extractor с защитой от zip-slip, DuckDB store (schema + 5 indexes + 3 preset queries), SQLite metadata store, 8 RPC методов. Все 29 unit/integration tests зелёные.
- **Frontend (Tauri 2 + React/TS):** Tauri-Rust shell с child-process sidecar bridge через stdio, JSON-RPC wrapper, Zustand store, 50+ icons, 13 UI primitives, 5 chart components, TopBar/Sidebar/StatusBar, Command Palette (Cmd+K), drag-and-drop, toasts, OQL Console screen (read-only editor + 3 preset buttons + Table/Raw views).
- **Дизайн-соответствие:** все 18 экранов видны в Sidebar (только oql enabled, остальные disabled с tooltip "Module N+1"); chrome 1:1 с дизайном; OQL Console — layout портирован из `design/opt/optimyzerql.jsx`.

### Что осталось open

- **Q1 (blocking для DoD #19):** реальный архив ТЖ от Сергея. Без него acceptance gate "≥95% events parsed without exceptions" не закрывается. Тест `test_real_archive_acceptance` помечен `@pytest.mark.skip` — активируется когда архив будет в `backend/tests/fixtures/real-archive/tj.zip`.
- **Manual smoke test:** `npm run tauri dev` ещё не запускался — frontend и Rust shell написаны, но `npm install` + `cargo build` не выполнялись в этой сессии. Заметка для следующей сессии: запустить, убедиться что окно открывается, sidebar/topbar/statusbar отрисованы, кнопка "Load TZ archive…" открывает диалог.
- **Vertical slice E2E:** RPC `ping` + загрузка synthetic-архива в running app — не тестировались живьём. Только unit/integration на backend.

### Архитектурные observations для следующих спринтов

1. **OQL DSL (Sprint 1) → SQL компилятор.** DuckDB native SQL — мощный target. Pipeline `events | where ... | summarize ... by ...` маппится в `SELECT ..., agg(...) FROM events WHERE ... GROUP BY ...`. Sprint 1 — parser + compiler. Сложности: timerange-операторы (`last 24h`, `between ts1 and ts2`), join к синтетическим источникам (`code_graph`, `metrics` — пока не существуют, нужны заглушки).
2. **CodeMirror в Sprint 1.** Sprint 0 — `<textarea>`. Sprint 1 нужен CodeMirror 6 с custom language для OQL: syntax highlighting (keywords, operators, sources, types), autocomplete (sources, operators, schema fields из DuckDB), error markers (от validate-RPC).
3. **Sidecar lifecycle.** Sprint 0 — sidecar запускается один раз в `setup()` и живёт всё время. Если crashed — не перезапускается. Sprint 1+ — добавить heartbeat + auto-restart.
4. **DuckDB performance.** Sprint 0 — batch insert через executemany (медленнее `Appender`, но проще). Sprint 2 — переключить на `Appender` API + parallel parsing (Python multiprocessing / Rust-side splitting).
5. **Sidebar tooltip strategy.** Сейчас disabled item показывает toast при click. Это работает, но для приватного позиционирования нужны полноценные hover tooltips с module name + 1-line описанием. Sprint 2.

### Open arch вопросы (накопленный backlog)

- Где хранить duckdb-файлы? `%APPDATA%` принят, но для архивов >5 ГБ — пользователь может хотеть выбрать диск D:\. UI для смены DB-папки в Settings — Sprint 3.
- Tauri 2 capabilities — сейчас open `core:default, dialog:default, fs:default, shell:default`. Sprint 3 — сузить, особенно fs (только read для архивов).
- Bundling sidecar exe (PyInstaller) — Sprint 3. Не тривиально из-за DuckDB native binaries; нужен test на чистой Windows VM.
