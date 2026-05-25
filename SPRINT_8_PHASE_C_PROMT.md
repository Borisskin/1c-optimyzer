# Sprint 8 Phase C — PostgreSQL Antipatterns Engine

> Завершение Sprint 8: добавление PG-specific anti-patterns detection через sqlglot postgres dialect.
> Это финальная phase Sprint 8 — после неё закрываем tag v0.8.0-internal.
>
> **База:** Phase A (Discovery) + Phase B (PG Plan Analyzer Core), оба закрыты. Tag `v0.8.0-pg-core-internal` на main.

---

## Контекст для исполнителя

**Кто работает:** Claude Code на машине Сергея.
**Что есть на входе:**
- Sprint 6 — T-SQL antipatterns engine через sqlglot (9 detectors)
- Sprint 7 — Plan Analyzer для MSSQL
- Phase B — PG Plan Analyzer + tj_parser DBPOSTGRS + AI prompts split + pev2 + re-EXPLAIN
- Реальный pgBase с pg_stat_statements и DBPOSTGRS sample

**Что добавляет Phase C:**
- Расширение `sqlglot` antipatterns engine на PostgreSQL dialect
- **15 PG-specific antipattern detectors** (включая 1С-аware)
- Integration в QueryAnalyzer для PG queries (engine='postgres')
- AI explanation context для PG antipatterns

**Что НЕ делаем (out of scope Phase C):**
- pg_stat_statements ingestion → Sprint 11+
- Manual demo session с тобой → отдельный шаг после Phase C
- Marketing / pricing / Phase 1 INFRA → пока заморожено

**Ожидаемая длительность:** 1 рабочая сессия (4-7 часов как Phase B).

---

## Архитектурные решения (приняты архитектором)

### Решение 1: Универсальный antipatterns engine, не split по dialect

Existing `T-SQL antipatterns` модуль (Sprint 6) расширяется на универсальный `SQL antipatterns engine` с поддержкой обоих диалектов. Не создаём отдельный модуль `pg_antipatterns/`.

Структура файлов после Phase C:

```
backend/src/optimyzer_backend/sql_antipatterns/   ← переименовать из tsql_antipatterns/
├── __init__.py
├── engine.py                    ← диспетчер по dialect
├── models.py                    ← TSqlAntipattern → SqlAntipattern
├── tsql/                         ← MSSQL-specific (existing Sprint 6)
│   ├── __init__.py
│   ├── not_in_with_nullable.py
│   ├── leading_wildcard_like.py
│   └── ... 9 detectors
├── postgres/                     ← NEW PG-specific
│   ├── __init__.py
│   ├── offset_without_limit.py
│   ├── ilike_without_trgm.py
│   └── ... 15 detectors
├── shared/                       ← общие для обоих движков
│   ├── __init__.py
│   ├── leading_wildcard_like.py  ← (общая логика, разные сообщения)
│   └── select_star.py
└── tests/
    ├── test_postgres_detectors.py
    ├── test_dialect_routing.py
    └── fixtures/
        ├── pg_queries/
        └── tsql_queries/
```

### Решение 2: Engine field из Phase B используется для dispatching

Когда юзер открывает SQL в QueryAnalyzer (с архива ТЖ → DBPOSTGRS / DBMSSQL event):
- `engine = "postgres"` → запускается PG antipatterns set
- `engine = "mssql"` → запускается T-SQL antipatterns set
- `engine = None` (юзер вставил SQL вручную) → юзер выбирает в dropdown «PostgreSQL» / «MS SQL Server»

### Решение 3: НЕ строим parser «с нуля» для PG SDBL

PG-specific детекторы работают на **SQL** уровне (T-SQL и PG SQL который генерирует 1С), **не на SDBL уровне**. Для SDBL anti-patterns у нас уже есть bsl-language-server (Sprint 6). Phase C — только SQL уровень.

### Решение 4: 1С-aware versions PG антипаттернов

Некоторые PG antipatterns имеют 1С-специфичную интерпретацию:
- `mchar`/`mvarchar` implicit casts — это нормально для 1С (extension от 1С специально для совместимости с MSSQL)
- Lowercase table names (`_document201`) — это PG case-folding, нормально
- `SET enable_mergejoin = off` — это уже применено клиентом, не recommendation

