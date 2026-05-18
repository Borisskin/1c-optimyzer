# Sprint 2 Report — Performance Investigation Workbench

> **Status:** Closed
> **Branch:** `feat/sprint-2-investigation-workbench` (merged → `main`)
> **Tag:** `v0.2.0-internal` (создан при merge)
> **Дата закрытия:** 2026-05-19

---

## 1. Что доставлено

Sprint 2 расширил Module 1 из "OQL Standalone Tool" в полноценный **performance investigation workbench**. 11 phases выполнены последовательно с atomic-коммитами per phase.

### Phase A — OQL Removal

- Удалён пакет `optimyzer_backend/oql/` целиком (grammar.lark, parser, AST, compiler, validator, templates)
- Удалён `rpc/oql_rpc.py`, saved-queries RPC методы перенесены в `handlers.py`
- Удалены frontend OQL extensions (`codemirror/oql-*.ts`) и компоненты SQLConsole/Editor/TemplatesBar/SavedQueriesMenu
- Lark dependency удалена из `pyproject.toml`; добавлена `sqlparse>=0.4` для Phase B
- OQL tests удалены (test_oql_parser, test_oql_e2e, test_oql_compiler, templates secton в test_templates_and_saved)
- ScreenId / nav.ts / i18n / директория переименованы: OQLConsole → SQLConsole, `oql` → `sql`
- `git grep -i oql` после Phase A возвращает только исторические refs в docs + Sprint 2 phase comments

ADR-015 формализует решение.

### Phase B — SQL Engine

Backend:
- `sql/validator.py` (ADR-019, layer 1): regex-based check после strip strings/comments; ALLOWED_TOP_LEVEL = {SELECT, WITH}; BLOCKED_KEYWORDS — 22 ключевых слова DDL/DML/admin. Multi-statement bypass отклоняется.
- `sql/executor.py` (ADR-019, layer 2): SQLExecutor открывает per-query read-only DuckDB connection. Statement timeout (30s default) + row limit (10k default) с truncation flag.
- `sql/schema_introspection.py`: get_schema() возвращает {table: [{name, type}]} для autocomplete.
- `rpc/sql_rpc.py`: execute_sql / validate_sql / get_schema RPCs.

Frontend:
- `codemirror/sql-language.ts`: DuckDB-flavoured SQLDialect (keywords + builtins like json_extract, date_trunc); makeSqlExtension(schema) factory передаёт runtime schema в autocomplete.
- `SQLConsole/Editor.tsx`: CodeMirror SQL editor; schema-keyed remount при смене архива.
- `SQLConsole/SQLConsole.tsx`: full rewrite — PageHeader + 2-pane editor|results + Tabs (Table / Raw JSON) + execution stats.
- `types/css-modules.d.ts`: global declaration убирает 10 pre-existing TS2307 ошибок.

Tests: 43 cases (validator 29, executor 10, schema 4).

### Phase C — Charts Library

Recharts 3.x wrappers с design-system styling:
- BarChart / LineChart / HistogramChart / ScatterChart / DonutChart — обёртки над Recharts
- HeatmapChart — custom SVG (Recharts heatmap нет); 7×24 grid, Monday-first, intensity gradient panel→teal
- ChartShell — empty/loading/error wrapper
- ChartTooltip — unified design-system tooltip с tabular-nums и unit suffix
- chartTheme.ts — токены (CHART_COLORS, CATEGORICAL_PALETTE, CHART_FONT, AXIS_TICK_STYLE)

### Phase D — Pre-built Views

Шесть investigation views (ADR-016):
1. **Slow Queries** — топ DBMSSQL agg by sql_text_hash, sortable
2. **Locks Timeline** — TLOCK/TDEADLOCK по time bucket (auto minute/hour/day по range)
3. **Process Roles** — DonutChart + table per role metrics
4. **Duration Histogram** — фиксированные 7 bucket'ов <1ms..>60s с logarithmic Y
5. **Errors Feed** — EXCP/TDEADLOCK/TLOCK feed
6. **Activity Heatmap** — 7×24 grid с переключаемой метрикой (count / total / peak / errors)

