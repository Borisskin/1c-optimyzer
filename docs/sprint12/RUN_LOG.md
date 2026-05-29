# S12 · Фаза 1 — Систематический прогон на боевых данных

> Прогон на `C:\1C-TechLog` headless-драйвером `scripts/s12_run.py` (in-process вызовы
> RPC-хендлеров) + диагностика `scripts/s12_diag.py` (read-only к .duckdb).
> Все цифры — агрегаты; значения полей (SQL, контексты, имена) не извлекались.

## Обновление картины Фазы 0 (важно)

ТЖ **живой** — за время между инвентаризацией и прогоном база отработала под нагрузкой,
и **слой СУБД появился**. Вывод Фазы 0 «нет DBMSSQL» относился к более раннему снапшоту.
Факт на момент прогона (диапазон событий 2026-05-26 22:00 → 2026-05-29 22:28):

| Событие | Кол-во | Поля |
|---------|-------:|------|
| SCALL | 73 096 | — |
| CALL | 27 293 | — |
| **DBMSSQL** | **13 316** | with_sql 13 175 · **with_plan 12 888** · engine=mssql |
| EXCP | 11 399 | — |
| EXCPCNTX | 730 | cumulative duration |
| TLOCK | 137 | **55 с WaitConnections** (реальные конфликты) |
| Context | 53 | — |
| **TDEADLOCK** | **1** | — |

DBMSSQL собраны в окне **29.05 22:09–22:21** (12 мин нагрузки), 200 уникальных запросов,
движок **MSSQL**. Итог: **флагман валидируется на боевых данных** (вариант A де-факто
обеспечен). PostgreSQL-плеча в этом архиве нет (DBPOSTGRS=0) — PG-сценарии остаются на synthetic.

## Результаты прогона — 19/19 сценариев без падений

Ingest: 506 файлов, **126 190 событий, 0 ошибок парсинга**, ~8–12k eps, 73.9 МБ DuckDB.

| Группа | Сценарий | Итог |
|--------|----------|------|
| Ingest | load_directory + wait + stats | OK — 0 ошибок |
| Module 1 | process_roles, duration_histogram, activity_heatmap | OK |
| Module 1 | errors_feed, locks_timeline, slow_queries | OK |
| Module 1 | top_business_operations [CALL]/[all] | OK |
| Module 1 | presets first_100 / longest / deadlocks | OK |
| Флагман | plan_analyzer.status (planview доступен, 30 правил) | OK |
| Флагман | list_tj_plans (**12 888** планов из ТЖ) | OK |
| Флагман | get_tj_plan (slowest: dur≈96 c, plan_text есть) | OK |
| Флагман | view_deadlock_anatomy (на реальном TDEADLOCK) | OK |
| Флагман | view_operation_anatomy (top-операция) | OK |
| Флагман | plan_analyzer.analyze_file (.sqlplan фикстура, planview CLI) | OK |
| Флагман | sql_antipatterns.detect (20 боевых SQL) | **OK по коду, но см. F1** |

## Находки (severity)

### F1 — sql_antipatterns: 84% боевых SQL → `parse_error` · **HIGH**
На выборке 50 топ-DBMSSQL-запросов: **42 parse_error (84%)**. Классификация (без дампа SQL):
- первый токен падающих: **SELECT 38**, INSERT 3, прочее 1 — ломаются обычные SELECT, не экзотика;
- признаки: `WITH(...)` хинты — 5, `#temp` — 5, `SELECT INTO` — 3 (меньшинство → дело не только в них);
- успешно парсятся в основном CALL/CREATE/EXEC, SELECT — единично.
`sp_executesql`-unwrap отрабатывает (запросы начинаются с SELECT) → причина в **парсинге самого
T-SQL от 1С** (sqlglot). Где проявляется в UI: `sql_antipatterns.detect` вызывается из экрана
«Анализ плана» (автодетект + ручной SQL). Для Discovery — видимый дефект на главном сценарии.
**Фаза 2:** разобрать конкретные конструкции, починить (диалект/препроцессинг/деградация вместо parse_error).

### F2 — `preset:longest` и `duration_histogram` включают cumulative-длительность EXCPCNTX · **MEDIUM**
Топ-200 по `duration_us`: EXCPCNTX 138, CALL 30, SCALL 29, DBMSSQL 3. «Самые медленные» события —
это `EXCPCNTX` с cumulative duration (до ~10 ч), что вводит в заблуждение. Аналитические view
(`process_roles`, `top_business_operations`, `activity_heatmap`) уже исключают EXCPCNTX/Context
через `_NON_CUMULATIVE_DURATION_EXPR`, но `preset:longest` (сырой `ORDER BY duration_us`) и
`duration_histogram` — **нет**. **Фаза 2:** решить — исключать ли EXCPCNTX/Context в гистограмме
и «longest», или это осознанный «сырой» просмотр (зависит от того, где preset используется в UI).

### F3 — `errors_feed` по умолчанию возвращает ВСЕ события · **LOW (UX)**
Без `event_types`-фильтра `errors_feed` вернул total_rows=126 190 (весь архив), event_types=8.
By-design (docstring: «Лента всех событий ТЖ»), UI фильтрует chips. **Фаза 2 (UI-прогон):**
проверить дефолтный выбор типов при открытии экрана «Лента ошибок» — не вываливает ли по
умолчанию все 126k вместо ошибок (EXCP/EXCPCNTX/TDEADLOCK).

## Заметки для S13 (телеметрия — точки эмита)
`load_directory` (размер S/M/L, file_count), каждый `view_*`, `plan_analyzer.list_tj_plans`/
`get_tj_plan`, `sql_antipatterns.detect` (вкл. долю parse_error — это и продуктовая метрика качества),
`view_deadlock_anatomy`. Без содержимого.

## Что НЕ покрыто этим прогоном
- AI-сценарии (explain_query/plan/regression/logcfg) — идут через cloud-сервер, отдельный UI-прогон
  (главная зона риска галлюцинаций — оценивает владелец-эксперт на боевых SQL/планах).
- PostgreSQL (DBPOSTGRS=0 в архиве) — на synthetic.
- Регрессии (`regression.compute`) — нужен 2-й срез/архив.
- Граничные случаи ingest (битый файл, иная кодировка) — отдельный заход.

## Вердикт Фазы 1
Ядро (ingest, Module 1, флагман-планы, дедлоки, анатомия, planview) на боевых данных
**работает без падений**. Главный риск для показа людям — **F1** (антипаттерны на 84% боевых
SQL). F2/F3 — осмысленность/UX. Ниже — СТОП: владелец-эксперт оценивает осмысленность и
определяет приоритет чистки Фазы 2.

---
**Дата прогона:** 2026-05-29 · **Метод:** `scripts/s12_run.py` + `scripts/s12_diag.py` · **Статус:** Фаза 1 завершена, СТОП.
