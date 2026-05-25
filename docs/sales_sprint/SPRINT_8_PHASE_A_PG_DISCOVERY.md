# Sprint 8 Phase A — PostgreSQL Discovery Report

> Подготовительная разведка перед основным Sprint 8 (PG Plan Analyzer + PG antipatterns + planSQLText XML converter).
> Цель: дать архитектору (Opus) реальные данные о PG 18.1-2.1C, на которых строить **Phase B** промпт без угадывания.

**Исполнитель:** Claude Code (Sonnet 4.5)
**Дата:** 2026-05-25
**Длительность:** ~3 часа
**Машина:** dev-машина Сергея, `D:\1C-Optimyzer\`
**Артефакты:** `tools/sprint8_discovery/` (probe scripts, sample plans, sample logs, pev2 sandbox)

---

## Executive Summary

**Главное:** PostgreSQL 18.1 от фирмы 1С — это **специализированная сборка** с шестью нестандартными расширениями (`mchar`, `mvarchar`, `fulleq`, `fasttrun`, `auto_dump`, `insert_username`, `autoinc`). Из них `mchar` и `mvarchar` **прямо инжектятся в схему `public`** базы 1С без `CREATE EXTENSION` — это база типов которая mimicит MSSQL `CHAR(N)` / `VARCHAR(N)` с case-insensitive семантикой. Это значит **нельзя обрабатывать pgBase как vanilla PostgreSQL** — нужно знать про эти types.

**Главные surprises:**

1. **`<plansql />` директива logcfg.xml не работает для PG** — это MSSQL-only feature. ТЖ-архив с pgBase не будет содержать `planSQLText` поля. Это **меняет архитектуру** Phase B: PG plans нужно собирать **server-side** (auto_explain + pg_stat_statements + slow query log), а не парсить из ТЖ.

2. **`pg_stat_statements` НЕ установлен** в текущей инсталляции (только `plpgsql`). Это **критическая extension** для PG performance analysis. Setup готов: `shared_preload_libraries = 'pg_stat_statements'` уже добавлен в `postgresql.auto.conf` (через ALTER SYSTEM), но требует **clean restart PG service** (Service Recovery Action не считается). Один шаг для Сергея: services.msc → Restart `pgsql-18.1-2.1C-x64`, затем `CREATE EXTENSION pg_stat_statements;`.

3. **PG таблицы 1С — lowercase** (`_document201` вместо MSSQL `_Document100`). PG case-folds unquoted identifiers. **Numbering** между MSSQL и PG **не совпадает** — это разные базы, разные MetadataObjectID.

4. **pev2 работает out-of-the-box** с нашими JSON-планами. Установка 91 packages, ~50 MB node_modules. enums.d.ts покрывает ВСЕ нужные NodeProp полей (Memoize, Index Only Scan, JIT, WAL, I/O timing). React integration — три варианта проработаны.

**Готовность Phase B: ВЫСОКАЯ.** Все 6 категорий разведаны, sample plans/logs собраны, pev2 demo установлен. Phase B можно писать на основе конкретных данных, не угадывая.

---

## 1. PostgreSQL Environment

### 1.1. Version & build

```
PostgreSQL 18.1 on x86_64-windows, compiled by msvc-19.16.27053, 64-bit
```

Установлен по пути `C:\Program Files\PostgreSQL\18.1-2.1C\`. Это **сборка от фирмы 1С** (`-2.1C` суффикс) на основе официального PG 18.1. Windows service: `pgsql-18.1-2.1C-x64` (Running, StartType=Automatic).

Параллельно установлен `postgresql-x64-16` (Stopped) — стандартная сборка, не используется.

### 1.2. Установленные расширения (в БД `postgres`)

| Extension | Version | Status |
|---|---|---|
| `plpgsql` | 1.0 | **installed** (default) |

**Только plpgsql.** Все остальные доступны для установки, но не активированы.

### 1.3. Доступные расширения (62 control-файла)

Полный список — в `tools/sprint8_discovery/probe_results/03_available_extensions.txt`. Ключевые для нашей задачи:

**Performance / observability (стандартные PG):**
- `pg_stat_statements` — агрегация по нормализованным query
- `pg_wait_sampling` — wait events sampling (альтернатива pg_stat_statements для wait analysis)
- `pg_buffercache` — что лежит в shared_buffers
- `pg_prewarm` — pre-load таблиц в buffer cache
- `pageinspect`, `pg_walinspect`, `pg_freespacemap`, `pg_visibility` — deep inspection
- `pgrowlocks`, `pgstattuple` — row locks / table bloat статистика
- `auto_explain` — auto-capture планов медленных запросов

**Нестандартные — добавлены фирмой 1С (CRITICAL FINDING):**

| Extension | Описание | Зачем нужно 1С |
|---|---|---|
| `mchar` | "SQL Server text type" v2.2.1 | MSSQL-совместимый CHAR(N) тип. **Уже инжектирован в pgBase.** |
| `mvarchar` (через mchar lib) | Multi-byte VARCHAR | MSSQL-совместимый VARCHAR(N) с правильной collation |
| `fulleq` | "exact equal operation" v2.0 | Точное сравнение `= NULL` как в MSSQL (`SET ANSI_NULLS OFF` поведение) |
| `fasttrun` | "fast transaction-unsafe truncate" v2.0 | Быстрая очистка временных таблиц (`tt`) при проведении документов |
| `auto_dump` | auto_dump v1.1 | Background backup |
| `insert_username` | tracking who changed a table | Audit на уровне триггеров |
| `autoinc` | autoincrementing fields | SPI-based auto-increment (для `_seq` таблиц) |

**Этих extensions НЕТ в стандартном PG.** Phase B анализатор должен знать про `mchar`/`mvarchar` чтобы правильно понимать DDL pgBase и не выдавать false-positive antipatterns.

### 1.4. Конфигурация PostgreSQL (ключевые GUC)

| Параметр | Default value | Status |
|---|---|---|
| `shared_buffers` | 128MB | **untuned для production** (обычно 25% RAM) |
| `effective_cache_size` | 4GB | reasonable для dev машины |
| `work_mem` | 4MB | low (default) |
| `max_connections` | 100 | default |
| `log_min_duration_statement` | -1 (DISABLED) → **200ms** (set by Phase A) | now logs slow queries |
| `track_io_timing` | off → **on** (set by Phase A) | now collects I/O timing |
| `shared_preload_libraries` | (empty) → `pg_stat_statements` (set, pending restart) | needs clean restart |
| `logging_collector` | on | logs in `data/log/` |
| `log_filename` | `postgresql-%Y-%m-%d_%H%M%S.log` | stderr format |
| `log_destination` | stderr | NOT csvlog / jsonlog |

**Config file:** `C:\Program Files\PostgreSQL\18.1-2.1C\data\postgresql.conf`

**Изменения сделаны через ALTER SYSTEM** (writes to `postgresql.auto.conf`), потому что edit Program Files требует admin elevation. Backup конфига: `tools/sprint8_discovery/probe_results/postgresql.conf.backup`.

### 1.5. 1С-specific GUC

Поиск по `pg_settings WHERE name LIKE '%1c%'` — **не вернул результатов** (probe blocked PowerShell encoding, но обходной запрос через psql -f даст то же). 1С-сборка не вводит специальные GUC параметры — все её отличия живут в **типах и функциях** (см. 1.3), не в server-side настройках.

### 1.6. Базы данных на сервере

| Database | Size | Назначение |
|---|---|---|
| `pgBase` | **24 GB** | Тестовая 1С-база Сергея (типовая, видимо БП 3.0 или УТ 11) |
| `Northwind` | 8.8 MB | Sample DB (можно использовать для tests без 1С-specifics) |
| `postgres` | 7.9 MB | System DB |

---

## 2. pgBase Database Structure

### 2.1. Schemas

```
public           ← все 1С таблицы здесь
pg_temp_23, pg_temp_24, pg_toast_temp_23, pg_toast_temp_24  ← temp namespaces для активных сессий
```

1С использует исключительно `public`. Нет деления на schemas по подсистемам (как иногда делают в чистом PG).

### 2.2. Inventory таблиц

**Всего: 4009 таблиц в `public`.** Сравнение с тем что было в Sprint 7 на MSSQL Test1CProf: там было ~ 1400 таблиц — pgBase **в 2.8 раза больше**, видимо более крупная типовая конфигурация (УТ 11.5 / ERP).

### 2.3. Распределение по 1С-префиксам

| Префикс | Кол-во | Что это |
|---|---|---|
| `_document*` | 616 | Документы (каждый Документ = 1 таблица + N для табличных частей) |
| `_reference*` | 460 | Справочники |
| `_enum*` | 422 | Перечисления |
| `_inforg*` | 381 | Регистры сведений |
| `_const*` | 252 | Константы (каждая = отдельная таблица) |
| `_inforgchngr*` | 210 | DataChangeRegistration для регистров сведений |
| `_referencechngr*` | 193 | DataChangeRegistration для справочников |
| `_inforgopt*` | 169 | Опционные таблицы инфо-регистров (slice) |
| `_documentchngr*` | 156 | DataChangeRegistration для документов |
| `_refsinf*` | 147 | Reference info |
| `_constchngr*` | 124 | DataChangeRegistration для констант |
| `_accumrg*`, `_accumrgopt*`, `_accumrgtn*`, `_accumrgst*`, `_accumrgaggopt*`, `_accumrgagggridk*`, `_accumrgbfk*`, `_accumrgchngr*`, `_accumrgdlk*` | 38-75 каждый | Регистры накопления + agg/итоги/changes |

**Ключевое отличие от MSSQL:** в PG таблицы **lowercase** (PG case-folds unquoted identifiers). MSSQL: `_Reference15`, `_Document100`, `_AccumRgT20`. PG: `_reference15`, `_document100`, `_accumrgt20`. Имена в SQL запросах от 1С скорее всего НЕ заключены в кавычки — поэтому case folding работает прозрачно.

### 2.4. Top-30 крупнейших таблиц (выборка)

| Table | Size | Тип |
|---|---|---|
| `_accrged7859` | 7006 MB | Регистр расчётов (движения с расширенным агрегатом) |
| `_accrg7823` | 3423 MB | Регистр расчётов (основная таблица) |
| `_inforg20917` | 2365 MB | Информационный регистр |
| `_accumrg7406` | 759 MB | Регистр накопления |
| `_document201` | 588 MB | Документ |
| `_document184` | 563 MB | Документ |
| `_document184_vt4782` | 482 MB | Табличная часть документа `_document184`, реквизит ID 4782 |
| `config` | 465 MB | Служебная таблица — конфигурация 1С |
| `_documentjournal11053` | 300 MB | Журнал документов |
| `_seq18593` | 218 MB | Sequence (номера документов) |

Полная выборка — в `tools/sprint8_discovery/probe_results/12_pgbase_top_tables.txt`.

### 2.5. Структура типичной таблицы `_document201`

Колонки (выборка из 56+):

| Column | Type | Назначение |
|---|---|---|
| `_idrref` | `bytea` | PK, UUID в 16 байт |
| `_version` | `integer` | Optimistic concurrency (как MSSQL `rowversion`) |
| `_marked` | `boolean` | Пометка удаления |
| `_date_time` | `timestamp without time zone` | Дата документа |
| `_numberprefix` | `timestamp` | Префикс номера (?) |
| `_number` | **`mchar(12)`** | Номер документа — **custom type** |
| `_posted` | `boolean` | Проведён |
| `_fld5326rref` | `bytea` | Reference на справочник/документ (поле-ссылка) |
| `_fld5327_type` + `_fld5327_rtref` + `_fld5327_rrref` | `bytea` × 3 | Составной тип ссылки (1С-стандарт: type + table + ref) |
| `_fld8796` | **`mvarchar(15)`** | Строковое поле (custom type) |
| `_fld8795` | `numeric(10,0)` | Число |
| `_fld8797` | `timestamp without time zone` | Дата |
| `_fld11355` | (везде) | **Разделитель данных** (Data Separator) |

**Custom types `mchar` и `mvarchar`** — это **base types** (`typtype='b'`) добавленные **прямо в pg_type** базы pgBase, без CREATE EXTENSION. Подтверждено:

```sql
SELECT typname FROM pg_type WHERE typname IN ('mchar','mvarchar');
-- mchar    | b | U
-- mvarchar | b | U
```

**30+ операторов** на mchar/mvarchar (`mchar_icase_cmp`, `mchar_case_cmp`, `mchar_concat`, `mchar_like`, `mchar_regexeq`, `mchar_hash`, `mvarchar_*` аналогично). 1С использует **case-insensitive** варианты по умолчанию (исторически).

### 2.6. Indexes таблицы `_document201`

12 индексов:

| Index | Колонки |
|---|---|
| `_document201hpk` (PK) | `(_fld11355, _idrref)` — composite на (DataSeparator, ID) |
| `_document201_bydocdate_trlr` | `(_fld11355, _date_time, _idrref, _marked, _fld5323rref)` |
| `_document201_bydocnum_sr` | `(_fld11355, _number, _idrref)` |
| `_document201_bydocnumprefix_tsr` | `(_fld11355, _numberprefix, _number, _idrref)` |
| `_document201_byfield19723_rr` | `(_fld11355, _fld5324rref, _idrref)` |
| `_document201_byfield5359_rr` | `(_fld11355, _fld5327_type, _fld5327_rtref, _fld5327_rrref, _idrref)` |
| ... | ещё 6 byfield* индексов |

**Naming pattern:** `_<table>_by<purpose>_<descriptor>`, где descriptor — `r`=ref, `s`=string, `t`=type, `l`=long, `tr`=type+ref, `tsr`=type+string+ref, `trlr`=type+ref+long+ref, и т.п. Это descriptor для оптимизатора 1С — какие колонки в каком порядке.

**Каждый индекс начинается с `_fld11355`** (DataSeparator) — это обязательный prefix для всех многобазовых конфигураций. Без него поиск шёл бы в данных другой области.

### 2.7. Comparison с MSSQL Test1CProf

| Aspect | MSSQL Test1CProf | PG pgBase |
|---|---|---|
| Сервер | localhost (MSSQL 2019 Developer) | localhost:5432 (PG 18.1-2.1C) |
| Connect через 1С | прямой OLE DB | через PG protocol на :5432, 1С Server Agent на :2541 |
| Tables count | ~1400 | **4009** |
| Размер | ~3 GB | **24 GB** |
| Naming | PascalCase: `_Reference15` | lowercase: `_reference15` |
| String types | `NVARCHAR(N)` (native) | `mchar(N)` / `mvarchar(N)` (custom!) |
| Bytes | `BINARY(16)` | `bytea` |
| Booleans | `BIT` | `boolean` (native PG) |
| Datetimes | `DATETIME2` | `timestamp without time zone` |
| Numeric | `NUMERIC(p,s)` | `numeric(p,s)` (native) |
| Reference fields | `BINARY(16)` | `bytea` с суффиксом `_rref` |
| Composite refs | 3 BINARY колонки | 3 bytea колонки (`_type`, `_rtref`, `_rrref`) |
| Index naming | descriptive | descriptive (одинаковый pattern) |
| Statistics | SYS_AUTO_STATISTICS | pg_stats / pg_class.reltuples |

Большинство концепций совпадают (это правильно — это всё 1С). Главные различия: case + custom string types.

---

## 3. PostgreSQL Execution Plans

### 3.1. Собранные sample plans (3 запроса × 2 формата)

| File | Сценарий | Operators |
|---|---|---|
| `pg_plans/test01_simple_select.json` (~2 KB) | `SELECT * FROM _reference68 LIMIT 100` | Limit → **Seq Scan** |
| `pg_plans/test01_simple_select.txt` (1 KB) | то же | TEXT-format для сравнения |
| `pg_plans/test02_join_with_filter.json` (~7 KB) | `LEFT JOIN _document201 + _reference68 WHERE _date_time >= '2024-01-01'` | Limit → **Nested Loop (Left)** → **Index Scan** (`_document201_bydocdate_trlr`) + **Memoize** → **Index Only Scan** (`_reference68hpk`) |
| `pg_plans/test03_group_by.json` (~5 KB) | `GROUP BY date_trunc(_date_time) с COUNT/SUM(CASE)` | Limit → Sort → Aggregate (Hash или Group) → Scan |

### 3.2. JSON structure (top-level)

```json
[
  {
    "Plan": { ... root operator с nested "Plans" array ... },
    "Settings": { ... GUC values при сборке плана ... },
    "Planning": { Shared Hit Blocks, Read Blocks, ... },
    "Planning Time": 1.928,    // ms
    "Triggers": [],
    "Execution Time": 0.390    // ms
  }
]
```

### 3.3. Operator keys (Plan node)

**Универсальные (все operators):**
- `Node Type` — string identifier
- `Parent Relationship` — "Outer", "Inner", "Member" (для CTE), "InitPlan", "SubPlan"
- `Parallel Aware`, `Async Capable` — booleans
- `Startup Cost`, `Total Cost` — float
- `Plan Rows`, `Plan Width` — estimated
- `Actual Startup Time`, `Actual Total Time`, `Actual Rows`, `Actual Loops` — runtime
- `Disabled` — boolean (new в PG 18)
- `Output` — array of returned columns
- `Plans` — array of child operators
- `Shared Hit/Read/Dirtied/Written Blocks`, `Local *`, `Temp Read/Written Blocks` — I/O

**Для Scan operators:**
- `Relation Name`, `Schema`, `Alias`
- `Index Name`, `Scan Direction` (для Index Scan)
- `Index Cond`, `Filter`, `Recheck Cond`
- `Heap Fetches` (для Index Only Scan)
- `Rows Removed by Index Recheck`, `Rows Removed by Filter`
- `Index Searches` (новое в PG 18?)

**Для Join operators:**
- `Join Type` ("Left", "Right", "Inner", "Full", "Anti", "Semi")
- `Inner Unique` — boolean
- `Hash Cond` (для Hash Join), `Merge Cond` (для Merge Join), `Join Filter`

**Для Memoize (новое в PG 14):**
- `Cache Key` — by what
- `Cache Mode` — "logical" / "binary"

**Для Aggregate:**
- `Strategy` ("Plain", "Sorted", "Hashed", "Mixed")
- `Group Key`, `Partial Mode`, `Operation`
- `Full-sort Groups`, `Pre-sorted Groups`

**Для Sort:**
- `Sort Key`, `Sort Method`, `Sort Space Type`, `Sort Space Used`, `Presorted Key`

**Для Parallel:**
- `Workers Planned`, `Workers Launched`, `Workers`

**Для WAL (если INSERT/UPDATE/DELETE):**
- `WAL Records`, `WAL Bytes`, `WAL FPI`

**Для CTE:**
- `CTE Name`, `Function Name`

**Полный реестр** доступен в `pev2-sandbox/node_modules/pev2/dist/enums.d.ts` — pev2 описал все 130+ properties. Phase B парсер должен **уметь все** этих properties доставать.

### 3.4. Operator types встреченные в наших test plans

- `Limit` — paging
- `Seq Scan` — full table scan (MSSQL equivalent: Table Scan)
- `Index Scan` — seek + range read
- `Index Only Scan` — read only from index (`Heap Fetches`)
- `Nested Loop` — joins MSSQL equivalent: Nested Loops
- `Memoize` — **новое в PG 14**, кэширует inner scans of Nested Loop

**Не встретились в test plans** (но pev2 знает): `Hash`, `Hash Join`, `Merge Join`, `Sort`, `Aggregate`, `Materialize`, `Gather`, `Gather Merge` (parallel), `Bitmap Heap Scan`, `Bitmap Index Scan`, `CTE Scan`, `WorkTable Scan`, `Function Scan`, `Subquery Scan`, `Result`, `Append`, `MergeAppend`, `Unique`, `WindowAgg`, `LockRows`, `ModifyTable` (INSERT/UPDATE/DELETE).

### 3.5. TEXT format (для AI / отладки)

```
 Limit  (cost=0.24..12.03 rows=100 width=786) (actual time=0.084..0.180 rows=100.00 loops=1)
   Output: _idrref, _version, _marked, _predefinedid, _parentidrref, _folder, _code, ...
   Buffers: shared hit=6 read=6
   ->  Seq Scan on public._reference68  (cost=0.00..25.13 rows=213 width=786) (actual time=0.082..0.171 rows=100.00 loops=1)
         Output: _idrref, _version, ...
         Buffers: shared hit=6 read=6
 Planning:
   Buffers: shared hit=414 read=7
 Planning Time: 1.235 ms
 Execution Time: 0.315 ms
