# 1C-Optimyzer

**Анализ архивов технологического журнала 1С — performance investigation workbench.**

> ![Infostart](docs/assets/infostart.svg)
>
> Публикация на Infostart: [infostart.ru/public/2733405](https://infostart.ru/public/2733405/)

## Status

🚀 **Active development.**

## Что работает

- **Drag-and-drop папки** с логами ТЖ → автоматический парсинг
- **6 типов process roles** (rphost, rmngr, ragent, 1cv8c, 1cv8s, 1cv8) с case-insensitive matching
- **Encoding auto-detect** (UTF-8 BOM / plain / cp1251 / cp866)
- **Streaming parser** для архивов произвольного размера (verified на 12 GiB)
- **DuckDB storage** с pyarrow Appender (production-grade bulk insert)
- **SQL Console** — raw SQL поверх событий с syntax highlighting, autocomplete по schema, read-only execution (Sprint 2)
- **6 Pre-built Views** — Slow Queries / Locks Timeline / Process Roles / Duration Histogram / Errors Feed / Activity Heatmap (Sprint 2)
- **Cross-filtering** — клик в одном view применяется ко всем (Sprint 2)
- **Multi-archive Comparison** — side-by-side diff baseline vs compared с regression detection (Sprint 2)
- **SQL Templates library** — 13 готовых запросов по категориям (Sprint 2)
- **Export** — CSV / TSV / JSON из каждого view (Sprint 2)
- **Saved queries** через SQLite
- **Archive management** — список загруженных архивов с per-item и bulk удалением
- **Live progress UI** — animated event counter (не замирает на больших файлах)
- **Full ru-RU localization**
- **Query Analyzer** — SDBL анализ через bsl-language-server (19 диагностик) + sqlglot T-SQL antipatterns + structured AI explanation на русском (Sprint 6, `Ctrl+Q`)
- **Plan Analyzer** — универсальный для **MS SQL Server и PostgreSQL**. Для MSSQL: PerformanceStudio CLI (30 правил) + SSMS-style визуализация (html-query-plan) + AI объяснение. Для PostgreSQL: syntax-highlighted EXPLAIN TEXT + AI prompt со знанием 1С-PG специфики (`enable_mergejoin=off`, `mchar/mvarchar`, lowercase naming) + opt-in интерактивная визуализация через [pev2](https://github.com/dalibo/pev2) (требует read-only PG connection в Settings, password в OS keychain). **SQL Antipatterns engine** обнаруживает 9 T-SQL + 15 PG-specific паттернов (`OFFSET без LIMIT`, `ILIKE без trgm`, `mchar vs text`, `missing WHERE on UPDATE/DELETE`...) с 1С-context awareness через regex heuristic. Автоматическое определение движка по событию (DBMSSQL → MSSQL, DBPOSTGRS → PostgreSQL). Три пути импорта: файл/paste/автоэкстракт из ТЖ архива (`<plansql/>` в logcfg.xml). Sprint 7-8, `Ctrl+P`.

## Architecture

- **Frontend:** Tauri 2 + React 18 + TypeScript + CodeMirror 6 + Recharts
- **Backend:** Python sidecar (JSON-RPC over stdio) + DuckDB read-only executor + sqlparse validator
- **Storage:** DuckDB (per-archive analytical store) + SQLite (app metadata)
- **Test coverage:** 183 unit tests + 15 env-gated acceptance tests

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

## Keyboard shortcuts

- `Ctrl/Cmd + K` — Command Palette
- `Ctrl/Cmd + 1..8` — quick switch между screens (SQL Console / Slow Queries / Locks / Process Roles / Duration / Errors / Activity / Comparison)
- `Ctrl/Cmd + Enter` в SQL editor — выполнить запрос

## Documentation

- [`docs/DECISIONS.md`](docs/DECISIONS.md) — архитектурные решения (ADR)
- [`docs/user-guide/`](docs/user-guide/) — руководство пользователя (TJ Config Builder, поддержка PostgreSQL)
- [`docs/configuration/pg-connection-setup.md`](docs/configuration/pg-connection-setup.md) — настройка подключения к PostgreSQL

## Команда

- **Owner & domain expert:** Сергей
- **Architect:** Claude Opus 4.7
- **Executor:** Claude Code

## Лицензия

Source-available. Код доступен для ознакомления. Коммерческое использование без разрешения автора запрещено. Для получения лицензии: nazarov.soft@gmail.com

---
Сергей Назаров, телеграм: @giottas
© 2024-2026 Sergei Nazarov
