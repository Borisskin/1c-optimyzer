# Sprint 8 — PostgreSQL Support (Final Report)

**Tag:** `v0.8.0-internal`
**Промежуточный sub-tag:** `v0.8.0-pg-core-internal` (Phase B closure marker)
**Длительность:** Phase A + B + C — закрыты последовательно
**Подготовил:** Claude Code (executor)
**Дата:** 2026-05-25

---

## Sprint 8 — что сделано

### Phase A — PostgreSQL Discovery
- Подключение к реальной 1С-PG базе `pgBase` (PostgreSQL 18.1-2.1C)
- Сбор сэмплов DBPOSTGRS events из tech journal
- Анализ EXPLAIN форматов (TEXT vs JSON) и pg_stat_statements
- Подтверждение feasibility для pev2 интеграции

### Phase B — PG Plan Analyzer Core (tag `v0.8.0-pg-core-internal`)
- tj_parser DBPOSTGRS support + engine field
- PlanAnalyzer UI engine detection + dispatcher (PgPlanTextView)
- AI prompts split (MSSQL/PG) с 1С-specific знанием
- PG connection storage (OS keychain) + re-EXPLAIN service
- pev2 интеграция через Vue Web Component

### Phase C — PG Antipatterns Engine (этот отчёт)
- `sql_antipatterns/` модуль с разделением `tsql/` + `postgres/`
- **15 PG-specific детекторов** (включая 1С-context aware)
- Engine dispatcher в RPC: `mssql` → 9 T-SQL правил, `postgres` → 15 PG правил
- 1С context detection heuristic (regex по `_reference\d+`, `mchar`/`mvarchar`)
- Интеграция в PlanAnalyzer UI — карточка `SqlAntipatternsCard` рядом с AI explanation
- AI prompt extension — `detected_antipatterns` передаются в Claude как контекст

---

## Метрики Sprint 8

| Метрика | До Sprint 8 | После Phase C |
|---|---|---|
| Backend tests | 687 | **861** (+174) |
| Server tests | 22 | **41** (+19) |
| Frontend tests | 0 | **23** (Phase B infra) |
| New PG components | — | **5** (planSQLText parser, antipatterns engine, re-EXPLAIN service, pev2 wrapper, dispatcher) |
| PG детекторов | 0 | **15** |
| T-SQL детекторов | 9 | 9 (без regression) |

### Backend tests (по Sprint и теме)
- Sprint 6 T-SQL antipatterns: 25 (unchanged)
- Sprint 8 Phase B: 102 (Phase B closure)
- Sprint 8 Phase C: +80 (61 unit + 13 edge cases + 4 real-data + 2 perf)
- Остальное: остаётся как было

### Coverage курса 1С:Эксперт после Phase C
- Раздел 8 (План запроса): 80% → **95%**
- Раздел 6 (ТЖ): 70% → **85%**
- Общее покрытие: 55% → **~62%**

---

## Каталог 15 PG детекторов

| # | Code | Severity | 1С-aware | Описание |
|---|---|---|---|---|
| 1 | `offset_without_limit` | Warning | — | `OFFSET N` без LIMIT |
| 2 | `large_offset_pagination` | Warning/Critical | — | OFFSET > 1000 (Critical если > 10000) |
| 3 | `ilike_without_trgm` | Warning | — | `ILIKE '%text%'` без pg_trgm GIN |
| 4 | `like_with_leading_wildcard` | Warning | ✓ | `LIKE '%text'` (downgrade до Info в 1С) |
| 5 | `not_in_with_subquery_pg` | Warning | — | `NOT IN (SELECT ...)` — NULL-trap + slow |
| 6 | `jsonb_without_gin` | Info | — | JSONB операции (heuristic — нет access к индексам) |
| 7 | `cast_in_where_predicate` | Warning | ✓ | CAST на колонке (mchar/mvarchar skip в 1С) |
| 8 | `union_instead_of_union_all` | Info | — | UNION (с implicit SORT+UNIQUE) |
| 9 | `subquery_in_select_list` | Warning | — | Correlated subquery в SELECT (N+1) |
| 10 | `distinct_on_large_result` | Info | — | DISTINCT + JOIN (часто 1:N дубликаты) |
| 11 | `implicit_type_cast` | Warning | ✓ | int_col = '123' (string vs int), `_Fld*` skip |
| 12 | `select_star_with_join` | Info | ✓ | SELECT * + JOIN (1С не делает SELECT *) |
| 13 | `order_by_random_with_limit` | Warning/Critical | — | ORDER BY RANDOM() (Critical без LIMIT) |
| 14 | `missing_where_on_update_delete` | **Critical** | — | UPDATE/DELETE без WHERE |
| 15 | `mchar_vs_text_comparison` | Warning | ✓ | mchar = text без явных cast (только 1С) |