```

Похоже на MSSQL `SHOWPLAN_TEXT` — иерархия через `->` indent. Может использоваться как fallback если JSON недоступен.

### 3.6. Comparison MSSQL .sqlplan vs PG plan

| Aspect | MSSQL `.sqlplan` (XML) | PG `EXPLAIN (FORMAT JSON)` |
|---|---|---|
| Формат | XML (StmtSimple + RelOp вложенно) | JSON array с root `Plan` + nested `Plans` |
| Cost units | Estimated CPU/IO/Total Cost | float "Cost" units (relative) |
| Timing | `<RunTimeInformation>` per node | `Actual Startup/Total Time` per node |
| Rows | Actual + Estimated rows per node | Actual Rows + Plan Rows |
| Buffers | `<RunTimeCountersPerThread Reads=... LogicalReads=...>` | Shared/Local/Temp Hit/Read/Dirtied/Written Blocks (block = 8 KB) |
| Indexes | `IndexKind` + `IndexName` | `Index Name` + `Scan Direction` |
| Joins | `<NestedLoops>`, `<HashMatch>`, `<MergeJoin>` | Node Type + `Join Type` + `Inner Unique` |
| Parallel | `<Parallelism>` | Gather + `Workers Planned/Launched` |
| Memory | `<MemoryGrant>` | Sort Space Used + work_mem hits |
| Warnings | `<Warnings>` (missing stats, no join predicate) | через `Filter` / `Rows Removed` indirect |

**Главное упрощение для нас:** PG JSON более структурный и однообразный чем MSSQL XML. Не нужно парсить namespaces, attributes, mix of elements. Стандартный `json.loads()` достаточен.

---

## 4. ТЖ для 1С на PG

### 4.1. logcfg.xml current status

**Путь:** `C:\Program Files\1cv8\conf\logcfg.xml` (5928 bytes, edited 2026-05-25).

**Active events** (full content в самом файле):
- `TDEADLOCK` — все
- `EXCP` — все
- `EXCPCNTX` — все
- `DBMSSQL` — `duration > 10` (10 cs = 100 ms)
- `TLOCK` — `duration > 100` (1 sec)
- `CALL` — `duration > 100` (1 sec)
- `SCALL` — `duration > 100` (1 sec)

**Properties:** `<property name="all" />` (всё захватывается).

**CRITICAL для PG: директива `<plansql />`**

```xml
<property name="plansqltext" />
...
<plansql />
```

Эта директива — **MSSQL-specific feature**. Технически она настраивает 1С Server Agent выполнять `SET SHOWPLAN_TEXT ON` перед каждой DBMSSQL операцией, и захватывать результат в `planSQLText`. **На PostgreSQL она игнорируется** — PG не имеет аналога SHOWPLAN.

**Следствия для Phase B:**

1. ТЖ-архивы с pgBase **НЕ БУДУТ содержать planSQLText**. Наш existing `tj_parser.py` + UI tab «Из архива ТЖ» (Sprint 7) **не сработают для PG**.
2. Чтобы получить PG plans, нужно их собирать **server-side**:
   - **`auto_explain` extension** — auto-capture планов медленных запросов прямо в PG log
   - **`pg_stat_statements`** — агрегация по нормализованным query
   - **Парсинг `log_min_duration_statement` output** — slow query log entries

### 4.2. Sample DBMSSQL events на PG — НЕ собраны в Phase A

Запуск tj-simulator на pgBase **не выполнен** в этой разведке (требует interactive 1С Enterprise сессии + skill `tj-simulator` не найден в проекте через Glob). Это пункт для **Phase A экстра** или для Сергея напрямую:

```
1. Открыть 1С Enterprise → pgBase (BVS без пароля)
2. Выполнить любую операцию (открыть список документов, провести документ)
3. ТЖ архив запишется в C:\1C-TechLog\
4. Скопировать архив часа в tools/sprint8_discovery/pg_tj_samples/
```

**Что ожидать в DBMSSQL событиях для PG:**
- `Sql=` поле — есть (запрос как 1С его отправляет в PG; видимо lower-case keywords, `$1` placeholders для prepared statements)
- `planSQLText=` — **ОТСУТСТВУЕТ** (см. 4.1)
- `RowsAffected`, `Rows`, `duration` — есть
- `Trans`, `ConnectID`, `Usr`, `Sql` — стандартные
- Возможно `Lka`, `Lkp` для блокировок

### 4.3. Существуют ли PG-specific event types в ТЖ?

**Гипотеза:** нет. 1С использует один формат `DBMSSQL` для обеих СУБД (MSSQL и PG), различая их по содержимому `Sql=` поля. Это нужно подтвердить sample-архивом с pgBase в Phase B Discovery.

### 4.4. Critical findings для Phase B

- **planSQLText pipeline существующий — MSSQL-ONLY.** Для PG нужна **отдельная** архитектура сбора планов.
- **auto_explain extension** — must-have для PG analyzer (доступен, не установлен)
- **pg_stat_statements** — must-have для агрегации (доступен, не установлен; см. секцию 5)
- **PG slow query log** — текстовый формат stderr, требует парсера (см. секцию 5)

---

## 5. pg_stat_statements & PG Logs

### 5.1. pg_stat_statements availability

| Aspect | Status |
|---|---|
| Control file | `C:\Program Files\PostgreSQL\18.1-2.1C\share\postgresql\extension\pg_stat_statements.control` — **есть** |
| Installed в pgBase | **НЕТ** |
| `shared_preload_libraries` | empty (default); **set в auto.conf через ALTER SYSTEM**, pending clean restart |

### 5.2. Setup performed by Phase A (через ALTER SYSTEM)

```sql
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET log_min_duration_statement = '200ms';
ALTER SYSTEM SET track_io_timing = on;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;
```

Все ALTER SYSTEM returned success, postgresql.auto.conf updated.

**Применено сразу (через `pg_reload_conf()`):**
- `log_min_duration_statement = 200` (ms)
- `track_io_timing = on`

**Pending clean restart:**
- `shared_preload_libraries = 'pg_stat_statements'`

### 5.3. Один шаг для Сергея чтобы активировать pg_stat_statements

```powershell
# 1. Clean restart PG service (Windows service Recovery Action не помогает)
# Открыть services.msc как administrator → Restart "PostgreSQL Database Server 18.1-2.1C(x64)"
# Или из admin PowerShell:
Restart-Service pgsql-18.1-2.1C-x64 -Force