Каждый детектор должен иметь optional `is_1c_context` parameter:
- `False` (default) — обычные PG правила
- `True` — 1С-aware: НЕ flag false-positives для 1С специфик

Detection of 1С context: smart heuristic — если в SQL встречаются таблицы вида `_reference\d+` / `_document\d+` / `_accumrg\d+` / тип `mvarchar` / `mchar` → `is_1c_context = True`.

### Решение 5: Severity scheme — единая для обоих движков

`CRITICAL` / `WARNING` / `INFO` — без специальных PG severity. Это упрощает UI и AI prompt.

---

## Структура Phase C (6 sub-phases)

| Sub-phase | Что | Длительность |
|---|---|---|
| **C.1** | Refactoring tsql_antipatterns → sql_antipatterns + structure | 0.5 дня |
| **C.2** | 15 PG detectors implementation + tests | 2-3 дня |
| **C.3** | Dispatcher по engine + QueryAnalyzer UI integration | 1 день |
| **C.4** | AI prompt integration для PG antipatterns context | 0.5 дня |
| **C.5** | Real-data tests + edge cases | 1 день |
| **C.6** | Documentation + closure + final tag v0.8.0-internal | 0.5 дня |

**Итого: 5-6 дней** (или 1 длинная сессия Claude Code).

---

# SUB-PHASE C.1 — Refactoring

## Цель

Переименовать existing `tsql_antipatterns` → `sql_antipatterns` без breaking changes для existing функциональности. Подготовить структуру для PG детекторов.

## Шаги

### C.1.1. Rename module

```bash
git mv backend/src/optimyzer_backend/tsql_antipatterns backend/src/optimyzer_backend/sql_antipatterns
```

### C.1.2. Создать подпапки `tsql/` и `postgres/`

В `sql_antipatterns/`:
- Перенести existing 9 T-SQL detectors в `tsql/`
- Создать пустой `postgres/` с `__init__.py`
- Перенести существующие общие helpers в `shared/`

### C.1.3. Обновить imports

Все existing imports `from optimyzer_backend.tsql_antipatterns import ...` обновить на `from optimyzer_backend.sql_antipatterns import ...`. Backward compat shim не нужен — это **внутренний** module, импорты внутри проекта.

Найти все usage:
```bash
grep -rn "tsql_antipatterns" backend/ --include="*.py"
```

### C.1.4. Models update

```python
# sql_antipatterns/models.py
from typing import Literal

class SqlAntipattern(BaseModel):
    name: str                                  # "OffsetWithoutLimit"
    description: str                            # для UI
    description_ru: str                         # для русского UI
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    dialect: Literal["mssql", "postgres"]      # ← новое поле
    is_1c_context_only: bool = False           # появляется только в 1С context
    location_in_ast: Optional[str] = None
    rationale: str                              # почему это antipattern
    recommendation: str                         # что делать
```

### C.1.5. Tests refactoring

Existing test файлы перемещены в `tests/tsql/` (или префиксы переименованы). Все existing 25 tests должны pass без изменений логики.

## Acceptance criteria C.1

- [ ] Module renamed без потери existing functionality
- [ ] Existing 9 T-SQL detectors работают как раньше
- [ ] All 25+ existing tests pass
- [ ] Структура `postgres/` готова к добавлению детекторов
- [ ] Backend tests > 789 (Phase B baseline)

**Stop rule C.1:** `pytest backend/ -v` показывает 789+ tests passing.

**Длительность: 0.5 дня.**

---

# SUB-PHASE C.2 — 15 PG Antipatterns

## Цель

Реализовать 15 PostgreSQL-specific antipatterns detector'ов через sqlglot `dialect="postgres"`.

## Каталог 15 детекторов

Для каждого детектора в Phase C создаётся отдельный файл в `postgres/`. Стандартная структура:

```python
# postgres/offset_without_limit.py

from sqlglot import exp
from ..models import SqlAntipattern

def detect_offset_without_limit(ast, is_1c_context: bool = False) -> list[SqlAntipattern]:
    """Detects OFFSET clause without LIMIT — pagination antipattern."""
    findings = []
    for offset_node in ast.find_all(exp.Offset):
        # ... detection logic
        findings.append(SqlAntipattern(
            name="OffsetWithoutLimit",
            description="OFFSET without LIMIT — все строки сканируются и отбрасываются до достижения OFFSET",
            description_ru="OFFSET без LIMIT — PG будет сканировать все строки до offset позиции, отбрасывая их. Используйте keyset pagination.",
            severity="WARNING",
            dialect="postgres",
            rationale="OFFSET в PostgreSQL требует сканирования и пропуска всех строк до достижения offset. Чем дальше пейджинг — тем медленнее.",
            recommendation="Используйте keyset pagination: `WHERE id > $last_id ORDER BY id LIMIT N` вместо `OFFSET N`.",
        ))
    return findings
```

