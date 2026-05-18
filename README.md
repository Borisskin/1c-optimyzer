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
- **Live progress UI** — animated event counter (не замирает на больших файлах)
- **Archive management** — список загруженных архивов с per-item и bulk удалением
- **Full ru-RU localization**

## Architecture

- **Frontend:** Tauri 2 + React 18 + TypeScript + CodeMirror 6
- **Backend:** Python sidecar (JSON-RPC over stdio) с Lark grammar parser
- **Storage:** DuckDB (per-archive analytical store) + SQLite (app metadata)
- **Test coverage:** 197 unit tests + 5 acceptance tests (12 GiB real-data verified)

## Setup для разработки

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