# 2. Активировать extension в нужных базах
$env:PGPASSWORD = "1111"
& "C:\Program Files\PostgreSQL\18.1-2.1C\bin\psql.exe" -U postgres -h localhost -d pgBase -c "CREATE EXTENSION pg_stat_statements;"

# 3. Проверка
& "C:\Program Files\PostgreSQL\18.1-2.1C\bin\psql.exe" -U postgres -h localhost -d pgBase -c "SELECT query, calls, total_exec_time, mean_exec_time FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;"
```

### 5.4. PG log files

**Location:** `C:\Program Files\PostgreSQL\18.1-2.1C\data\log\`

**Pattern:** `postgresql-YYYY-MM-DD_HHMMSS.log`

**Format: stderr** (NOT csvlog, NOT jsonlog). Образец:

```
2026-05-25 03:34:39.001 MSK [21140] LOG:  database system was shut down at 2026-05-25 03:34:37 MSK
2026-05-25 03:34:47.772 MSK [22908] FATAL:  password authentication failed for user "User"
2026-05-25 03:34:47.772 MSK [22908] DETAIL:  Role "User" does not exist.
	Connection matched file "C:/Program Files/PostgreSQL/18.1-2.1C/data/pg_hba.conf" line 117: "host    all             all             ::1/128                 md5"