### Список 15 детекторов

**1. `OffsetWithoutLimit`** — OFFSET без LIMIT
- Pattern: `SELECT ... OFFSET N` без `LIMIT M`
- Severity: WARNING
- 1С-aware: False (стандартный PG антипаттерн)

**2. `LargeOffsetPagination`** — OFFSET с large value (>1000)
- Pattern: `OFFSET N` где N > 1000
- Severity: WARNING (CRITICAL если > 10000)
- Why: PG сканирует все строки до offset

**3. `IlikeWithoutTrgm`** — ILIKE без `pg_trgm` GIN индекса
- Pattern: `WHERE col ILIKE '%...%'`
- Severity: WARNING
- Why: ILIKE с double wildcard не использует индекс без `pg_trgm` extension
- 1С-aware: False (1С обычно использует LIKE с case-insensitive collation через mchar)

**4. `LikeWithLeadingWildcard`** — LIKE с leading `%`
- Pattern: `LIKE '%text'` или `LIKE '%text%'`
- Severity: WARNING
- Why: невозможен B-tree index seek, нужен Seq Scan
- 1С-aware: True (1С генерирует такое для full-text search)

**5. `NotInWithSubquery`** — NOT IN с подзапросом (NULL issues + performance)
- Pattern: `WHERE col NOT IN (SELECT ...)`
- Severity: WARNING
- Why: PG не оптимизирует так же хорошо как NOT EXISTS + NULL handling issues
- Recommendation: переписать на `NOT EXISTS`

**6. `JsonbWithoutGin`** — JSONB операции без GIN индекса (heuristic)
- Pattern: `WHERE col @> '...'` или `col -> 'key'` или `col ->> 'key' = '...'`
- Severity: INFO (мы не знаем есть ли индекс, только намёк)
- Why: JSONB без GIN — sequential scan

**7. `CastInWherePredicate`** — Function/CAST на колонке в WHERE
- Pattern: `WHERE LOWER(col) = '...'` / `WHERE col::text = '...'` / `WHERE EXTRACT(YEAR FROM col) = ...`
- Severity: WARNING
- Why: index seek невозможен, нужен expression index или WHERE без функции
- 1С-aware: специальная обработка — `_fld100::mchar = '...'` это нормально для 1С (mchar/mvarchar interop)

**8. `UnionInsteadOfUnionAll`** — UNION где данные точно не пересекаются
- Pattern: `... UNION ...` (без ALL) при условии что подзапросы из разных таблиц или с явно непересекающимися фильтрами
- Severity: INFO (не всегда antipattern)
- Why: UNION добавляет implicit SORT + UNIQUE

**9. `SubqueryInSelectList`** — Correlated subquery в SELECT list
- Pattern: `SELECT col, (SELECT ... FROM other WHERE other.fk = main.id) FROM main`
- Severity: WARNING
- Why: N+1 на больших результатах, лучше LATERAL или JOIN

**10. `DistinctOnLargeResult`** — DISTINCT для устранения дубликатов от JOIN
- Pattern: `SELECT DISTINCT ... FROM a JOIN b ...` (heuristic — DISTINCT + JOIN)
- Severity: INFO
- Why: лучше переписать на EXISTS или субзапрос с агрегацией

**11. `ImplicitTypeCast`** — implicit cast между несовместимыми типами
- Pattern: `WHERE int_col = '123'` (string vs int) / `WHERE col = 1` где col это text
- Severity: WARNING
- Why: PG делает implicit cast, который может ломать индекс
- 1С-aware: специальная обработка — `_fld100::mvarchar = $1::mvarchar` это нормально

**12. `SelectStarWithJoin`** — `SELECT *` с JOIN'ами
- Pattern: `SELECT * FROM a JOIN b ...`
- Severity: INFO
- Why: лишние колонки, network bandwidth, defeats index-only scan
- 1С-aware: 1С НИКОГДА не пишет SELECT *, эта проблема не для 1С context

