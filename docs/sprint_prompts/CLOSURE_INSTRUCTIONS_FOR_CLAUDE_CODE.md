# Closure Instructions — Sprint 1 finalization + Module 1 freeze

> **Задача:** формальная финализация Sprint 1 + установка проекта в maintenance mode перед pivot к следующему направлению.

---

## Контекст

Sprint 1 завершён 31/31 (включая 5/5 acceptance gate на 12 GiB). Module 1 (OptimyzerQL Standalone Tool) функционально полный — drag-drop папки, OQL DSL, CodeMirror, real-data verified.

По стратегическому решению владельца + архитектора, **активная разработка приостанавливается**. Module 2+ (real-time agents, central server, AI Co-pilot, и т.д.) **не реализуется** в обозримом периоде.

Полное обоснование — в `docs/PROJECT_CLOSURE_MODULE_1.md` (создаётся в этой задаче).

---

## Tasks

### 1. Положить PROJECT_CLOSURE_MODULE_1.md в репо

Архитектор передаёт через Сергея файл `PROJECT_CLOSURE_MODULE_1.md`. Положи его в:

```
D:\1C-Optimyzer\1c-optimyzer\docs\PROJECT_CLOSURE_MODULE_1.md
```

Не модифицируй содержимое.

### 2. Smoke test перед merge

Перед merge PR в `main` убедись что приложение запускается:

```powershell
.\start.bat
```

Окно должно открыться, OQL Console должна отрисоваться, drag-drop папки должен принимать (или хотя бы не падать с error). Если есть критический бaгue который ломает запуск — зафиксируй в `KNOWN_ISSUES.md`, но всё равно продолжай closure (issues могут быть исправлены через GitHub issues позже).

### 3. Merge PR в `main`

```bash
git checkout main
git pull
git merge feat/sprint-1-ingest-and-oql
# Resolve conflicts если есть (не должно быть)
git push origin main
```

Если есть PR создан через `gh pr create` — можно через `gh pr merge --squash` либо `gh pr merge --merge` (на твоё усмотрение, squash чище но теряется атомарная история коммитов).

### 4. Создать tag `v0.1.0-internal`

```bash
git tag -a v0.1.0-internal -m "Module 1: OptimyzerQL Standalone Tool — feature complete

Features:
- Folder ingestion with streaming parser (real-data verified on 12 GiB)
- OptimyzerQL DSL with CodeMirror editor
- Templates library (8 presets)
- Saved queries via SQLite
- Full ru-RU localization
- 197 unit tests + 5 acceptance tests passing

Status: maintenance mode (active development paused 2026-05-18)
See docs/PROJECT_CLOSURE_MODULE_1.md for details."

git push origin v0.1.0-internal
```

### 5. Обновить README.md

Замени содержимое `README.md` в корне репо на следующее (адаптируй детали по факту):

```markdown
# 1C-Optimyzer

**Анализ архивов технологического журнала 1С через специализированный DSL.**

## Status

⏸️ **Active development paused** (2026-05-18). Project в maintenance mode.

Module 1 (OptimyzerQL Standalone Tool) функционально завершён — рабочий desktop-инструмент с verified parsing 12 GiB real-world архивов. Module 2+ (real-time monitoring, AI Co-pilot, и др.) отложены indefinitely по стратегическим причинам.

Подробное обоснование статуса — в [`docs/PROJECT_CLOSURE_MODULE_1.md`](docs/PROJECT_CLOSURE_MODULE_1.md).

## Что работает

- **Drag-and-drop папки** с логами ТЖ → автоматический парсинг
- **6 типов process roles** (rphost, rmngr, ragent, 1cv8c, 1cv8s, 1cv8) с case-insensitive matching
- **Encoding auto-detect** (UTF-8 BOM / plain / cp1251 / cp866)
- **Streaming parser** для архивов произвольного размера (verified на 12 GiB)
- **DuckDB storage** с pyarrow Appender (production-grade bulk insert)
- **OptimyzerQL DSL** — declarative query language для аналитических запросов поверх ТЖ
- **CodeMirror 6 editor** с syntax highlighting + autocomplete + linter
- **Templates library** — 8 предустановленных запросов
- **Saved queries** через SQLite
- **Full ru-RU localization**

## Architecture

- **Frontend:** Tauri 2 + React 18 + TypeScript + CodeMirror 6
- **Backend:** Python sidecar (JSON-RPC over stdio) с Lark grammar parser
- **Storage:** DuckDB (per-archive analytical store) + SQLite (app metadata)
- **Test coverage:** 197 unit tests + 5 acceptance tests (12 GiB real-data verified)

## Setup для разработки

См. [`docs/SETUP.md`](docs/SETUP.md) (если создан) или:

```powershell
# Backend dependencies
pwsh scripts/setup-backend.ps1