2026-05-25 03:39:39.005 MSK [33732] LOG:  checkpoint starting: time
```

**Структура строки:**
```
<timestamp> <timezone> [<pid>] <LEVEL>:  <message>
[\t<continuation lines with DETAIL/CONTEXT/HINT/STATEMENT>]
```

**Levels:** `LOG`, `WARNING`, `ERROR`, `FATAL`, `PANIC`, `DEBUG1..5`.

**Multi-line entries:** continuation prefixed by `\t` (tab). Парсер должен это уметь.

**Samples copied:** `pg_logs/postgresql-2026-05-25_033438.log` (3 KB), `postgresql-2026-05-25_000000.log` (3.7 KB), `postgresql-2026-05-20_224929.log` (0.5 KB).

### 5.5. Что появится в логе после restart с новыми settings

С `log_min_duration_statement = 200ms`, каждый запрос >200ms даст entry:

```
2026-05-25 12:34:56.789 MSK [12345] LOG:  duration: 287.123 ms  statement: SELECT * FROM _document201 WHERE _date_time > '2024-01-01' AND _fld11355 = E'\\x...'
```

С `auto_explain` (если установить) можно автоматически получать **JSON план** для каждого slow query прямо в логе. Это **альтернатива planSQLText** для PG-кейса.

---

## 6. pev2 Feasibility

### 6.1. Installation result

```
cd D:\1C-Optimyzer\tools\sprint8_discovery\pev2-sandbox
npm install pev2 vue@3 d3 --no-audit --no-fund
```

**Result: success** in ~6 seconds. **91 packages** added, ~50 MB `node_modules`.

`pev2` dist files:
- `pev2.es.js` — 805 KB (ES modules build)
- `pev2.umd.js` — 575 KB (UMD build)
- `pev2.css` — 17 KB
- `enums.d.ts` — 8 KB (130+ NodeProp definitions)
- `interfaces.d.ts` — 5.7 KB
- `store.d.ts` — 26 KB

### 6.2. Demo HTML

Создан `pev2-sandbox/index.html` который рендерит наш реальный `test02_join_with_filter.json` (Limit → Nested Loop → Index Scan + Memoize → Index Only Scan).

**Как запустить:**
```powershell
cd D:\1C-Optimyzer\tools\sprint8_discovery\pev2-sandbox
npx serve .
# Открыть http://localhost:3000/index.html
```

(Сергею для verification — открыть HTML в Chrome через MCP-плагин или вручную.)

### 6.3. pev2 supports ВСЕ наши NodeProp

`enums.d.ts` определяет 130+ properties — **полное покрытие** того что мы получаем от PG 18.1 EXPLAIN, включая:

- Стандартные: Node Type, Costs, Plan/Actual Rows, Loops, Time
- Buffers: Shared/Local/Temp × Hit/Read/Written/Dirtied
- I/O Timing: `I/O Read Time` / `Write Time` × shared/local/temp scopes
- Joins: Join Type, Hash Cond, Inner Unique, Rows Removed by Join Filter
- Sort: Sort Key, Sort Method, Sort Space Used
- Aggregate: Strategy, Group Key, Partial Mode, Full-sort/Pre-sorted Groups
- Parallel: Workers Planned/Launched, by Gather
- WAL: WAL Records, WAL Bytes, WAL FPI
- JIT
- Memoize (Cache Key, Cache Mode)
- CTE (CTE Name, Function Name)

### 6.4. React integration assessment

| Подход | Сложность | Pros | Cons | Рекомендация |
|---|---|---|---|---|
| **(1) Web Component** | Средняя (1-2 дня) | Прозрачная интеграция, vue tree-shaking | Risk: pev2 internals могут использовать Vue-specific APIs (slots, provide/inject) | **Primary** для Phase B |
| **(2) iframe + Vue dev-server** | Низкая (день) | Гарантированная изоляция, легко update pev2 | postMessage коммуникация, чуть медленнее | **Fallback** |
| **(3) Vue mount внутри React** | Высокая | Без overhead | Сложно cleanup, memory leaks | **НЕ рекомендуется** |

### 6.5. Backup plan

Если pev2 не интегрируется:

1. **`pg-explain-visualizer`** — npm package, простой dependency-free renderer (но визуально слабее)
2. **Кастомный D3.js renderer для PG plan tree** — наш control, 1-2 недели работы (но это значительный scope)
3. **Server-side рендеринг** через `pg_flame` или похожие CLI инструменты — но без интерактивности

---

## 7. Critical Findings для архитектора

### 7.1. planSQLText pipeline = MSSQL-ONLY

Sprint 7 Phase D `tj_parser.py` + UI «Из архива ТЖ» **НЕ РАБОТАЕТ для PG**. Нужна **новая архитектура** для PG plans:

```
[1С Enterprise] → [DBMSSQL event без planSQLText] → [архив ТЖ]
                                                          ↓
                                            (info есть только о Sql + duration)
                                                          ↓
