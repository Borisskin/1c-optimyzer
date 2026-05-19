# Opus Handover — Sprint 3 → Sprint 4

> **From:** Claude Code (Sprint 3 implementation)
> **To:** Claude Opus 4.7 (architect for Sprint 4 planning)
> **Date:** 2026-05-19
> **Status:** Sprint 3 closed, tag `v0.3.0-internal`

---

## What Sprint 3 delivered

Полный отчёт — [`docs/SPRINT_3_REPORT.md`](./SPRINT_3_REPORT.md). Кратко:

- 3 anatomy views (Top Business Operations / Operation Anatomy / Deadlock Anatomy)
- Rule-based + AI hybrid explainer (8 markdown rules, Claude API через backend-only)
- Schema migration (`context_normalized`)
- 268 backend tests passing (+85 vs Sprint 2)
- Покрытие курса 1С:Эксперт по Разделу 13 поднято с 30% → 75%

---

## Follow-up #1: Phase D real-data validation pass

**Prereq:** архив содержащий TDEADLOCK events. В текущем production-архиве Сергея 0 TDEADLOCK / 0 DBMSSQL — logcfg.xml собран без `<event><eq property="name" value="DBMSSQL"/></event>` и `<event><eq property="name" value="TDEADLOCK"/></event>` filters.

**Что нужно от Сергея:**

1. Изменить `logcfg.xml` на 1С-сервере, добавив filters для:
   - `DBMSSQL` (даст SQL Slow Queries реальные данные)
   - `TDEADLOCK` (даст real-data validation Phase D)
   - `TLOCK` (уже есть в архиве — 142 events; больший набор не помешает)
   - Опционально `EXCP` (есть 299, больше не повредит)

2. Запустить продакшен-нагрузку 10-30 минут с включённой multi-session activity, желательно с deadlock-prone сценариями (параллельное проведение Реализаций, параллельные обновления одного справочника).

3. Загрузить новый архив через UI.

**Steps когда архив будет available:**

1. Запустить `inspect_extra_json.py` на новом архиве — проверить что реальная schema `extra` JSON для TDEADLOCK совпадает с нашими гипотезами по ИТС (поля `Regions`, `WaitConnections`, `DeadlockConnectionIntersections`).
2. Запустить `pytest backend/tests/test_sprint3_real_data.py` (env-gated tests подхватят новый архив автоматически).
3. Если schema mismatch с ИТС spec — patch `backend/src/optimyzer_backend/sql/deadlock_anatomy.py` (`parse_deadlock_extra` / альтернативные имена полей) + добавить regression test.
4. Update `docs/SPRINT_3_REPORT.md` → Phase D Validation Status → «real-data validated».
5. Re-record demo (опционально) с real TDEADLOCK на экране.

---

## Follow-up #2: Lock Wait Anatomy view (Sprint 5+ candidate)

В архиве 142 TLOCK events — это **просится** под отдельный view (по аналогии с Deadlock Anatomy, но для timeouts/waits). По ЦУП раздел 2.13.2 это «Анализ ожиданий блокировок».

**Что было бы:**

- Backend: `sql/lock_wait_anatomy.py` — для каждого TLOCK event парсит extra JSON (поля `WaitConnections`, `Locks`, `lck:Mode`), показывает «кто ждал кого на каком ресурсе»
- Frontend: list TLOCK events + drill page с graph blocked↔blocking↔resource
- Rule additions: `lock_wait_long` (>5 sec), `lock_wait_regular` (множество wait'ов на одном ресурсе → системный конфликт)
- Mapping на курс: Раздел 13 пункты «совместимость блокировок MSSQL/Postgres», «"точные" vs "предположительные" блокировки» (ЦУП 2.13.2)

**Почему не сделано в Sprint 3:** scope-out. В promt'е D был Deadlock Anatomy, не Lock Wait. Принято решение не расширять scope mid-sprint.

**Когда делать:** Sprint 5+ после ясности по hosted edition / production monitoring direction.

---

## Follow-up #3: URL routing для anatomy (shareable URLs)

В Sprint 3 промт Phase C просил URL `/anatomy/operation/<context>` и `/anatomy/session/<id>`. Сейчас реализовано через `store.selectedOperation + setScreen("anatomy")` — **не shareable**.

**Что бы дало:**
- Bookmarkable links к конкретной операции / сессии / deadlock
- Browser back/forward navigation
- Можно поделиться ссылкой в Telegram/Slack коллеге

**Что нужно:** добавить React Router, рефакторнуть все экраны на routes. Это **большая работа** — Sprint 4 не должен начинаться с этого, лучше отдельный refactor sprint.

---

## State of the repo

| Артефакт | Расположение |
|---|---|
| Branch | `feat/sprint-3-anatomy-and-explainer` |
| Tag | `v0.3.0-internal` (предлагается ставить после merge на main) |
| Sprint 3 report | `docs/SPRINT_3_REPORT.md` |
| Field study (Phase 0) | `docs/EXTRA_JSON_FIELD_STUDY.md` |
| Curriculum mapping | `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` |
| ADRs | `docs/DECISIONS.md` (ADR-022/023/024 в конце) |
| Synthetic fixture | `backend/tests/fixtures/synthetic_tdeadlock_archive.py` |
| Discovery script | `backend/scripts/inspect_extra_json.py` |
| AI .env example | `.env.example` |

---

## Что ждёт Sprint 4

Архитектор знает: после Sprint 3 идёт **Sprint 4 — Query Analyzer**. Promt пишется отдельно. Главные пункты курса для Sprint 4:

- Раздел 10 (Запросы которые работают быстро) — ~85% покрытия
- Раздел 8 (Анализ плана запроса) — ~80% покрытия (требует подключение к БД через `EXPLAIN`)
- Раздел 7 (Индексы) — ~60% покрытия (recommendation engine)

**Pre-condition Sprint 4:** архив с DBMSSQL events. Без него Query Analyzer не на чем валидировать. Это идёт **в parallel** с Follow-up #1 (один и тот же сбор logcfg.xml даст и DBMSSQL для Sprint 4, и TDEADLOCK для Phase D follow-up).

---

## Конец Sprint 3

Sprint 3 закрыт. Все 9 phases выполнены, все blocking acceptance gates пройдены. Open follow-ups зафиксированы. Я (Claude Code) готов к merge на main и тегу v0.3.0-internal как только Сергей одобрит.