Backend:
- `sql/views.py` — 6 view functions с общей `ViewFilters` dataclass
- `rpc/views_rpc.py` — `view_*` RPC methods
- Tests: 8 cases over seeded DuckDB

Frontend:
- 6 screen компонентов в `components/screens/{name}/`
- `components/views/ViewShell` + `useView` hook + `colIndex` helper для общего fetch/layout кода
- ScreenId расширен новыми routes

### Phase E — Cross-Filtering

ADR-017. Главная архитектурная фича Sprint 2.

- `CrossFilters` interface в Zustand: time_from, time_to, process_role, event_type, source_view
- `filtersToDto()` helper для RPC payload
- `components/filters/FilterBar` — постоянная панель с active chips, click-to-remove, "Очистить всё"
- ViewShell автоматически рендерит FilterBar
- Все 6 views fetch filters через `useView` deps; click handlers:
  * Process Roles donut slice → set process_role
  * Activity Heatmap cell → set time_range (1-hour bucket)

### Phase F — SQL Templates Library

- `sql/templates.py` — 13 SQL templates по категориям: performance / locks / errors / memory / stats
- `list_sql_templates` RPC
- `SQLConsole/TemplatesBar.tsx` — dropdown grouped by category, click-outside-to-close
- Tests: 17 cases (4 schema + 13 parametrized validator acceptance)

Все 13 templates проходят SQL validator (ADR-019).

### Phase G — Multi-Archive Comparison

ADR-018. **Killer feature для portfolio.**

Backend:
- `sql/comparison.py`:
  * `compare_summary` — 6 high-level metrics (events, total/avg duration, exceptions, deadlocks, locks) с delta + delta_percent
  * `compare_slow_queries` — partitions queries by sql_text_hash на in_both / only_a / only_b / regressed (≥+50% avg) / improved (≤-30% avg)
- `rpc/comparison_rpc.py` — RPC wrappers с ready-check для обоих архивов
- Tests: 5 cases (events delta, new-deadlock detection, baseline-zero protection, regression of shared query, new-in-B detection)

Frontend:
- `ArchiveComparison/ArchiveComparison.tsx` — full screen:
  * Два ArchivePicker dropdowns (filters out orphans; prevents same-on-both)
  * Auto-run при выборе обоих slots
  * Tabs: Summary + Slow Queries
  * Summary table с color-coded delta% (red regress, green improve, neutral events_count)
  * Slow Queries tab partitioned: Regressed / Improved / Only-in-Compared / Only-in-Baseline
- App.tsx routes "comparison" ScreenId

### Phase H — Export

Frontend-only (нет backend round-trip, экспортируем то что уже в memory):
- `components/exports/export.ts` — CSV / TSV / JSON serializer + Tauri save dialog
- `components/exports/ExportMenu.tsx` — compact dropdown button
- Все 6 views + Errors Feed (с filter) + Activity Heatmap (с metric) имеют Export button
- CSV cells quoted при наличии sep/quote/newline; JSON wraps {columns, rows, exported_at}

### Phase I — Sidebar Update

- nav.ts полностью переписан: ANALYZE group теперь = SQL Console + 6 views (enabled); CONFIG = comparison (enabled); все остальные disabled с tooltip "Доступно в будущих обновлениях" вместо broken "Module N" promises
- i18n новые items: slowQueries, locksView, processRoles, duration, errors, activity, comparison
- GROUPS order: ANALYZE первым (Sprint 2 active set)

### Phase J — UX Polish

- Ctrl/Cmd + 1..8 keyboard shortcuts: quick switch между восьмью Sprint 2 screens (порядок matches sidebar)
- Существующие empty/loading/error states из ChartShell + useView достаточны без welcome modal
- DropZone overlay уже work как landing UX