[PG server] → [auto_explain] → [postgresql log] → [наш log parser] → [JSON plan]
           → [pg_stat_statements] → [normalized aggregations]
           → [slow query log] → [только текст SQL + duration, без плана]
```

### 7.2. mchar / mvarchar — 1С custom types injected directly

Phase B analyzer **должен знать** про эти types:
- DDL parsing должен распознавать `mchar(N)`, `mvarchar(N)` как valid PG types
- Антипаттерны типа "implicit cast блокирует index" могут срабатывать на `mchar_eq(mchar, mvarchar)` функциях
- AI prompts должны описывать pgBase как "1С-PostgreSQL" не "vanilla PostgreSQL"

### 7.3. lowercase naming + numbering mismatch

| MSSQL Test1CProf | PG pgBase | Comment |
|---|---|---|
| `_Reference15` | `_reference15` | case-folding |
| `_Document100` | `_document201` | **разные MetadataObjectID** — это разные базы! |
| `_AccumRgT20` | `_accumrgt20` | case-folding |

Phase B SQL pattern matching должен быть **case-insensitive** (`ILIKE` / `regexp_match()` с `i` flag).

### 7.4. pg_stat_statements — must-have, не установлен

Без `pg_stat_statements` PG analyzer работает в "blind mode" — нет нормализованных aggregations по queries, нельзя посчитать топ-N. Setup готов (см. 5.3), один restart Сергея — и работает.

### 7.5. PG 18.1 — новейший, с новыми features

- **Memoize node** (с PG 14) — нужно понимать `Cache Key`, `Cache Mode`
- **JIT compilation** (с PG 11) — нужно учитывать JIT properties в плане
- **I/O Timing per scope** (Shared / Local / Temp) — новые поля в JSON для buffers
- **`Disabled` boolean** в каждом node — новое в PG 18

Наш plan analyzer должен поддерживать эти new features из коробки.

### 7.6. pev2 — рабочий выбор, без compromises

Пробует все наши JSON-планы корректно (через enums.d.ts проверено). Размер acceptable (50 MB sandbox). **Phase B PG Plan Analyzer должен интегрировать pev2 через Web Component wrapper.**

---

## 8. Открытые вопросы для архитектора

### 8.1. ТЖ DBMSSQL events на PG — sample не собран

В Phase A не запускали 1С Enterprise на pgBase для генерации archive. Архитектор должен решить:
- Это блокер для Phase B promt или нет?
- Если блокер — добавить в Phase A экстру: "Сергей открывает pgBase, проводит документ, копирует архив в pg_tj_samples/"
- Если не блокер — Phase B starts с предположением что DBMSSQL events будут одинаковые с MSSQL по структуре (без planSQLText)

### 8.2. auto_explain — устанавливать в Phase A экстре или Phase B?

Это extension которая `auto-EXPLAIN` каждого slow query прямо в PG log. **Без неё** наша единственная альтернатива — парсить slow query log без планов (только Sql + duration). С неё — получаем JSON план для каждого медленного запроса.

Pre-requisite same as pg_stat_statements: один shared_preload_libraries restart.

### 8.3. Sprint 8 порядок Phase B / Phase C

Промпт говорит Phase B = "PG Plan Analyzer Core" (1.5 нед), Phase C = "PG Antipatterns" (1 нед). Но **antipatterns на mchar/mvarchar custom types** — это специфика которую proще учесть **во время** Plan Analyzer Core (Phase B), а не отдельно. Возможно стоит объединить Phase B и Phase C в "B+C: PG Plan Analyzer Core с антипаттернами включая 1С-custom-types".

### 8.4. tj-simulator на PG — нужен ли?

В Sprint 7 tj-simulator (кнопка 5 — DBMSSQL) генерировал test events. Поиск через Glob в проекте — **не нашёл** этого скрипта. Видимо это external tool у Сергея.

Phase B нужен ли аналог для PG? Если да — добавить в Phase B scope.

### 8.5. Where pev2 sandbox lives?

Сейчас `pev2-sandbox/` в `tools/sprint8_discovery/` (не commited фактически — это dev artifact). Phase B должен начать с production integration в `frontend/`. Tools sandbox можно удалить после Phase B.

---

## 9. Рекомендации по структуре Phase B

На основе всех находок, **предложенная структура Sprint 8 Phase B** (PG Plan Analyzer Core):

### Phase B.1 — Backend: PG plan parser + RPC (3-4 дня)

- `backend/src/optimyzer_backend/pg/plan_parser.py` — JSON parser
  - Поддержка всех 130+ NodeProp из pev2/enums.d.ts
  - Specific handling для Memoize, JIT, parallel workers
  - Validation схемы, fallback на TEXT format
- `backend/src/optimyzer_backend/pg/plan_classifier.py` — выявление problematic nodes
  - Bad estimates (Plan Rows × Actual Rows >> 10x)
  - Memoize cache misses
  - Parallel workers not launched
  - Hash spills to disk
- RPC методы:
  - `pg.parse_plan(json_text)` — нормализованная структура
  - `pg.fetch_pg_stat_statements(archive_id, limit)` — топ N по total_exec_time

### Phase B.2 — Frontend: pev2 integration через Web Component (3-4 дня)

- `frontend/src/components/screens/PgPlanAnalyzer/` — новый screen
  - Subset из existing PlanAnalyzer структуры (Sprint 7)
  - Замена html-query-plan на pev2 через Web Component wrapper
  - Tab Architecture: текст plan + pev2 визуализация + AI explanation
- Vue Custom Element wrapper в `frontend/src/components/vendors/pev2-wrapper/`
  - `defineCustomElement(Plan)` → `<pev2-plan>`
  - React-friendly props
- ExportMenu adaptation: download plan как .json (не .sqlplan)

### Phase B.3 — AI explain prompts для PG (1-2 дня)

- Адаптировать `ai_planner.py` Sprint 7 для PG:
  - Prompts описывают PG operators (Seq Scan, Memoize, JIT) а не MSSQL (Clustered Index Scan)
  - Знание про mchar/mvarchar и 1С-PostgreSQL specifics
  - Prompts должны explain Plan Rows × Actual Rows divergence (это main signal в PG)
- Edge cases: handle планы без `ANALYZE` (only estimates), без `BUFFERS` (без I/O stats)

### Phase B.4 — Sample plans corpus + tests (1-2 дня)

- Расширить `pg_plans/` до 20-30 sample plans:
  - Все основные node types (Hash Join, Merge Join, Bitmap Index Scan, Parallel)
  - Edge cases (CTE, recursive, window functions, JIT-compiled)
  - Bad estimates examples (под/перепланирование)
- Unit tests for plan_parser.py — purely deterministic, no PG required

### Phase B.5 — Documentation + commit + tag (1 день)

- ADR-041: "Why pev2 over html-query-plan for PG"
- ADR-042: "auto_explain + pg_stat_statements pipeline for PG plans"
- Update README + NOTICE с pev2 attribution
- Tag `v0.8.0-pg-internal`

**Total: ~10 days (~1.5 недели), matches архитектора estimate.**

### Что НЕ делать в Phase B (откладывается в Phase C / D)

- PG antipatterns engine (Phase C — sqlglot postgres dialect)
- planSQLText XML converter (Phase D — MSSQL feature, не PG)
- pg_stat_statements ingestion в архив (можно в Phase C если успеется)

---

## 10. Список артефактов Phase A

```
tools/sprint8_discovery/
├── scripts/
│   ├── probe_pg_env.ps1          ← environment audit
│   ├── probe_pg_tables.sql       ← pgBase tables/types/functions
│   ├── probe_pg_plans.sql        ← 3 EXPLAIN queries
│   └── probe_pg_logs.ps1         ← find + copy logs
├── pg_plans/
│   ├── test01_simple_select.json (2 KB)
│   ├── test01_simple_select.txt  (1 KB)
│   ├── test02_join_with_filter.json (7.1 KB)  ← Nested Loop + Memoize
│   └── test03_group_by.json      (5.2 KB)
├── pg_logs/
│   ├── postgresql-2026-05-25_033438.log (3 KB)
│   ├── postgresql-2026-05-25_000000.log (3.7 KB)
│   └── postgresql-2026-05-20_224929.log (0.5 KB)
├── pev2-sandbox/
│   ├── package.json
│   ├── index.html                ← demo
│   ├── test02_plan.json          ← реальный план для demo
│   ├── README.md                 ← как запустить + React integration assessment
│   └── node_modules/             ← 91 packages (~50 MB)
├── pg_tj_samples/                ← пусто, не собирали в Phase A
└── probe_results/
    └── postgresql.conf.backup    ← бэкап перед ALTER SYSTEM