**13. `OrderByRandomWithLimit`** — `ORDER BY RANDOM() LIMIT N`
- Pattern: `ORDER BY RANDOM() LIMIT N` или `ORDER BY random()`
- Severity: WARNING (CRITICAL если N большое или таблица большая)
- Why: full table scan + sort, очень медленно для больших таблиц
- Recommendation: `TABLESAMPLE BERNOULLI(N)` или ID-based random

**14. `MissingWhereOnUpdateDelete`** — UPDATE/DELETE без WHERE
- Pattern: `UPDATE tbl SET ...` или `DELETE FROM tbl` без WHERE
- Severity: **CRITICAL**
- Why: затронет все строки таблицы

**15. `McharVsTextComparison`** — 1С-specific: mchar/mvarchar и text сравнение
- Pattern: `WHERE col::mchar = $1::text` или `col::mvarchar = $1` без cast
- Severity: WARNING
- 1С-aware: True (специфично для 1С)
- Why: PG может не уметь оптимально использовать индекс

## Шаги Phase C.2

### C.2.1. Установить/проверить sqlglot postgres dialect

Existing `sqlglot==30.8.0` в backend deps уже работает для PG.

Sanity check:
```python
import sqlglot
sqlglot.parse_one("SELECT * FROM _document201 OFFSET 100", dialect="postgres")
```

### C.2.2. 1С context detection helper

```python
# sql_antipatterns/postgres/_helpers.py

import re

_1C_TABLE_PATTERN = re.compile(
    r'_(reference|document|accumrg|accumrgt|inforg|enum|const|seq|chrc)\d+',
    re.IGNORECASE
)
_1C_TYPE_PATTERN = re.compile(r'::?(mchar|mvarchar)\b', re.IGNORECASE)

def detect_1c_context(sql: str) -> bool:
    """Heuristic: SQL содержит 1С-specific identifiers?"""
    return bool(_1C_TABLE_PATTERN.search(sql) or _1C_TYPE_PATTERN.search(sql))
```

### C.2.3. Engine с registry detectors

```python
# sql_antipatterns/engine.py

from typing import Literal
import sqlglot
from .models import SqlAntipattern
from .postgres import (
    detect_offset_without_limit,
    detect_large_offset_pagination,
    detect_ilike_without_trgm,
    detect_like_with_leading_wildcard,
    detect_not_in_with_subquery,
    detect_jsonb_without_gin,
    detect_cast_in_where_predicate,
    detect_union_instead_of_union_all,
    detect_subquery_in_select_list,
    detect_distinct_on_large_result,
    detect_implicit_type_cast,
    detect_select_star_with_join,
    detect_order_by_random_with_limit,
    detect_missing_where_on_update_delete,
    detect_mchar_vs_text_comparison,
)
from .tsql import (
    # existing 9 detectors
)
from .postgres._helpers import detect_1c_context

POSTGRES_DETECTORS = [
    detect_offset_without_limit,
    detect_large_offset_pagination,
    # ... 15 total
]

TSQL_DETECTORS = [
    # ... existing 9
]

def detect_antipatterns(
    sql: str,
    engine: Literal["mssql", "postgres"],
    force_1c_context: Optional[bool] = None,
) -> list[SqlAntipattern]:
    """Main entry point — analyze SQL and return list of detected antipatterns."""
    is_1c = force_1c_context if force_1c_context is not None else detect_1c_context(sql)
    
    try:
        ast = sqlglot.parse_one(sql, dialect=engine)
    except sqlglot.errors.ParseError as e:
        return [SqlAntipattern(
            name="ParseError",
            description=str(e),
            description_ru=f"Не удалось распарсить SQL: {e}",
            severity="WARNING",
            dialect=engine,
            rationale="Запрос не валиден или dialect не определён правильно.",
            recommendation="Проверьте синтаксис.",
        )]
    
    findings: list[SqlAntipattern] = []
    
    detectors = POSTGRES_DETECTORS if engine == "postgres" else TSQL_DETECTORS
    for detector in detectors:
        try:
            findings.extend(detector(ast, is_1c_context=is_1c))
        except Exception as e:
            # Robustness — один сломанный detector не должен валить весь анализ
            logger.warning(f"Detector {detector.__name__} failed: {e}")
    
    # Sort by severity: CRITICAL > WARNING > INFO
    return sorted(findings, key=lambda f: ["CRITICAL", "WARNING", "INFO"].index(f.severity))
```

