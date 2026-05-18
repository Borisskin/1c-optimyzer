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
