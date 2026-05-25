# Real-World Test Fixtures — Sprint 9

Fixtures для regression-тестирования на реальных данных.
Цель: ловить регрессии когда движок ломается на production-like SQL.

---

## mssql_sp_executesql/queries.json

**32 запроса** в форматах sp_executesql, ODBC call.

**Источник:** Синтетические запросы по образцу реальных 1С-запросов из MSSQL ТЖ.
Созданы скриптом `tools/sprint9_collect/extract_fixtures.py`, Sprint 9 Phase A.

**Формат:** `[{"sql": "exec sp_executesql N'...'"}, ...]`

**Охватываемые антипаттерны:**
- SELECT * (select_star)
- LIKE с ведущим % (leading_wildcard_like)
- NOT IN с подзапросом (not_in_with_subquery)
- SELECT без WHERE (missing_where_clause)
- Implicit conversion через функции (implicit_conversion)
- Декартово соединение (missing_join_predicate)
- NOLOCK hint (nolock_hint)
- Динамический SQL (dynamic_sql)

**Особенности:**
- Все запросы обёрнуты в `exec sp_executesql N'...'` или `{call sp_executesql(N'...')}` (ODBC)
- Перед анализом ОБЯЗАТЕЛЬНО вызывать `_unwrap_sp_executesql()` — RPC layer делает это автоматически
- Тестировать через `detect_rpc(sql=..., engine="mssql")` для end-to-end покрытия

---

## pg_queries/queries.json

**34 запроса** в стиле 1С PostgreSQL.

**Источник:**
- 12 запросов из `dbpostgrs_sample.log` (реальный ТЖ pgBase)
- 22 синтетических запроса по образцу pg_stat_statements из базы Test1CProf на PG

**Формат:** `["SELECT ...", ...]` — plain list строк

**Охватываемые паттерны:**
- pg_catalog / pg_proc / pg_tablespace / pg_available_extensions — metadata queries от 1С Platform
- SELECT * с 1С-именованием (_Reference15, _Document70)
- LIKE '%text%' с ведущим подстановочным
- NOT IN с подзапросом (NULL propagation risk)
- $1, $2 ... параметры (prepared statement стиль PG)
- CASE WHEN, GROUP BY, агрегаты SUM()
- Кросс-регистровые JOIN (`_AccumRg`, `_InfoRg`)
- INSERT INTO / UPDATE / DELETE на 1С-таблицах

**Особенности:**
- `detect_1c_context()` должен возвращать True для запросов с `_reference`/`_document` в имени таблицы
- Metadata queries (pg_catalog) не должны вызывать crash и не должны генерировать false positives

---

## pg_plans_text/plan_00.txt ... plan_13.txt

**14 планов** в текстовом формате PostgreSQL EXPLAIN.

**Источник:** Извлечены из `dbpostgrs_sample.log` скриптом `extract_fixtures.py`.
Формат: output `EXPLAIN` без FORMAT JSON (то что пишет 1С Platform в ТЖ DBPOSTGRS события).

**Охватываемые типы планов:**
- Seq Scan на больших таблицах
- Index Scan / Index Only Scan
- Hash Join, Nested Loop, Merge Join
- Sort + Limit
- Aggregate

---

## mssql_plans/*.sqlplan

**13 файлов** — MSSQL execution plans в XML формате (SHOWPLAN_XML).

**Источник:** 
- `key_lookup.sqlplan`, `implicit_convert.sqlplan`, `exchange_spill.sqlplan` — созданы Sprint 9
- `memory_grant_wait.sqlplan`, `param_sniffing.sqlplan` — созданы Sprint 9
- `missing_join_predicate.sqlplan`, `compile_memory_exceeded.sqlplan` — созданы Sprint 9
- `case_predicate.sqlplan` — создан Sprint 9
- `plan_00.sqlplan` ... `plan_04.sqlplan` — скопированы из Sprint 7 discovery (реальные планы тестовой базы)

**Использование:**
```python
from optimyzer_backend.rpc.plan_analyzer_rpc import analyze_file_rpc
result = analyze_file_rpc(path="path/to/plan.sqlplan")
```

---

## Как добавлять новые fixtures

### MSSQL:
1. Получить сырой SQL из ТЖ DBMSSQL события (поле `sql`)
2. Если формат `exec sp_executesql N'...'` — оставить как есть
3. Добавить в `mssql_sp_executesql/queries.json` как `{"sql": "...", "note": "optional"}`

### PG:
1. Получить SQL из `pg_stat_statements` или ТЖ DBPOSTGRS события (поле `sql`)
2. Добавить в `pg_queries/queries.json` как строку в массиве

### .sqlplan:
1. Сохранить XML план из SSMS (Plan → Save As) в `mssql_plans/`
2. Имя файла = описание антипаттерна (snake_case)

---

## Связанные тесты

- `backend/tests/sql_antipatterns/test_real_world_regression.py` — main regression suite
- `backend/tests/sql_antipatterns/test_performance.py` — latency benchmarks
- `backend/tests/test_architecture.py` — module import + RPC registry sanity