### C.2.4. Implementation 15 detectors

Каждый detector — отдельный файл. Стандартная структура (см. шаблон выше).

**Test-driven approach:**
1. Для каждого detector написать test fixture с **positive** примером (антипаттерн обнаружен) и **negative** примером (антипаттерн не обнаружен)
2. Реализовать detector до прохода теста
3. Edge cases: парсер на nested queries, CTE, UNION, разные styles

**Fixtures** — собрать из:
- `tools/sprint8_discovery/pg_tj_samples/dbpostgrs_sample.log` — реальные PG queries от 1С
- `pg_stat_statements` view из pgBase — top queries
- Synthetic positive/negative cases

### C.2.5. Tests для каждого детектора

```python
# tests/postgres/test_offset_without_limit.py

def test_offset_without_limit_detected():
    sql = "SELECT * FROM _document201 OFFSET 100"
    findings = detect_antipatterns(sql, engine="postgres")
    assert any(f.name == "OffsetWithoutLimit" for f in findings)

def test_offset_with_limit_not_detected():
    sql = "SELECT * FROM _document201 OFFSET 100 LIMIT 50"
    findings = detect_antipatterns(sql, engine="postgres")
    assert not any(f.name == "OffsetWithoutLimit" for f in findings)

def test_1c_context_detection_for_offset():
    """OFFSET без LIMIT в 1С коде — всё равно flagged."""
    sql = "SELECT * FROM _document201 OFFSET 100"
    findings = detect_antipatterns(sql, engine="postgres")
    assert any(f.name == "OffsetWithoutLimit" for f in findings)
```

**Minimum 30 tests** для 15 детекторов (positive + negative + 1с edge case для каждого).

## Acceptance criteria C.2

- [ ] Все 15 PG detector файлов созданы в `postgres/`
- [ ] Engine.py dispatch по dialect работает
- [ ] 1С context detection helper работает
- [ ] Минимум 30 тестов passing для PG детекторов
- [ ] Real PG queries из `dbpostgrs_sample.log` обработаны без crashes
- [ ] T-SQL детекторы продолжают работать (regression)

**Stop rule C.2:** `pytest backend/src/optimyzer_backend/sql_antipatterns/tests/postgres/ -v` показывает 30+ tests passing. Прогон на real `dbpostgrs_sample.log` не падает.

**Длительность: 2-3 дня.**

---

# SUB-PHASE C.3 — Dispatcher + QueryAnalyzer UI integration

## Цель

Интегрировать новый PG antipatterns engine в existing QueryAnalyzer UI. Когда юзер открывает SQL с engine="postgres" — показываются PG antipatterns. Иначе — T-SQL antipatterns.

## Шаги

### C.3.1. RPC layer

В `backend/src/optimyzer_backend/rpc/query_analyzer_rpc.py` — расширить existing endpoint:

```python
@rpc("query_analyzer.detect_antipatterns")
async def detect_antipatterns_rpc(
    sql: str,
    engine: Literal["mssql", "postgres"] = "mssql",  # default для backward compat
    force_1c_context: Optional[bool] = None,
) -> list[dict]:
    """Returns list of detected antipatterns."""
    findings = detect_antipatterns(sql, engine=engine, force_1c_context=force_1c_context)
    return [f.model_dump() for f in findings]
```

### C.3.2. Frontend dispatcher

Frontend существующий `QueryAnalyzer.tsx`:

```tsx
const [engine, setEngine] = useState<"mssql" | "postgres">("mssql");

// Auto-detect engine when SQL loaded from TJ archive
useEffect(() => {
  if (sqlSource?.engine) {
    setEngine(sqlSource.engine);
  }
}, [sqlSource]);

// Manual dropdown when SQL pasted manually
{sqlSource?.origin === "manual" && (
  <Select value={engine} onValueChange={setEngine}>
    <SelectItem value="mssql">MS SQL Server</SelectItem>
    <SelectItem value="postgres">PostgreSQL</SelectItem>
  </Select>
)}
```

### C.3.3. UI rendering

Existing antipatterns list rendering (T-SQL) расширяется на universal:

