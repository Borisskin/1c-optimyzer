# Sprint 3 Report — Business Anatomy Views + AI Explainer

> **Status:** Closed
> **Branch:** `feat/sprint-3-anatomy-and-explainer`
> **Tag:** `v0.3.0-internal`
> **Дата:** 2026-05-19
> **Цель:** Превратить tool из «SQL-консоль над ТЖ» в «1С:Эксперт-в-коробке для middle-программиста 1С».

---

## TL;DR

Sprint 3 закрыт со всеми 9 phases. 268 backend tests passing (+85 vs Sprint 2 baseline 183). Real-data acceptance gates passed: Top Business Operations < 3 sec на 1.09M-events архиве, Operation Anatomy < 3 sec, rule classifier correctly классифицирует 3/3 типов synthetic deadlocks. AI explainer интегрирован с hybrid UX (rule instant + AI fire-and-forget с кешем). Покрытие курса 1С:Эксперт по Разделу 13 (Транзакционные блокировки) поднято с 30% до 75%.

Открытая площадка для follow-up: **0 TDEADLOCK / 0 DBMSSQL events в текущем production-архиве Сергея** (logcfg.xml без соответствующих filters). Phase D design + synthetic validation готов; real-data validation deadlock-схем — отдельная пост-Sprint 3 задача (см. OPUS_HANDOVER).

---

## Что фактически сделано

| Phase | Deliverable | Tests | Файлы |
|---|---|---|---|
| **0** | Discovery script + `EXTRA_JSON_FIELD_STUDY.md` | — | `backend/scripts/inspect_extra_json.py`, `docs/EXTRA_JSON_FIELD_STUDY.md` |
| **A** | `context_normalized` колонка + idempotent миграция + backfill | 17 | `tj_parser.py`, `duckdb_store.py`, `test_context_normalization.py` |
| **B** | Top Business Operations view (backend + frontend) | 5 | `sql/views.py`, `Operations.tsx`, `nav.ts` |
| **C** | Operation/Session Anatomy drill-down | 9 | `sql/anatomy.py`, `Anatomy.tsx` |
| **D** | Deadlock Anatomy по ИТС spec + synthetic fixture (3 ЦУП 2.12.3 types) | 19 | `sql/deadlock_anatomy.py`, `synthetic_tdeadlock_archive.py`, `DeadlockAnatomy.tsx` |
| **E** | Rule engine + 8 markdown rules | 22 | `explainer/{rule_loader,classifier}.py`, `explainers/*.md` |
| **F** | AI explainer (Claude API + SQLite cache) + ExplainerCard | 11 | `explainer/{claude_client,cache}.py`, `rpc/explainer_rpc.py`, `ExplainerCard.tsx` |
| **G** | Updated `FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` + ADR-022/023/024 | — | `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md`, `docs/DECISIONS.md` |
| **H** | Real-data acceptance tests + synthetic Deadlock acceptance | 4 | `test_sprint3_real_data.py` |

**Tests total:** 268 passed, 3 skipped (live AI без API key, POSIX permission test, owner-archived E2E).
**Frontend TypeScript:** clean (0 errors).
**Commits на feat-branch:** 8 atomic с conventional messages.

---

## Acceptance gates (DoD блокирующие)

| # | Criterion | Status |
|---|---|---|
| 19 | Top Business Operations < 3 sec на real archive | ✅ **passed** (1.09M events, < 3 sec) |
| 20 | Operation Anatomy < 3 sec | ✅ **passed** на топ-операции с context_normalized |
| 21 | Deadlock Anatomy works (synthetic, real-data — follow-up) | ✅ **passed** на 3 ЦУП 2.12.3 типах |
| 22 | Rule classifier 3/3 типов synthetic deadlocks | ✅ **passed** (deadlock_lock_escalation + deadlock_different_order + deadlock_single_resource fallback) |
| 23 | AI explainer < 15s uncached (skipped без API key) | ⏭️ skipped (нет ANTHROPIC_API_KEY в env Сергея пока) |
| 24 | Demo recording | ⏳ pending — записывает Сергей после merge |

---

## Phase D Validation Status

### Реальный production-архив (Phase 0 discovery)

Запуск `backend/scripts/inspect_extra_json.py` на самом крупном архиве (`99cabbc...duckdb`, 548 MB DuckDB / 12 GB original, 1,090,995 events) показал распределение:

| event_type | count | % |
|---|---:|---:|
| `CALL` | 438,868 | 40.23% |
| `Context` | 302,137 | 27.69% |
| `SRVC` | 214,548 | 19.67% |
| `SCALL` | 93,489 | 8.57% |
| `CONN` | 14,530 | 1.33% |
| `VRSREQUEST` | 6,479 | 0.59% |
| `VRSRESPONSE` | 6,175 | 0.57% |
| `SESN` | 5,470 | 0.50% |
| `VRSCACHE` | 3,078 | 0.28% |
| `ATTN` | 2,918 | 0.27% |
| `CLSTR` | 1,985 | 0.18% |
| `EXCPCNTX` | 450 | 0.04% |
| **`EXCP`** | **299** | **0.03%** |
| `HASP` | 262 | 0.02% |
| **`TLOCK`** | **142** | **0.01%** |
| **`TDEADLOCK`** | **0** | **0%** |
| **`DBMSSQL`** | **0** | **0%** |
| другие | < 0.01% | |