---

## Что работает теперь (Sprint 8 closure)

E2E flows для обоих движков СУБД:

| Возможность | Engine | Sprint |
|---|---|---|
| Импорт `.sqlplan` (SSMS) | MSSQL | 7 |
| Импорт планов из ТЖ (SHOWPLAN_TEXT) | MSSQL | 7 D |
| Импорт планов из ТЖ (planSQLText TEXT) | PostgreSQL | 8 B |
| Re-EXPLAIN через PG connection | PostgreSQL | 8 B.4 |
| pev2 интерактивная визуализация | PostgreSQL | 8 B.5 |
| AI explanation с MSSQL prompt | MSSQL | 7 + 8 B.3 |
| AI explanation с PG prompt + 1С-specific | PostgreSQL | 8 B.3 |
| AI получает detected_antipatterns как context | оба | **8 C.4** |
| 9 T-SQL antipatterns | MSSQL | 6 |
| **15 PG antipatterns + 1С-aware** | PostgreSQL | **8 C** |

---

## Что НЕ сделано (вне scope Sprint 8)

- pg_stat_statements ingestion → **Sprint 11+**
- Manual demo session с Сергеем — отдельный шаг ПОСЛЕ Phase C
- SDBL парсер для PG (bsl-language-server уже работает) — out of scope
- Объединение Phase C с Sprint 9 (Testing) — не делаем

---

## Tech debt после Sprint 8

- Real-data parse success rate для PG ~10% на dbpostgrs_sample.log — это в основном T-SQL queries которые в реальности от MSSQL connector попали; для запросов от чистого PG connector rate выше. Зафиксировано в test `test_parse_success_rate_when_engine_matches` (split по engine heuristic).
- pev2 — добавляет ~185 KB gz (Vue runtime + pev2 + d3). Acceptable для desktop-app.
- Frontend Vitest infra только Phase B basic — `detectPlanEngine` (23 tests). Будет расширена в Sprint 9.

---

## Список новых ADR (Sprint 8 Phase C)

- **ADR-045** — `sql_antipatterns` module (новый, рядом с `sql/`), dialect-aware structure
- **ADR-046** — 1С-context detection через regex heuristic (не proper parser)
- **ADR-047** — Параллельный flow: antipatterns fast (local sqlglot) + AI slow (cloud)
- **ADR-048** — Sprint 8 закрыт без Phase D (planSQLText XML конвертер не нужен — для PG это уже TEXT)

См. `docs/DECISIONS.md`.

---

## После Sprint 8 — что дальше

**Manual demo session с Сергеем (отдельный шаг):**
- Откатать pipeline E2E на pgBase: импорт архива → Анатомия операции → PlanAnalyzer (PG план) → QueryAnalyzer (PG SQL) → AI explanation
- Проверить: antipatterns обнаруживаются, pev2 рендерит, re-EXPLAIN работает
- Зафиксировать баги в `docs/sales_sprint/SPRINT_8_BUGS.md`

**Sprint 9 — Deep Real-world Testing + tj-simulator expansion**