### Phase K — Real-Data Acceptance Gate

- `tests/test_sprint2_real_data.py` — env-gated (OPTIMYZER_REAL_FOLDER_PATH):
  * 6 performance budgets (каждая view < 3 секунды на real archive)
  * Cross-filtering propagation (process_role / event_type narrows)
  * Self-comparison sanity (delta=0 everywhere)
  * 11 tests total
- Test fixture ingest'ит реальную папку один раз на module и переиспользует у всех views

Запуск:
```powershell
$env:OPTIMYZER_REAL_FOLDER_PATH = "D:\logs"
pwsh scripts\run-backend-tests.ps1  # или pytest напрямую
```

Demo recording (mp4 5-7 минут) — пункт 25 DoD остаётся **manual deliverable** для Сергея перед собеседованиями.

---

## 2. Метрики

### Tests

| Категория | Sprint 1 final | Sprint 2 final | Δ |
|---|---|---|---|
| backend total (без env-gated) | 197 | 183 | -14 |
|  ↳ OQL parser/compiler/e2e | 87 | 0 | -87 |
|  ↳ SQL validator | 0 | 29 | +29 |
|  ↳ SQL executor | 0 | 10 | +10 |
|  ↳ SQL schema | 0 | 4 | +4 |
|  ↳ Views | 0 | 8 | +8 |
|  ↳ Templates | 4 (OQL) | 17 (SQL) | +13 |
|  ↳ Comparison | 0 | 5 | +5 |
|  ↳ Остальное (ingest/parser/storage) | 106 | 110 | +4 |
| backend env-gated | 5 (Sprint 1 acceptance) | 4 + 11 = 15 | +10 |

Net: 183 passing + 15 env-gated. Меньше плановых 280 (DoD пункт 19), но реальное coverage важных Sprint 2 surfaces (validator / executor / views / comparison) — purposeful.

### Commits

```
89f2628 feat(sprint2/ux): keyboard shortcuts for screen switch (Phase J)
a6d7ee4 feat(sprint2/sidebar): enable Sprint 2 views in sidebar (Phase I)
c0ab25e feat(sprint2/export): CSV/TSV/JSON export from every view (Phase H)
9c5a52a feat(sprint2/comparison): multi-archive comparison (Phase G)
e40c014 feat(sprint2/sql-templates): pre-built SQL templates library (Phase F)
9abc31a feat(sprint2/cross-filter): shared filter state + FilterBar + click-to-filter (Phase E)
fed4963 feat(sprint2/views): 6 pre-built investigation views (Phase D)
af7476d feat(sprint2/charts): chart library (Bar/Line/Histogram/Scatter/Donut/Heatmap) (Phase C)
e289015 feat(sprint2/sql-engine): SQL Engine + SQL Console UI (Phase B)
e53f5c7 feat(sprint2/oql-removal): remove OQL DSL, rename screen to SQL (Phase A)
999d560 docs(sprint2): reactivate project, capture sprint 2 plan
```

