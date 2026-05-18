# Opus Handover — Sprint 0 → Sprint 1 (1C-Optimyzer)

> Передача состояния проекта в следующую сессию архитектора (Claude Opus 4.7).
> Сергей открывает эту сессию вместе с архитектором, чтобы спланировать Sprint 1.

---

## Краткий статус

**Sprint 0 = foundation Module 1 — закрыт по коду на 16/19 criteria.** Open:
- Manual smoke test `npm run tauri dev` (требует `npm install` + `cargo build`, которые не запускались в Sprint 0).
- Real-data acceptance gate (`test_real_archive_acceptance`) — blocked на Q1 (owner-provided fixture).

**Что заработало:**
- Backend Python sidecar (JSON-RPC 2.0 over stdio) — 29 тестов passing.
- TJ-парсер обрабатывает CALL/DBMSSQL/EXCP/TLOCK/TDEADLOCK + unknown types.
- DuckDB store с 3 preset queries (first_100/longest/deadlocks).
- Tauri 2 frontend с дизайн-системой, chrome (TopBar/Sidebar/StatusBar), Command Palette, drag-and-drop, OQL Console screen.

**Что НЕ заработало (вне scope Sprint 0):**
- OQL DSL parser/compiler (Sprint 1).
- CodeMirror editor (Sprint 1).
- Chart/Timeline result views (Sprint 2).

---

## Что архитектор должен прочитать первым делом

1. `docs/SPRINT_0_REPORT.md` — полный отчёт по эпикам, метрики, проблемы.
2. `docs/DECISIONS.md` — 8 ADR-ов, которые задают стек, стратегию, design rules.
3. `docs/QUESTIONS.md` — Q1 (real archive — blocking), Q2–Q5 (платформа/кодировка/размер/sanitization).
4. `docs/ARCHITECT_NOTES.md` — observations + open arch вопросы.

---

## Sprint 1 scope (предлагаемый — для уточнения архитектором)

Главная цель Sprint 1 — **OptimyzerQL DSL: parser + compiler в SQL → DuckDB**.

### Epics предположительные

- **OQL parser.** EBNF/PEG grammar (`events | where ... | summarize ... by ...`). Имплементация на Python через `lark` или ручной recursive-descent. AST + validation.
- **OQL compiler → SQL.** Маппинг AST → DuckDB SQL. Каждый pipe-оператор (`where`, `project`, `order by`, `summarize`, `join`, `timerange`, `limit`, `render`) — отдельный traversal step.
- **CodeMirror 6 editor.** Замена `<textarea>` на CodeMirror с custom language: syntax highlighting (keywords/operators/sources), bracket matching, line numbers, gutter с error markers.
- **Autocomplete.** Trigger на Tab/Ctrl+Space: sources, operators, schema fields (columns events table, dynamically — после `load_archive`).
- **Templates library.** Bottom bar в OQL Console — кликабельные templates вместо preset buttons. Файлы `.oql` в `frontend/src/templates/`.
- **Saved queries.** SQLite table `saved_queries` + RPC методы. UI — modal "Save Query" + "Open Saved" list.
- **Validate RPC.** Метод `validate_oql_query(query) → {valid, errors[]}` без запуска (для inline-error markers).

### Acceptance gate Sprint 1

Real-data acceptance из Sprint 0 — **обязателен закрыть в Sprint 1** (Q1 на главном пути).

### Risks / unknowns для Sprint 1

- Performance: компилированный SQL на больших архивах (10+ ГБ) может быть медленным. DuckDB native engine хорошо оптимизирован, но первый бенчмарк нужен.
- `join code_graph on procedure_name` в OQL — source `code_graph` пока не существует. Sprint 1 — заглушка с пустыми результатами; Sprint 3 — реальный парсер BSL.
- `metrics` source — server agents (Module 2). В Sprint 1 — заглушка.

---

## Что архитектор уже знает про проект (не нужно re-explain)

- **Стек:** Tauri 2 + React/TS + Python sidecar + DuckDB + SQLite. ADR-001.
- **Модульная стратегия:** Module 1 = OQL Standalone, Module 2+ = real-time agents. ADR-005.
- **CSS Modules** (не Tailwind) в production app. ADR-002.
- **Светлая тема, 1280px min-width.** ADR-004.
- **Conventional commits, русский в docs/code-comments, английский в identifiers.** ADR-007, ADR-008.
- **Real-data testing — mandatory acceptance gate** для каждого спринта. Sprint 0 закрылся с pending — Sprint 1 должен закрыть.

---

## Структура репо (для быстрой ориентации)

```
1c-optimyzer/
├── README.md
├── design/
│   ├── 1c-optimyzer-design-v1.html       # shell дизайн-концепта
│   ├── opt/                              # 19 JSX-файлов: screens + shared chrome
│   └── screenshots/                      # 3 PNG
├── docs/
│   ├── DECISIONS.md                      # ADR-001..ADR-008
│   ├── QUESTIONS.md                      # Q1..Q5
│   ├── ARCHITECT_NOTES.md
│   ├── SPRINT_0_REPORT.md
│   └── OPUS_HANDOVER_SPRINT_0.md         # этот файл
├── backend/                              # Python sidecar
│   ├── pyproject.toml
│   ├── src/optimyzer_backend/
│   │   ├── __main__.py                   # JSON-RPC entry
│   │   ├── rpc/{dispatcher,handlers}.py
│   │   ├── parsers/tj_parser.py          # ⭐ главный — Sprint 1 расширяет
│   │   ├── storage/{duckdb,sqlite}_store.py
│   │   ├── archive/extractor.py
│   │   └── models/{events,archive}.py
│   └── tests/                            # 29 tests + 1 skipped (real-archive)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts, tsconfig.json
│   ├── index.html
│   ├── src-tauri/                        # Tauri 2 shell + sidecar bridge
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── api/backend.ts                # typed RPC wrapper
│       ├── store/appStore.ts             # Zustand
│       ├── styles/optimyzer-design.css   # design tokens
│       ├── components/
│       │   ├── icons/Icon.tsx            # 53 SVG
│       │   ├── primitives/               # Badge, Panel, KPI, Tabs, Th/Td, SQLBlock
│       │   ├── charts/Charts.tsx
│       │   ├── chrome/{TopBar,Sidebar,StatusBar}.{tsx,module.css} + nav.ts
│       │   ├── overlays/{CommandPalette,DropZone,Toasts}.{tsx,module.css}
│       │   └── screens/OQLConsole/OQLConsole.{tsx,module.css}
└── scripts/{setup-backend,dev,test-backend,check-env}.ps1
```

---

## Git state

- Ветка: `feat/sprint-0-foundation`
- Базовая ветка: `main`
- Последний коммит: `0734bc9 chore: dev scripts...`
- 9 коммитов сверх main, conventional commits, atomic-ish (несколько объединились из-за PowerShell heredoc — содержание корректно).
- PR в GitHub откроем после ручного smoke test.

---

## Готов к Sprint 1

Архитектор может приступать к проектированию Sprint 1 promt'а сразу после прочтения этой передачи. Никаких blocking-questions для старта дизайна нет — Q1 (real archive) нужен для закрытия Sprint 1 gate, но дизайн OQL parser'а можно начинать без него.