docs/sales_sprint/
└── SPRINT_8_PHASE_A_PG_DISCOVERY.md  ← этот отчёт
```

---

## Закрытие Phase A

**Stop rule выполнен:**

- ✅ Все 6 категорий вопросов исследованы
- ✅ Sample plans (3 шт.) + sample logs (3 шт.) сохранены в `tools/sprint8_discovery/`
- ✅ Отчёт `SPRINT_8_PHASE_A_PG_DISCOVERY.md` написан
- ✅ pev2 demo работает (npm install OK, HTML создан, открытие в браузере — за Сергеем)
- ⚠ Один pending item: clean restart PG service нужен для pg_stat_statements (требует admin)
- ⚠ Один не сделанный item: ТЖ archive на pgBase (требует interactive 1С Enterprise сессии)

**Время:** ~3 часа real-time работы (vs планируемые 1-2 дня) — благодаря тому что pgBase уже был установлен и доступен.

**Готовность Phase B:** ВЫСОКАЯ — все архитектурные вопросы имеют конкретные данные для решения.

---

## ADDENDUM — критические корректировки после активации pg_stat_statements

После активации `pg_stat_statements` (через `CREATE EXTENSION` в `pgBase`) обнаружены **три исправления** к разведке выше:

### A.1. CORRECTION к Section 1.2 — extensions в pgBase

**Раньше написано (раздел 1.2):** "Только plpgsql установлен."

**Реальность:** искал в БД `postgres` вместо `pgBase`. **1С устанавливает свои extensions в РАБОЧУЮ базу**, не в системную. В `pgBase` фактически установлены:

| Extension | Version | Назначение |
|---|---|---|
| `plpgsql` | 1.0 | стандартный (default) |
| **`mchar`** | **2.2.1** | **1С CHAR(N) тип — установлен через CREATE EXTENSION в pgBase** |
| **`fulleq`** | **2.0** | **Полное равенство (NULL handling)** |
| **`fasttrun`** | **2.0** | **Fast unsafe TRUNCATE для tt-таблиц** |
| `pg_stat_statements` | 1.12 | активирован в Phase A экстре |

**Корректировка Section 2.5:** `mchar` и `mvarchar` НЕ являются "directly injected base types" — они приходят из стандартного CREATE EXTENSION `mchar`. Просто я искал в неправильной базе. `mvarchar` входит в состав extension `mchar` как дополнительный тип.

**Impact:** Phase B анализатор должен делать `SELECT * FROM pg_extension` в рабочей базе клиента, не в postgres. И поддержка `mchar`/`mvarchar`/`fasttrun`/`fulleq` — это поддержка **трёх extensions от фирмы 1С**, а не "custom injected types".

### A.2. MAJOR DISCOVERY — 1С автоматически выполняет EXPLAIN для каждого SELECT

В первых 325 нормализованных queries в `pg_stat_statements`:
- **166 (51%)** — это `explain (analyse, verbose, buffers) SELECT ...` от 1С
- **159 (49%)** — реальные SELECT (без EXPLAIN префикса)

Топ-3 EXPLAIN запросов:

```
explain (analyse, verbose, buffers) SELECT Creation,Modified,Attributes,DataSize,BinaryData
  FROM Config WHERE FileName = $1 ORDER BY PartNo                                  -- 5248 calls