**Архив — client-server protocol trace без СУБД-слоя.** logcfg.xml собран без `<event><eq property="name" value="DBMSSQL"/></event>` и `<event><eq property="name" value="TDEADLOCK"/></event>` filters.

### Что валидировано на real data

- ✅ **Phase A** — `normalize_context` на 532K CALL+SCALL events с context.
- ✅ **Phase B** — Top Business Operations < 3 sec на 1.09M events.
- ✅ **Phase C** — Operation Anatomy < 3 sec на популярной операции.
- ✅ **Phase E** — TLOCK / EXCP rules валидированы на 142 TLOCK + 299 EXCP real events.
- ⚠️ **Phase F (AI explainer)** — code-path валидирован, live API call в env без API key пока skipped.

### Что валидировано на synthetic fixture

- ✅ **Phase D Deadlock Anatomy** — 3 типа ЦУП 2.12.3 (lock escalation / different order / single resource) распарсиваются correctly.
- ✅ **Phase E deadlock rules** — все 3 типа классифицируются разными правилами.

### Что НЕ валидировано (follow-up)

- ❌ **Phase D real-data Deadlock Anatomy** — нет TDEADLOCK events в архиве. См. OPUS_HANDOVER_SPRINT_3.md → «Phase D real-data validation pass».

---

## Покрытие курса 1С:Эксперт (по разделам)

Полный mapping — в [`docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md`](./FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md). Дельты Sprint 3:

| Раздел курса | До Sprint 3 | После Sprint 3 |
|---|---:|---:|
| Раздел 4 «Когда уже тормозит» | 70% | **90%** ↑ |
| Раздел 13 «Транзакционные блокировки» ⭐ | 30% | **75%** ↑ (synthetic-validated, real-data validation в follow-up) |
| Раздел 3 «Apdex» (частично через `context_normalized` group by) | 0% | **40%** ↑ |
| Раздел 6 «ТЖ» | 60% | **75%** ↑ |

**Итоговое целевое покрытие Module 1:** ~40-45% программы (analytical/diagnostic part). Sprint 3 завёл нас в верхнюю часть этого диапазона по всему обещанному scope.

---

## Архитектурные решения

- **ADR-022** — Курс 1С:Эксперт как canonical roadmap reference.
- **ADR-023** — Explainer hybrid architecture (rule + AI параллельно с кешем).
- **ADR-024** — Backend-only AI calls (API ключ никогда не уходит в frontend).

Все три в [`docs/DECISIONS.md`](./DECISIONS.md).

---

## Что не сделано / отложено

| Item | Reason | Куда |
|---|---|---|
| URL routing `/anatomy/operation/<x>` (Q3 ответ Opus был «shareable URL») | Sprint 2 не использовал React Router; refactor — отдельная задача | OPUS_HANDOVER → Sprint 4+ |
| Phase D real-data validation | 0 TDEADLOCK в текущем архиве | OPUS_HANDOVER → когда появится архив с deadlocks |
| Lock Wait Anatomy view (по ЦУП 2.13.2) | 142 TLOCK в архиве позволяют, но scope-out для Sprint 3 | OPUS_HANDOVER → Sprint 5+ кандидат |
| N-archive comparison (N>2) | Direction D отложен (см. Field Report Q5) | Sprint 4 или позже |
| Demo recording | Записывает Сергей после merge на main | DoD #24 pending |

---

## Полезные команды

```powershell
# Запуск
.\start.bat

# Discovery на текущем архиве
backend\.venv\Scripts\python.exe -X utf8 backend\scripts\inspect_extra_json.py --top-types 25 --max-events-per-type 50000

# Все backend tests
backend\.venv\Scripts\python.exe -m pytest backend\tests --ignore=backend\tests\test_sprint1_real_folder.py -q

# Только Sprint 3 acceptance
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_sprint3_real_data.py -v
```

---

## Diff vs Sprint 2 closure

- Schema: +1 колонка `context_normalized` + 1 индекс. Backward-compatible через `_migrate_context_normalized` (PRAGMA-проверка + idempotent UPDATE).
- 19 events distinct types в архиве, NONE из ожидаемых `TDEADLOCK/DBMSSQL` присутствуют. Это **первое открытие Sprint 3** — оно повлияло на Phase D approach.
- Backend ingest pipeline: новые ingest'ы будут писать `context_normalized` напрямую (через `parse_log_file_streaming` → `interpret`).
- Frontend: 3 новых screen + 1 explainer component + 5 новых RPC clients. TypeScript clean.

---

**Prepared by:** Claude Code (Sprint 3 implementation session)
**For:** Claude Opus 4.7 (architect) + Сергей (product owner)