- Severity badges (CRITICAL/WARNING/INFO) — те же что и раньше
- Engine indicator (small badge next to title): "MS SQL" / "PostgreSQL"
- **Description на русском** (`description_ru`) — основное отображение
- Rationale + Recommendation — expandable details

### C.3.4. Engine badge в antipatterns card

Если ты видишь PG-only детектор активным — показать badge:
```
[OffsetWithoutLimit]  [PostgreSQL]  [WARNING]
```

### C.3.5. 1С context auto-detection indicator

Если detect_1c_context() вернул True — показать info badge:
```
ℹ Распознан 1С-context — некоторые паттерны интерпретируются с учётом 1С
```

## Acceptance criteria C.3

- [ ] RPC endpoint принимает engine parameter
- [ ] Frontend QueryAnalyzer dispatcher работает
- [ ] Engine dropdown показывается для manual SQL
- [ ] Auto-detect engine из TJ archive (через engine field из Phase B)
- [ ] UI отображает PG antipatterns корректно
- [ ] Engine badges + 1С context indicator работают

**Stop rule C.3:** Сергей берёт PG plan из архива → QueryAnalyzer → видит antipatterns для PG специфики.

**Длительность: 1 день.**

---

# SUB-PHASE C.4 — AI prompt integration

## Цель

PG antipatterns передаются в AI explainer как дополнительный context — Claude использует их для более точных recommendations.

## Шаги

### C.4.1. Extend PlanExplainRequest

```python
# server/services/ai_explainer.py

class PlanExplainRequest(BaseModel):
    # ... existing fields
    detected_antipatterns: Optional[list[dict]] = None  # NEW
    engine: Literal["mssql", "postgres"] = "mssql"      # already from Phase B
```

### C.4.2. Updated SYSTEM_PROMPT_EXPLAIN_PG_PLAN

Расширить existing PG prompt из Phase B с новой секцией:

```python
SYSTEM_PROMPT_EXPLAIN_PG_PLAN = """... (existing content from Phase B) ...

## Detected SQL Antipatterns

If `detected_antipatterns` provided in request — это уже найденные паттерны от sqlglot engine. **Используй их как стартовую точку** для своего анализа:
- Не повторяй их в hotspots
- Расширяй с конкретикой плана (например antipattern говорит "OFFSET без LIMIT", ты можешь дополнить — "в плане видно Seq Scan + Limit без index — это особенно плохо для большой таблицы _document201")
- Если в antipatterns есть категория "1с-aware" — учитывай 1С-context
"""
```

### C.4.3. User prompt template update

```python
USER_PROMPT_PG_PLAN_TEMPLATE = """SQL запрос:
```sql
{sql_text}
```

PostgreSQL execution plan:
```
{plan_text}
```

Контекст конфигурации 1С: {configuration_context}

Уже обнаруженные антипаттерны от sqlglot:
{detected_antipatterns_json}

Стандартные SET-команды клиента 1С-PG:
- SET enable_mergejoin = off
- SET cpu_operator_cost = 0.001
- SET lock_timeout = 20000

Объясни план, дай recommendations с учётом найденных антипаттернов."""
```

### C.4.4. Flow integration

В PlanAnalyzer (frontend):
1. Юзер импортирует PG plan
2. Backend парсит, определяет engine="postgres"
3. **Параллельно** запускается:
   - PG antipatterns detection (быстро, локально)
   - AI explanation request (медленно, cloud)
4. Antipatterns показываются сразу (в плане secondary card)
5. AI response приходит позже — учитывая antipatterns context

## Acceptance criteria C.4

- [ ] PlanExplainRequest расширен detected_antipatterns
- [ ] PG SYSTEM prompt обновлён с antipatterns секцией
- [ ] Frontend параллельный вызов antipatterns + AI explain
- [ ] AI response учитывает antipatterns context (manual проверка на 2-3 примерах)

**Stop rule C.4:** Сергей открывает PG план с явным OFFSET без LIMIT → видит antipattern сразу + AI explanation учитывает это в recommendations.

**Длительность: 0.5 дня.**

---

# SUB-PHASE C.5 — Real-data tests + edge cases

## Цель

Прогон engine на реальных PG queries из pgBase + проверка edge cases.

## Шаги

### C.5.1. Real data corpus

Из `dbpostgrs_sample.log` (Phase A) extract все unique queries:

```python
import re
from collections import Counter

with open("tools/sprint8_discovery/pg_tj_samples/dbpostgrs_sample.log", "r") as f:
    content = f.read()

sql_pattern = re.compile(r'Sql="([^"]+?)",planSQLText=', re.DOTALL)
queries = sql_pattern.findall(content)

unique_queries = list(set(queries))
print(f"Total: {len(queries)}, Unique: {len(unique_queries)}")
```

Cохранить уникальные queries в `backend/src/optimyzer_backend/sql_antipatterns/tests/fixtures/pg_real_queries.json`.

### C.5.2. pg_stat_statements queries

```bash
$env:PGPASSWORD = "1111"
psql -U postgres -h localhost -d pgBase -c \
  "COPY (SELECT query FROM pg_stat_statements WHERE query NOT LIKE 'explain%' LIMIT 200) TO STDOUT" \
  > tools/sprint8_discovery/pg_stat_top_queries.txt
```

Сохранить top-200 reales queries из pg_stat_statements.

### C.5.3. Real-data integration test

```python
# tests/postgres/test_real_pg_queries.py

@pytest.mark.parametrize("query", load_real_queries())
def test_real_pg_query_processed_without_crash(query):
    findings = detect_antipatterns(query, engine="postgres")
    # No crash — это уже success
    assert isinstance(findings, list)
```

### C.5.4. Edge cases

- Multi-statement queries (`SELECT ...; SELECT ...`)
- CTE с recursive (`WITH RECURSIVE ...`)
- Window functions (`SUM() OVER (...)`)
- JSONB operations (`col -> 'key' ->> 'subkey'`)
- LATERAL joins
- UNION ALL chains
- Очень длинные queries (>10000 chars)
- Queries с inline comments (`-- ...` и `/* ... */`)
- Comments-only edge case
- Empty query / whitespace-only

### C.5.5. Performance benchmark

Для типичной PG query (~ 200 chars):
- Target: < 50 ms per detector call
- Target: < 100 ms для всех 15 детекторов на одной query
- Test: 1000 queries за < 60 секунд

## Acceptance criteria C.5

- [ ] 100+ real PG queries из pgBase обработаны без crash
- [ ] All 10 edge case classes покрыты тестами
- [ ] Performance bench passing (< 100 ms full pipeline)
- [ ] Backend tests > 850 (Phase B baseline + ~60 новых)

**Stop rule C.5:** `pytest backend/ -v` показывает 850+ tests, real-data integration не падает.

**Длительность: 1 день.**

---

# SUB-PHASE C.6 — Documentation + closure + final tag

## Цель

Закрытие Sprint 8 финальной документацией и tag `v0.8.0-internal` (без -pg-core-internal suffix).

## Документы

### C.6.1. SPRINT_8_FINAL_REPORT.md

Полный отчёт по всему Sprint 8 (Phase A + B + C) в `docs/sales_sprint/SPRINT_8_FINAL_REPORT.md`:

```markdown
# Sprint 8 — PostgreSQL Support (Final Report)

**Tag:** v0.8.0-internal
**Sub-tags:** v0.8.0-pg-core-internal (Phase B)
**Длительность:** 3 phases

## Sprint 8 Achievement Summary

- Phase A: PG Discovery — нашли DBPOSTGRS events, planSQLText в TEXT format, pgBase extensions
- Phase B: PG Plan Analyzer Core — tj_parser DBPOSTGRS, PlanAnalyzer dispatcher, AI split, re-EXPLAIN, pev2
- Phase C: PG Antipatterns Engine — 15 detectors, 1С-context awareness, AI integration

## Metrics

- Backend tests: 687 → ~850 (+163)
- Server tests: 22 → ~36 (+14)
- Frontend tests: 0 → 23 (+23, new infra)
- New PG-aware components: 4 (planSQLText engine, antipatterns engine, re-EXPLAIN service, pev2 wrapper)

## What works now

[Список E2E flows]

## Limitations

[Что не работает]

## Tech debt

[Items для следующих Sprints]
```

### C.6.2. ADRs

- **ADR-045** — sql_antipatterns module (renamed from tsql_antipatterns), structure для dialects
- **ADR-046** — 1С-context detection heuristic (regex patterns vs proper parser)
- **ADR-047** — Parallel detection + AI flow (sqlglot fast local + cloud AI slow)
- **ADR-048** — Sprint 8 closure без Phase D (planSQLText XML converter отменён — для PG это уже TEXT)