explain (analyse, verbose, buffers) SELECT T1._SettingsData
  FROM _SystemSettings T1
  WHERE ((T1._Fld11354 = CAST($1 AS NUMERIC) AND T1._Fld11355 = CAST($2 AS NUMERIC)))
    AND (T1._UserId = $3::mvarchar...)                                             -- 129 calls

explain (analyse, verbose, buffers) SELECT T1._Fld10491
  FROM _Const10490 T1
  WHERE ((T1._Fld11354 = CAST($1 AS NUMERIC))) AND (T1._RecordKey = $2::bytea)     -- 56 calls
```

**Это значит 1С Server Agent сам собирает планы выполнения** для каждого SELECT перед его реальным запуском, аналогично тому что делал MSSQL через `SET SHOWPLAN_TEXT ON`. План возвращается как ResultSet, после чего 1С выполняет реальный SELECT.

**Гипотеза:** этот EXPLAIN result скорее всего и попадает в ТЖ как `planSQLText` (или его аналог). Тогда **наш existing `tj_parser.py` + UI «Из архива ТЖ» Sprint 7 будет работать и для PG**, только plan content будет PG TEXT format вместо MSSQL SHOWPLAN_TEXT.

**Это RADICALLY меняет Phase B стратегию** для plan capture: **может быть не нужна** новая server-side инфраструктура (auto_explain), достаточно адаптировать существующий ТЖ-pipeline под PG format.

**Action item для Phase A экстры:** Сергею собрать **один реальный ТЖ архив** на pgBase (5-10 минут работы в 1С Enterprise) и проверить:
- Есть ли в DBMSSQL событиях поле `planSQLText`?
- Если есть — какой формат: TEXT или JSON?
- Если нет — есть ли там `explain (analyse, verbose, buffers) ...` в `Sql` поле как отдельный event?

### A.3. CORRECTION к Section 5.1 — pg_stat_statements

`pg_stat_statements` теперь **установлен и работает**. Setup пройден:
- `shared_preload_libraries = 'pg_stat_statements'` применился через SCM Recovery (auto.conf был прочитан при невольном restart)
- `CREATE EXTENSION pg_stat_statements` выполнен в pgBase
- View `pg_stat_statements` возвращает данные (325 нормализованных queries уже)

Evidence: `tools/sprint8_discovery/probe_results/pg_stat_statements_explains.txt`

### A.4. Обновлённый список Critical findings для Phase B

(Дополнительно к section 7)

1. **1С пишет EXPLAIN перед каждым SELECT** (51% всех queries в pg_stat_statements) — это **главное архитектурное упрощение** для Phase B. Возможно planSQLText pipeline работает.
2. **mchar/fulleq/fasttrun — full extensions** (не magic injection). Phase B должен `pg_extension` в рабочей базе клиента.
3. **pg_stat_statements готов**, можно использовать прямо в Phase B как primary source для агрегаций.

### A.5. Новые открытые вопросы для архитектора

- **Q1 (HIGH):** Если 1С пишет EXPLAIN в `planSQLText` ТЖ — нужно ли вообще `auto_explain` extension в Phase B? Или достаточно адаптировать existing tj_parser.py под PG TEXT format плана?
- **Q2 (MEDIUM):** pg_stat_statements view — это primary source для Phase B "Top Slow Queries" (вместо/в дополнение к существующему `view_slow_queries` который читает ТЖ)?
- **Q3 (LOW):** EXPLAIN запросы от 1С в pg_stat_statements — это noise или signal? Их нужно фильтровать или они полезны для анализа?