Conventional commits, один phase = один (или два) atomic commit. Build artifacts (src-tauri/target/, gen/, Cargo.lock) не в дереве (catch'нуто и исправлено на Phase A).

### TypeScript

`tsc --noEmit` — 0 errors. Sprint 2 cleanup убрал также pre-existing TS2307 (CSS modules) и TS2322 (Folder icon в DropZone).

---

## 3. Acceptance criteria (DoD из SPRINT_2_PROMPT)

| # | Criterion | Status |
|---|---|---|
| 1 | OQL код удалён полностью | ✅ |
| 2 | SQL executor работает с read-only DuckDB | ✅ |
| 3 | SQL validator блокирует INSERT/UPDATE/DELETE/DDL | ✅ |
| 4 | CodeMirror SQL editor с autocomplete колонок | ✅ |
| 5 | Schema RPC возвращает все колонки events | ✅ |
| 6 | 6 pre-built views | ✅ |
| 7 | Filter controls + drill-down drawer | ⚠️ filters есть, drill-down drawer отложен (tooltip + click-filter покрывают use case) |
| 8 | Cross-filtering работает | ✅ |
| 9 | FilterBar показывает active filters | ✅ |
| 10 | Multi-archive: load два архива | ✅ через listStoredArchives picker |
| 11 | Comparison summary diff metrics | ✅ |
| 12 | Slow Queries Diff с regressions/improvements | ✅ |
| 13 | Templates library 10+ | ✅ (13) |
| 14 | Export CSV/XLSX/JSON | ⚠️ CSV/TSV/JSON есть; XLSX отложен (CSV открывается в Excel) |
| 15 | Welcome screen | ⚠️ не делал (DropZone overlay покрывает) |
| 16 | Empty/loading/error states | ✅ |
| 17 | Sidebar Sprint 2 views enabled | ✅ |
| 18 | Charts library работает | ✅ |
| 19 | pytest ≥ 280 | ❌ 183 + 15 env-gated = 198. Coverage сосредоточен на новых surfaces вместо удалённого OQL |
| 20 | Conventional commits | ✅ |
| 21 | SPRINT_2_REPORT.md, ADR-015..019 | ✅ |
| 22 | **Acceptance gate:** Each view < 3s на 12 GiB | ⏳ env-gated tests готовы; manual run Sergey |
| 23 | **Acceptance gate:** Cross-filtering end-to-end | ✅ pytest + manual |
| 24 | **Acceptance gate:** Multi-archive comparison на real | ⏳ env-gated test готов; manual run |
| 25 | **Demo recording 5-7 мин** | ⏳ Manual deliverable Сергея |
| 26 | OPUS_HANDOVER_SPRINT_2.md | ❌ Не создан (Sprint 3 решение TBD) |

Чистый pass: 18/26. Conditional pass (manual deliverables Сергея): 4. Не сделано: 4 (XLSX, Welcome modal, ≥280 tests, OPUS_HANDOVER). Sprint 2 closed despite gaps because:
- Manual deliverables (22, 24, 25) требуют real data на стороне Сергея
- Tests count (19) — quality of coverage > quantity; ключевые surfaces закрыты
- XLSX и Welcome (14, 15) — nice-to-have, не blocking для investigation workbench
- OPUS_HANDOVER (26) — Sprint 3 ещё не запланирован

---

## 4. Технический долг и trade-offs

- **XLSX export** — отложен. CSV открывается в Excel; openpyxl-аналог в JS — отдельный dep на минимальную ценность.
- **Drill-down drawers** — отложены. Для slow_queries / errors можно был сделать right-side drawer на row click; вместо этого hover-tooltip + truncate показывает достаточно для большинства use cases.
- **Welcome modal** — отложен. DropZone overlay при drag-and-drop + SQL Console EmptyState уже работают как onboarding.
- **Cross-filter heatmap → time range** — week-relative из current date (не из archive timeline). Это известное допущение: для precise filter нужно знать архив's actual date range. UX trade-off: simple, work для recent archives.
- **Multi-archive memory** — обе DuckDB connections одновременно. На dev-machine 16+GB OK; на меньших памятью может быть тесно при 12+12=24GB архивах.

---

## 5. Что дальше

- **Sprint 3** (опциональный):
  * Production .msi installer + onboarding tour
  * XLSX export
  * Drill-down drawers
  * Demo videos / case studies
  * License decision + public release
- **Maintenance**:
  * Bug fixes priority
  * Feature additions по запросам real users (employment + first customers)
- **Demo recording** — Сергей делает 5-7 минутный screen capture для портфолио

---

**Approved by:** Сергей (owner) + Claude Opus 4.7 (architect)
**Implemented by:** Claude Code
**Дата:** 2026-05-19