### C.6.3. README + NOTICE update

- README: добавить PostgreSQL support announcement (Plan Analyzer + Query Analyzer)
- NOTICE.md: уже есть sqlglot attribution (MIT, Toby Mao)

### C.6.4. Documentation files

- `docs/user-guide/postgresql-support.md` — user guide для PG users
  - Как настроить logcfg.xml для DBPOSTGRS events
  - Как добавить PG connection в Settings
  - Что значит каждый из 15 PG antipatterns

### C.6.5. Final tag

```bash
git tag -d v0.8.0-pg-core-internal  # remove intermediate
git tag -a v0.8.0-internal -m "Sprint 8: PostgreSQL Support — Plan Analyzer + Query Analyzer + Antipatterns"
git push --tags
```

Existing tag `v0.8.0-pg-core-internal` остаётся как milestone marker для Phase B closure.

## Acceptance criteria C.6

- [ ] SPRINT_8_FINAL_REPORT.md написан
- [ ] 4 ADRs добавлены в DECISIONS.md
- [ ] README обновлён с PG announcement
- [ ] User guide создан
- [ ] Tag v0.8.0-internal pushed

**Длительность: 0.5 дня.**

---

# Итоговый Definition of Done Sprint 8 Phase C

- [ ] sql_antipatterns module renamed без regression
- [ ] 15 PG detectors реализованы
- [ ] 1С-context detection работает
- [ ] sqlglot postgres dialect parsing работает
- [ ] Engine dispatcher по mssql/postgres
- [ ] QueryAnalyzer UI показывает PG antipatterns
- [ ] AI prompt учитывает detected antipatterns
- [ ] Real-data tests на pgBase data passing
- [ ] Backend tests > 850
- [ ] Documentation + 4 ADRs
- [ ] Tag v0.8.0-internal pushed
- [ ] **Sprint 8 полностью закрыт**

---

# Что НЕ делать в Phase C

- НЕ строить SDBL parser для PG — bsl-language-server Sprint 6 уже работает
- НЕ интегрировать pg_stat_statements ingestion — Sprint 11+
- НЕ менять existing T-SQL antipatterns logic — backward compat
- НЕ объединять Phase C с Sprint 9 (Testing) — Sprint 8 закрывается этим
- НЕ делать manual UI demo session — это отдельный шаг после Phase C

---

# После закрытия Sprint 8

**Manual demo session с Сергеем (отдельный шаг):**
- E2E на pgBase: загрузить архив с DBPOSTGRS → импортировать план → QueryAnalyzer + PlanAnalyzer + AI explanation + antipatterns
- 30-минутный smoke test, фиксация багов в SPRINT_8_BUGS.md если найдены

**Sprint 9 — Deep Real-world Testing + tj-simulator расширение:**
- tj-simulator: 10+ кнопок для разных сценариев нагрузки (включая PG)
- Golden corpus 50+ SDBL/SQL queries
- Performance benchmarks на больших архивах
- AI quality regression testing

---

# Если есть вопросы

Сергей разрешил задавать вопросы перед началом. Возможные:

- **Q: какие topN PG antipatterns priority?** → Все 15 равноценные в Phase C, начинай с CRITICAL (#14 MissingWhereOnUpdateDelete), потом WARNING, потом INFO
- **Q: что если 1С-context detection дает false positive?** → Сейчас не блокер, можем доработать heuristic после real-data testing
- **Q: какие PG версии поддерживаем?** → PG 14+ (Memoize) до PG 18.1 (текущий pgBase). Если parser упадёт на PG 12 — Sprint 11
- **Q: SQL parsing failures?** → Каждый детектор обернут в try/except — один сломанный не валит весь анализ

---

**Подготовил:** Claude Opus 4.7 (Architect)
**Для:** Claude Code (executor)
**Дата:** 2026-05-25
**Версия:** Sprint 8 Phase C v1
**База:** Phase A + Phase B reports (закрыты), real pgBase data
**Длительность:** 5-6 дней (одна сессия)
**Tag goal:** v0.8.0-internal (финальный Sprint 8)
**Следующий sprint:** Sprint 9 (Deep Real-world Testing + tj-simulator expansion)