# Frontend dependencies
cd frontend
npm install
cd src-tauri
cargo build

# Run dev mode
cd ..\..
.\start.bat
```

## Maintenance policy

См. [`docs/PROJECT_CLOSURE_MODULE_1.md`](docs/PROJECT_CLOSURE_MODULE_1.md) section 4.

Кратко:
- Bug fixes — accepted, best-effort response
- Security issues — приоритетно (~дни response)
- Feature requests — accepted, **not implemented** в обозримом периоде
- Critical compatibility issues — устраняются если занимают <1 day

## Documentation

- [`docs/PROJECT_CLOSURE_MODULE_1.md`](docs/PROJECT_CLOSURE_MODULE_1.md) — текущий статус проекта
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — все архитектурные решения (ADR-001..014)
- [`docs/SPRINT_0_REPORT.md`](docs/SPRINT_0_REPORT.md), [`docs/SPRINT_1_REPORT.md`](docs/SPRINT_1_REPORT.md) — детальные отчёты по спринтам
- [`docs/ARCHITECT_NOTES.md`](docs/ARCHITECT_NOTES.md) — observations архитектора
- [`design/`](design/) — visual design specification (18 screens, premium UI system)

## Команда

- **Owner & domain expert:** Сергей
- **Architect:** Claude Opus 4.7
- **Executor:** Claude Code

## License

TBD (см. PROJECT_CLOSURE_MODULE_1.md раздел 4 "Open source status")

---

© 2026 anymasoft. All rights reserved (pending license decision).
```

### 6. Add `KNOWN_ISSUES.md` если есть

Если после smoke test обнаружились bugs — создай `docs/KNOWN_ISSUES.md` со списком. Формат:

```markdown
# Known Issues

> Bugs выявленные после закрытия Sprint 1, требующие future fix.

## Open

### [ISSUE-001] Краткое описание
- **Severity:** low / medium / high
- **Description:** что именно не работает
- **Repro:** шаги воспроизведения
- **Workaround:** временное решение если есть
```

### 7. Финальный commit

```bash
git add docs/PROJECT_CLOSURE_MODULE_1.md README.md docs/KNOWN_ISSUES.md
git commit -m "docs: project closure - Module 1 feature complete, maintenance mode

- Add PROJECT_CLOSURE_MODULE_1.md with formal closure document
- Update README.md with paused status + maintenance policy
- Tag v0.1.0-internal as semantic versioning marker
- Active development of Module 2+ paused per founder decision

See docs/PROJECT_CLOSURE_MODULE_1.md for full reasoning."

git push origin main
```

### 8. Финальный status message для архитектора

После завершения — пришли краткое подтверждение:

```
✅ Sprint 1 finalized. Module 1 closure complete.

- PR смержен в main
- Tag v0.1.0-internal создан и pushed
- PROJECT_CLOSURE_MODULE_1.md размещён в docs/
- README обновлён с paused status
- [Known issues: N items / нет issues после smoke test]

Repo: github.com/anymasoft/1c-optimyzer
Tag: https://github.com/anymasoft/1c-optimyzer/releases/tag/v0.1.0-internal

Готов к новому проекту. Жду pre-prompt от архитектора.
```

---

## Что НЕ делаем в этой задаче

- НЕ начинаем новые features
- НЕ исправляем performance (~1 МБ/сек остаётся baseline)
- НЕ пишем contentmarketing (Хабр статью и т.д.)
- НЕ создаём .msi installer
- НЕ настраиваем CI/CD
- НЕ изменяем license — решение откладывается

Задача = **administrative closure**, не development.

---

## После закрытия

Архитектор подготовит **pre-prompt для нового проекта** — AI Product Analytics. Это будет:
- Новый GitHub repo
- Новая working directory
- Discovery-фаза перед Sprint 0 (similar to inspect_logs для 1C-Optimyzer)
- Связи с существующим ГосЛог продуктом для первого use case

1C-Optimyzer repo остаётся paused, но **доступен** для maintenance issues если появятся.

Удачи с финализацией.
