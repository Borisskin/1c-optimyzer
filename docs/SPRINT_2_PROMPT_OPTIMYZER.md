# Sprint 2 — Performance Investigation Workbench

> **Контекст:** Module 1 (OptimyzerQL Standalone) был paused после Sprint 1, теперь **reactivated** на основе нового стратегического решения. См. `docs/PROJECT_REACTIVATION_SPRINT_2.md`.
>
> **Главная стратегическая цель:** превратить OptimyzerQL Standalone в **полноценный performance investigation workbench** — готовый продукт для портфолио + применения на реальных production-кластерах 1С при трудоустройстве.
>
> **Working directory:** `D:\1C-Optimyzer\1c-optimyzer\`
> **Branch:** `feat/sprint-2-investigation-workbench` (от `main`, который содержит `v0.1.0-internal`)

---

## 1. Контекст и решения

### Что изменилось со Sprint 1

После Sprint 1 и closure project был paused в maintenance mode. В рамках strategic re-evaluation владелец принял решение:

1. **Reactivate проект** — не выбрасывать готовый код, а **довести до полноценного product-ready состояния** для портфолио и применения в найме
2. **Удалить OQL DSL полностью** — заменить на raw SQL. SQL знают все 1С-эксперты, OQL не имеет адекватного value proposition для standalone-tool без brand эффекта
3. **Сделать tool максимально полезным как investigation workbench** — pre-built views под главные сценарии performance engineer'а
4. **Multi-archive comparison** — киллер-фича для демонстрации на собеседованиях (сравнение производительности до/после релиза)

### Новые ADR (фиксируются в Sprint 2)

**ADR-015: Remove OQL DSL, replace with raw SQL**

Решение: полностью удалить Lark grammar, parser, AST, compiler, validator, RPC methods для OQL. Заменить на прямое выполнение SQL против DuckDB.

Обоснование:
- OQL предполагал быть killer feature как "DataDog query language for 1C". Без активного бренд-маркетинга (Module 2+, который paused) это просто dialect которому пользователи не имеют мотивации учиться.
- SQL — universal language, известный всем 1С-экспертам и DBA.
- Maintenance двух языков (OQL + SQL alias) удваивает complexity.
- Saved queries из Sprint 1 переписываются на SQL — это однократная работа.

**ADR-016: Pre-built Views as Primary UI**

Решение: главный UX продукта — не SQL editor (для power users), а **набор pre-built analytical views** под типичные performance investigation сценарии. SQL editor становится secondary tab для специфичных query.

Обоснование:
- 80% типичных задач performance engineer'а: Top Slow Queries, Locks Analysis, Process Roles, Errors Feed, Activity Patterns — могут быть решены **готовыми views без написания SQL**.
- Demo на собеседовании: "вот загрузил архив за 4 часа prod-нагрузки, вот Top 20 slow queries, вот deadlock pattern" — drag-and-drop + clicks, не SQL writing.
- Custom SQL остаётся в отдельной вкладке для power users.

**ADR-017: Cross-Filtering Across Views**

Решение: все views имеют общий filter state (time range, process role, event type). При выборе фильтра в одном view — все views переключаются.

Обоснование:
- Главная боль 1С performance engineer'а — найти **корреляции**: spike в lock conflicts ↔ memory growth ↔ slow queries в этот же момент. Изолированные views не дают эту картину.
- Cross-filtering позволяет drilling down: кликнул на пик в Locks Timeline → Top Slow Queries автоматически фильтруется на этот же интервал → видна root cause.

**ADR-018: Multi-Archive Comparison**

Решение: добавить возможность одновременной загрузки **двух** архивов с side-by-side comparison views и diff visualization.

Обоснование:
- Главный business use case в найме: "релизнули новую версию, провалилась производительность, найди регрессию". Comparison views отвечают на это **прямо**, без необходимости писать SQL.
- Конкурентов с этой фичей на нашем уровне детализации нет (1С:ЦКК делает comparison на уровне agregated metrics, не event-level).

**ADR-019: Read-Only SQL Execution**

Решение: SQL editor выполняет только SELECT statements. INSERT/UPDATE/DELETE/CREATE/DROP/ALTER блокируются на уровне validation перед execution.

Обоснование:
- Tool — analytical, не data manipulation.
- Защита от случайного destructive query пользователем.
- DuckDB поддерживает read-only mode connections — используем.

---

## 2. Структура изменений

### Backend

```
backend/src/optimyzer_backend/
├── oql/                                  УДАЛИТЬ ВЕСЬ ПАКЕТ
│   (grammar.lark, parser.py, ast.py, compiler.py, validator.py, 
│    functions.py, templates.py)
│
├── sql/                                  NEW
│   ├── __init__.py
│   ├── executor.py                       SQL execution с timeout + size limits
│   ├── validator.py                      Whitelist SELECT only, block DDL/DML
│   ├── templates.py                      Pre-built SQL templates (15-20 шт)
│   └── schema_introspection.py           List tables/columns для autocomplete
│
├── views/                                NEW — pre-built analytical views
│   ├── __init__.py
│   ├── base.py                           Common filtering, pagination
│   ├── slow_queries.py
│   ├── locks_timeline.py
│   ├── process_roles.py
│   ├── duration_histogram.py
│   ├── errors_feed.py
│   ├── activity_heatmap.py
│   └── multi_archive.py                  Compare two archives
│
├── rpc/
│   ├── oql_rpc.py                        УДАЛИТЬ
│   ├── sql_rpc.py                        NEW (execute_sql, validate_sql, get_schema)
│   ├── views_rpc.py                      NEW (RPC для каждой pre-built view)
│   ├── multi_archive_rpc.py              NEW (load_second_archive, compare_*)
│   └── archive_rpc.py                    UPDATE (поддержка multi-archive state)
│
├── storage/
│   └── duckdb_store.py                   UPDATE: read-only connections, 
│                                          возможность держать две архивы одновременно
│
└── tests/
    ├── test_sql_executor.py              NEW
    ├── test_sql_validator.py             NEW  
    ├── test_views_*.py                   NEW (один файл на каждую view)
    ├── test_multi_archive.py             NEW
    └── test_sprint2_real_data.py         Real-data acceptance
```

### Frontend

```
frontend/src/
├── codemirror/
│   ├── oql-language.ts                   УДАЛИТЬ
│   ├── oql-autocomplete.ts               УДАЛИТЬ
│   ├── oql-linter.ts                     УДАЛИТЬ
│   ├── oql-theme.ts                      УДАЛИТЬ
│   ├── sql-language.ts                   NEW (использует @codemirror/lang-sql)
│   ├── sql-autocomplete.ts               NEW (table/column names из schema)
│   └── sql-theme.ts                      NEW
│
├── components/
│   ├── charts/                           NEW
│   │   ├── BarChart.tsx                  Recharts wrapper (теал style)
│   │   ├── LineChart.tsx
│   │   ├── HeatmapChart.tsx
│   │   ├── HistogramChart.tsx
│   │   ├── ScatterChart.tsx
│   │   └── DonutChart.tsx
│   │
│   ├── filters/                          NEW — cross-filtering UI
│   │   ├── TimeRangeFilter.tsx
│   │   ├── ProcessRoleFilter.tsx
│   │   ├── EventTypeFilter.tsx
│   │   └── FilterBar.tsx                 Общая полоса фильтров над всеми views
│   │
│   ├── screens/
│   │   ├── OQLConsole/                   ПЕРЕИМЕНОВАТЬ → SQLConsole/
│   │   │   ├── OQLConsole.tsx            → SQLConsole.tsx
│   │   │   ├── Editor.tsx                UPDATE: SQL вместо OQL
│   │   │   └── ...
│   │   │
│   │   ├── SlowQueries/                  NEW
│   │   ├── LocksTimeline/                NEW
│   │   ├── ProcessRoles/                 NEW
│   │   ├── DurationHistogram/            NEW
│   │   ├── ErrorsFeed/                   NEW
│   │   ├── ActivityHeatmap/              NEW
│   │   └── ArchiveComparison/            NEW (multi-archive)
│   │
│   └── chrome/
│       └── Sidebar.tsx                   UPDATE: enable 7 views, oql переименовать
│
├── store/
│   └── appStore.ts                       UPDATE: cross-filter state, 
│                                          multi-archive state
│
├── i18n/
│   └── ru.ts                             UPDATE: новые strings для всех views
│
└── api/
    └── backend.ts                        UPDATE: новые RPC methods
```

---

## 3. Phases

### Phase A — OQL removal

Чистый remove всего OQL-related кода. Без миграционных слоёв.

**A1. Backend:**
- Удалить пакет `backend/src/optimyzer_backend/oql/` целиком
- Удалить `rpc/oql_rpc.py`
- В `__main__.py` убрать импорт и регистрацию `oql_rpc`
- В `pyproject.toml` / `requirements.txt` удалить `lark` если только OQL его использовал
- Запустить тесты — убедиться что **все pytest** проходят, тесты OQL уже удалены

**A2. Frontend:**
- Удалить `frontend/src/codemirror/oql-*.ts`
- В `package.json` оставить `@codemirror/*` пакеты (используются для SQL)
- Удалить из `frontend/src/api/backend.ts` методы `executeOqlQuery`, `validateOqlQuery`, `listTemplates` (последний переедет в SQL templates)

**A3. Saved queries migration:**
- В `saved_queries` SQLite table — переименовать колонку `oql_text` → `sql_text` (если такое имя было)
- Существующие saved queries — пометить флагом `legacy_oql = 1` и сохранить как есть (для возможного manual rewrite, но в UI не отображать)
- Альтернатива: просто очистить таблицу saved_queries (Sergei решает — есть ли там что-то ценное из Sprint 1)

**A4. Tests after removal:**
- Все Sprint 1 tests которые тестировали OQL — удалить из codebase
- Acceptance tests которые использовали OQL queries — переписать на SQL (Phase D после Pre-built views будут готовы)

**Acceptance Phase A:**
- `git grep -i "oql"` — возвращает только references в docs/ADR-009..014/PROJECT_CLOSURE (исторические)
- Все oставшиеся pytest зелёные
- Приложение запускается, OQL Console отображает **временную заглушку** "переходим на SQL — phase B"

### Phase B — SQL Engine

#### B1. SQL Executor (`backend/sql/executor.py`)

```python
import time
from typing import Any
import duckdb
from ..storage.duckdb_store import DuckDBStore

class SQLExecutionError(Exception):
    pass

class SQLExecutor:
    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_MAX_ROWS = 100_000
    
    def __init__(self, archive_id: str, read_only: bool = True):
        self.store = DuckDBStore.for_archive(archive_id, read_only=read_only)
    
    def execute(self, sql: str, timeout_s: int = None, max_rows: int = None) -> dict:
        timeout_s = timeout_s or self.DEFAULT_TIMEOUT_SECONDS
        max_rows = max_rows or self.DEFAULT_MAX_ROWS
        
        start = time.monotonic()
        
        try:
            # DuckDB supports query timeout через PRAGMA
            self.store.conn.execute(f"SET statement_timeout = '{timeout_s}s'")
            
            result = self.store.conn.execute(sql)
            rows = result.fetchmany(max_rows + 1)  # +1 чтобы детектить truncation
            
            truncated = len(rows) > max_rows
            if truncated:
                rows = rows[:max_rows]
            
            columns = [(d[0], str(d[1])) for d in result.description]
        
        except duckdb.Error as e:
            raise SQLExecutionError(f"Ошибка выполнения SQL: {e}")
        
        elapsed_ms = (time.monotonic() - start) * 1000
        
        return {
            "columns": [{"name": n, "type": t} for n, t in columns],
            "rows": [list(r) for r in rows],
            "row_count": len(rows),
            "truncated": truncated,
            "executed_ms": round(elapsed_ms, 1),
        }
```

#### B2. SQL Validator (`backend/sql/validator.py`)

Использовать **sqlparse** для парсинга, проверять что:
- Только SELECT statements (top-level)
- Никаких DDL: CREATE/DROP/ALTER/TRUNCATE
- Никаких DML: INSERT/UPDATE/DELETE/MERGE
- Никаких system functions: ATTACH/DETACH/COPY/EXPORT
- WITH ... AS (CTEs) разрешены (только SELECT внутри)

```python
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML, DDL

ALLOWED_TOP_LEVEL = {'SELECT', 'WITH'}
BLOCKED_KEYWORDS = {
    'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'TRUNCATE',
    'CREATE', 'DROP', 'ALTER', 'GRANT', 'REVOKE',
    'ATTACH', 'DETACH', 'COPY', 'EXPORT', 'IMPORT',
    'PRAGMA', 'SET', 'CALL', 'EXECUTE',
}

def validate_sql(sql: str) -> tuple[bool, str | None]:
    """Returns (is_valid, error_message)."""
    if not sql or not sql.strip():
        return False, "Пустой запрос"
    
    try:
        parsed = sqlparse.parse(sql)
    except Exception as e:
        return False, f"Не удалось распарсить SQL: {e}"
    
    if not parsed:
        return False, "Не удалось распарсить SQL"
    
    if len(parsed) > 1:
        # Multiple statements — нужно проверить что все SELECT
        # Простейшая проверка через ; в нормализованной форме
        # (для Sprint 2 — отклоняем множественные statements полностью)
        non_empty = [s for s in parsed if s.tokens and any(t for t in s.tokens if t.ttype is not None or hasattr(t, 'tokens'))]
        if len(non_empty) > 1:
            return False, "Поддерживается только один SQL statement за раз"
    
    stmt = parsed[0]
    
    # Получить первый non-whitespace, non-comment token верхнего уровня
    first_keyword = None
    for token in stmt.tokens:
        if token.ttype is None and hasattr(token, 'tokens'):
            # Это группа — пропускаем
            continue
        if token.is_whitespace:
            continue
        if token.ttype in (sqlparse.tokens.Comment.Single, sqlparse.tokens.Comment.Multiline):
            continue
        if token.ttype is Keyword or token.ttype is DML:
            first_keyword = token.value.upper()
            break
    
    if first_keyword not in ALLOWED_TOP_LEVEL:
        return False, f"Разрешены только SELECT (и WITH) запросы. Найдено: {first_keyword}"
    
    # Проверяем что нет blocked keywords в основном тексте
    sql_upper = sql.upper()
    for blocked in BLOCKED_KEYWORDS:
        # Ищем как слово (с границами)
        import re
        if re.search(rf'\b{blocked}\b', sql_upper):
            return False, f"Запрещённое ключевое слово: {blocked}. Разрешены только SELECT."
    
    return True, None
```

#### B3. Schema Introspection (`backend/sql/schema_introspection.py`)

```python
def get_schema(archive_id: str) -> dict:
    """Возвращает структуру таблиц для autocomplete."""
    store = DuckDBStore.for_archive(archive_id, read_only=True)
    
    tables = store.conn.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
    """).fetchall()
    
    result = {}
    for (table_name,) in tables:
        columns = store.conn.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()
        
        result[table_name] = [
            {"name": name, "type": dtype} for name, dtype in columns
        ]
    
    return result
```

#### B4. SQL RPC (`backend/rpc/sql_rpc.py`)

```python
@rpc.method('execute_sql')
def execute_sql(archive_id: str, sql: str, max_rows: int = 10000) -> dict:
    """Execute SQL against archive's DuckDB."""
    is_valid, error = validate_sql(sql)
    if not is_valid:
        return {"ok": False, "error": error, "phase": "validate"}
    
    try:
        executor = SQLExecutor(archive_id, read_only=True)
        result = executor.execute(sql, max_rows=max_rows)
        return {"ok": True, **result}
    except SQLExecutionError as e:
        return {"ok": False, "error": str(e), "phase": "execute"}


@rpc.method('validate_sql')
def validate_sql_rpc(sql: str) -> dict:
    """Static validation for debounced typing in editor."""
    is_valid, error = validate_sql(sql)
    return {"ok": is_valid, "error": error}


@rpc.method('get_schema')
def get_schema_rpc(archive_id: str) -> dict:
    """Return tables/columns structure for autocomplete."""
    return get_schema(archive_id)
```

#### B5. CodeMirror SQL setup (frontend)

Использовать `@codemirror/lang-sql` — уже есть готовая поддержка SQL syntax, autocomplete keywords. Расширяем для DuckDB-specific:

```typescript
// frontend/src/codemirror/sql-language.ts
import { sql, SQLDialect } from '@codemirror/lang-sql';

// DuckDB-specific dialect
const duckdbDialect = SQLDialect.define({
  keywords: 'select from where group by having order limit offset join inner left right outer cross on as and or not in like between is null asc desc distinct count sum avg min max with case when then else end union all',
  operatorChars: '+-*/<>!=~|&^%',
  specialVar: '?',
});

export function makeSqlExtension(schema: Record<string, Array<{name: string, type: string}>>) {
  // Schema передаётся для autocomplete table.column hints
  const schemaForLangSql = {};
  for (const [table, cols] of Object.entries(schema)) {
    schemaForLangSql[table] = cols.map(c => c.name);
  }
  
  return sql({
    dialect: duckdbDialect,
    schema: schemaForLangSql,
    upperCaseKeywords: true,
  });
}
```

#### B6. SQL Console (renamed from OQL Console)

Frontend компонент `SQLConsole.tsx` — почти точно повторяет старый `OQLConsole.tsx`, но:
- Filename `untitled.sql` вместо `untitled.oql`
- Editor использует SQL extension
- Run button вызывает `execute_sql` RPC
- Templates panel заменена на новые SQL templates (Phase D)
- Doс panel содержит SQL reference + список колонок events table

**Acceptance Phase B:**
- В SQL Console можно написать `SELECT * FROM events LIMIT 10` → нажать Ctrl+Enter → получить таблицу с 10 строками
- Запрос `INSERT INTO events ...` → отклоняется с понятной ошибкой
- Autocomplete показывает имена колонок events после набора `SELECT `
- Schema RPC возвращает структуру events table

### Phase C — Charts library

Recharts уже в design system (есть в shared.jsx Sprint 0). Делаем production-ready wrappers с правильной стилизацией.

**C1. BarChart, LineChart, HistogramChart, HeatmapChart, ScatterChart, DonutChart** — каждый с:
- Деflate теал цвет (`#0F766E`) primary
- JetBrains Mono для tooltip values (моноширинный consistent с tabular-nums)
- Inter для axis labels  
- Subtle grid `#EDEDED`
- Hover state с tooltip
- Responsive sizing (fill parent container)
- Custom legends когда нужны

**C2. Empty state и error state** — если данных нет / запрос упал → корректный пустой график с message, не crash.

**Acceptance Phase C:**
- Каждый chart-компонент рендерится с mock data
- Storybook не нужен, но в `frontend/src/components/charts/__demo__/` создать страницу-демо для visual testing

### Phase D — Pre-built Views

Каждая view = отдельная страница (Sidebar item) + backend SQL query + frontend visualization.

#### D1. Top Slow Queries

**Path:** `/views/slow-queries`
**Sidebar:** "Медленные запросы" — было `queries` disabled, теперь enabled

**Backend (`views/slow_queries.py`):**

```python
def get_slow_queries(
    archive_id: str,
    time_range: tuple[str, str] | None = None,
    process_role: str | None = None,
    limit: int = 100,
    sort_by: str = 'total_duration',  # 'avg_duration' | 'total_duration' | 'count'
) -> dict:
    """Топ медленных SQL запросов с агрегацией по sql_text_hash."""
    
    sql = """
        SELECT 
            sql_text_hash,
            sql_text_normalized AS query,
            COUNT(*) AS calls,
            SUM(duration_us) / 1000.0 AS total_duration_ms,
            AVG(duration_us) / 1000.0 AS avg_duration_ms,
            MAX(duration_us) / 1000.0 AS max_duration_ms,
            SUM(rows_read) AS total_rows_read,
            MIN(ts) AS first_seen,
            MAX(ts) AS last_seen,
            COUNT(DISTINCT process_role) AS process_roles_count,
            STRING_AGG(DISTINCT process_role, ', ') AS process_roles
        FROM events
        WHERE archive_id = ?
          AND event_type = 'DBMSSQL'
          AND sql_text_normalized IS NOT NULL
    """
    params = [archive_id]
    
    if time_range:
        sql += " AND ts >= ? AND ts <= ?"
        params.extend(time_range)
    
    if process_role:
        sql += " AND process_role = ?"
        params.append(process_role)
    
    sort_column = {
        'total_duration': 'total_duration_ms',
        'avg_duration': 'avg_duration_ms',
        'count': 'calls',
    }.get(sort_by, 'total_duration_ms')
    
    sql += f"""
        GROUP BY sql_text_hash, sql_text_normalized
        ORDER BY {sort_column} DESC
        LIMIT ?
    """
    params.append(limit)
    
    executor = SQLExecutor(archive_id, read_only=True)
    return executor.execute_raw(sql, params)
```

**Frontend (`SlowQueries.tsx`):**
- Header с filters: time range, process role, sort selector
- Main table: rank, query (truncated, hover для full text), calls, total time, avg time, max time, rows read
- Каждая строка clickable → opens drawer справа с full query, statistics chart (histogram of durations), related events feed
- Bottom: pagination

#### D2. Locks Timeline

**Path:** `/views/locks`
**Sidebar:** "Блокировки"

**Backend (`views/locks_timeline.py`):**
- Bucket events `TLOCK` and `TDEADLOCK` по minute или hour buckets (зависит от time range)
- Возвращает time series с count per bucket
- Отдельный endpoint для drill-down: получить все lock events за конкретный bucket

**Frontend:**
- LineChart (timeline) с двумя series: TLOCK count, TDEADLOCK count
- Time range selector
- Click на bar → opens drawer с list событий из этого bucket
- Right panel: текущий summary (total locks, total deadlocks, top contended objects если можно извлечь из payload)

#### D3. Process Roles Distribution

**Path:** `/views/process-roles`
**Sidebar:** "Роли процессов"

**Backend:**
```sql
SELECT 
    process_role,
    COUNT(*) AS events_count,
    SUM(duration_us) / 1000.0 AS total_duration_ms,
    COUNT(DISTINCT process_pid) AS unique_processes,
    AVG(duration_us) / 1000.0 AS avg_duration_ms
FROM events
WHERE archive_id = ?
GROUP BY process_role
ORDER BY events_count DESC
```

**Frontend:**
- Главный chart: DonutChart с распределением events_count по ролям
- Right side: table с разбивкой metrics per role
- Click на сегмент donut → фильтрует все другие views на этот process role (cross-filter)

#### D4. Duration Histogram

**Path:** `/views/duration`
**Sidebar:** "Распределение длительностей"

**Backend:**
- Создаёт buckets duration: <1ms, 1-10ms, 10-100ms, 100-1000ms, 1-10s, 10-60s, >60s
- Возвращает count per bucket
- Опционально breakdown по event_type или process_role

**Frontend:**
- HistogramChart с logarithmic Y axis
- Toggle: All events / DBMSSQL only / CALL only / etc.
- Tooltip: count + percentage от total
- Click на bucket → drawer с примерами событий из этого bucket

#### D5. Errors/Exceptions Feed

**Path:** `/views/errors`
**Sidebar:** "Ошибки и исключения"

**Backend:**
```sql
SELECT 
    ts,
    event_type,
    process_role,
    process_pid,
    context,
    duration_us / 1000.0 AS duration_ms,
    extra,
    source_file,
    source_line_start
FROM events
WHERE archive_id = ?
  AND event_type IN ('EXCP', 'TDEADLOCK', 'TLOCK')
ORDER BY ts DESC
LIMIT 1000
```

**Frontend:**
- Scrollable feed event-by-event
- Каждый event: timestamp, type badge (red для EXCP/TDEADLOCK, amber для TLOCK), context (1С-модуль), expand для full extra JSON
- Filter: by event_type, by process_role, by context (substring search)

#### D6. Activity Heatmap

**Path:** `/views/activity`
**Sidebar:** "Активность"

**Backend:**
- Aggregate events по (day_of_week, hour_of_day)
- Возвращает 7×24 grid с metrics: count, total_duration, peak_duration

**Frontend:**
- HeatmapChart 7×24, color intensity = метрика
- Selector: метрика = count / total_duration / peak_duration / error_count
- Click на cell → time range filter применяется ко всем views

**Acceptance Phase D:**
- Все 6 views работают на 12 GiB архиве за <3 секунды (DuckDB должна справиться, проверить с помощью EXPLAIN ANALYZE если медленно)
- Каждая view имеет drill-down (drawer с подробностями)
- Filters работают на каждой view индивидуально

### Phase E — Cross-Filtering

Это **главная архитектурная фича** Sprint 2, превращающая dashboard в workbench.

**E1. Shared filter state (`appStore.ts`)**

```typescript
type CrossFilters = {
  archive_id: string | null;
  time_range: [string, string] | null;  // ISO timestamps
  process_role: string | null;
  event_type: string | null;
  source_view: string | null;  // какая view последняя выставила фильтры
};

// Все views читают этот state и подгружают данные с учётом фильтров.
// Любая view может set фильтры через action.
```

**E2. FilterBar (`components/filters/FilterBar.tsx`)**

Постоянная панель сверху каждой view с активными filter chips:
- "Время: 14:30 — 15:00 [×]"
- "Процесс: rphost [×]"
- "Тип: DBMSSQL [×]"
- "Очистить все"

Клик на × — снимает фильтр, view re-rendered.

**E3. Cross-filter interactions**

| Action в view | Filter применяется |
|---|---|
| Click bar в Locks Timeline | time_range = bucket interval |
| Click cell в Activity Heatmap | time_range = day+hour interval |
| Click segment в Process Roles Donut | process_role = selected |
| Click row в Top Slow Queries | (no filter, opens drawer instead) |
| Click event в Errors Feed | time_range = ±5min от event |

**E4. Reactive view refresh**

Все views subscribe на CrossFilters через Zustand. При изменении фильтра — re-fetch data.

Backend каждый view-RPC method принимает optional filters в payload:

```python
class ViewRequest(BaseModel):
    archive_id: str
    time_range: tuple[str, str] | None = None
    process_role: str | None = None
    event_type: str | None = None
    # ... view-specific параметры
```

**Acceptance Phase E:**
- В Activity Heatmap кликнул на cell (например четверг 14:00) → переходим в Locks Timeline → видим только locks из этого часа
- В Locks Timeline кликнул на spike → переходим в Top Slow Queries → видим только queries из этого интервала
- В Process Roles кликнул на rphost → все views (Slow Queries, Locks, Duration, Errors, Activity) фильтруют по rphost
- "Clear all" возвращает к полному dataset
- Filter chips correctly отображают active filters

### Phase F — Templates Library

Pre-built SQL templates для quick start. Заменяют старые OQL templates.

**`backend/sql/templates.py`:**

```python
TEMPLATES = [
    {
        "id": "top_slow_sql",
        "category": "performance",
        "label": "Топ 100 медленных SQL запросов",
        "sql": """
SELECT 
    sql_text_normalized,
    COUNT(*) AS calls,
    SUM(duration_us)/1000.0 AS total_ms,
    AVG(duration_us)/1000.0 AS avg_ms,
    MAX(duration_us)/1000.0 AS max_ms
FROM events
WHERE event_type = 'DBMSSQL'
GROUP BY sql_text_normalized
ORDER BY total_ms DESC
LIMIT 100;
        """.strip(),
    },
    {
        "id": "deadlocks_by_hour",
        "category": "locks",
        "label": "Дедлоки по часам",
        "sql": """
SELECT 
    date_trunc('hour', ts) AS hour,
    COUNT(*) AS deadlocks
FROM events
WHERE event_type = 'TDEADLOCK'
GROUP BY hour
ORDER BY hour;
        """.strip(),
    },
    {
        "id": "events_by_role_and_type",
        "category": "stats",
        "label": "Распределение событий по ролям и типам",
        "sql": """
SELECT 
    process_role,
    event_type,
    COUNT(*) AS cnt
FROM events
GROUP BY process_role, event_type
ORDER BY process_role, cnt DESC;
        """.strip(),
    },
    {
        "id": "top_contexts_slow",
        "category": "performance",
        "label": "Самые медленные 1С-контексты (модули/процедуры)",
        "sql": """
SELECT 
    context,
    COUNT(*) AS calls,
    SUM(duration_us)/1000.0 AS total_ms,
    AVG(duration_us)/1000.0 AS avg_ms
FROM events
WHERE context IS NOT NULL
GROUP BY context
ORDER BY total_ms DESC
LIMIT 50;
        """.strip(),
    },
    {
        "id": "memory_heavy_events",
        "category": "memory",
        "label": "События с высоким потреблением памяти",
        "sql": """
SELECT 
    ts,
    event_type,
    process_role,
    process_pid,
    context,
    json_extract(extra, '$.Memory') AS memory,
    json_extract(extra, '$.MemoryPeak') AS memory_peak
FROM events
WHERE json_extract(extra, '$.Memory') IS NOT NULL
ORDER BY CAST(json_extract(extra, '$.MemoryPeak') AS BIGINT) DESC NULLS LAST
LIMIT 100;
        """.strip(),
    },
    {
        "id": "exceptions_feed",
        "category": "errors",
        "label": "Поток исключений",
        "sql": """
SELECT 
    ts,
    process_role,
    context,
    json_extract(extra, '$.Exception') AS exception,
    json_extract(extra, '$.Descr') AS description
FROM events
WHERE event_type = 'EXCP'
ORDER BY ts DESC
LIMIT 200;
        """.strip(),
    },
    {
        "id": "locks_top_resources",
        "category": "locks",
        "label": "Топ заблокированных ресурсов",
        "sql": """
SELECT 
    json_extract(extra, '$.Regions') AS resource,
    COUNT(*) AS lock_events,
    SUM(CASE WHEN json_extract(extra, '$.WaitConnections') IS NOT NULL THEN 1 ELSE 0 END) AS wait_count
FROM events
WHERE event_type = 'TLOCK'
GROUP BY resource
ORDER BY lock_events DESC
LIMIT 50;
        """.strip(),
    },
    {
        "id": "activity_by_hour",
        "category": "stats",
        "label": "Активность по часам суток",
        "sql": """
SELECT 
    EXTRACT(hour FROM ts) AS hour_of_day,
    COUNT(*) AS events,
    SUM(duration_us)/1000.0 AS total_ms,
    SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exceptions
FROM events
GROUP BY hour_of_day
ORDER BY hour_of_day;
        """.strip(),
    },
    {
        "id": "long_running_calls",
        "category": "performance",
        "label": "Длинные server calls (>10 сек)",
        "sql": """
SELECT 
    ts,
    process_role,
    context,
    duration_us/1000.0 AS duration_ms,
    json_extract(extra, '$.Memory') AS memory
FROM events
WHERE event_type IN ('CALL', 'SCALL')
  AND duration_us > 10000000
ORDER BY duration_us DESC
LIMIT 100;
        """.strip(),
    },
    {
        "id": "sessions_overview",
        "category": "stats",
        "label": "Обзор сеансов пользователей",
        "sql": """
SELECT 
    session_id,
    user_name,
    COUNT(*) AS events,
    SUM(duration_us)/1000.0 AS total_ms,
    MIN(ts) AS first_event,
    MAX(ts) AS last_event,
    COUNT(DISTINCT context) AS unique_contexts
FROM events
WHERE session_id IS NOT NULL
GROUP BY session_id, user_name
ORDER BY total_ms DESC
LIMIT 100;
        """.strip(),
    },
    # ... ещё 5-10 templates по тем же категориям (performance, locks, errors, memory, stats)
]


@rpc.method('list_sql_templates')
def list_templates() -> list[dict]:
    return TEMPLATES
```

**Frontend:**
- Templates dropdown в SQLConsole header
- Categories tabs (performance / locks / errors / memory / stats)
- Click template → load в editor

### Phase G — Multi-Archive Comparison

Главная новая фича Sprint 2 для портфолио. Демо-сценарий: "релизнули новую версию УТ, провалилась производительность, сравни до/после".

#### G1. Backend: open two archives simultaneously

`DuckDBStore` supports множественные одновременные connections (each archive в своём `.duckdb` файле).

`appStore` (Python) держит state:
```python
class ArchiveSlot(BaseModel):
    archive_id: str | None = None
    archive_name: str | None = None
    loaded_at: datetime | None = None
    events_count: int | None = None

class AppState:
    archive_a: ArchiveSlot
    archive_b: ArchiveSlot  # optional, для comparison
```

`load_directory` принимает параметр `slot: 'a' | 'b'`. По default — `'a'`. Для второй загрузки — `'b'`.

#### G2. Comparison RPC methods

```python
@rpc.method('compare_slow_queries')
def compare_slow_queries(filters: ComparisonFilters) -> dict:
    """Сравнение топ медленных запросов между двумя архивами."""
    queries_a = get_slow_queries(archive_id_a, ...)
    queries_b = get_slow_queries(archive_id_b, ...)
    
    # Match by sql_text_hash
    diff = compute_diff(queries_a, queries_b, key='sql_text_hash')
    
    return {
        "in_both": [...],   # queries в обоих архивах, с delta metrics
        "only_in_a": [...], # были в A, исчезли в B
        "only_in_b": [...], # появились в B, не было в A
        "regressed": [...], # avg_ms вырос >50% в B vs A
        "improved": [...],  # avg_ms упал >50%
    }


@rpc.method('compare_summary')
def compare_summary() -> dict:
    """High-level diff: total events, errors, durations."""
    return {
        "events_count": {"a": ..., "b": ..., "delta_percent": ...},
        "total_duration_ms": {"a": ..., "b": ..., "delta_percent": ...},
        "errors_count": {"a": ..., "b": ..., "delta_percent": ...},
        "deadlocks_count": {"a": ..., "b": ..., "delta_percent": ...},
        "avg_duration_ms": {"a": ..., "b": ..., "delta_percent": ...},
    }


@rpc.method('compare_durations_distribution')
def compare_durations() -> dict:
    """Distribution buckets для обоих архивов."""
    ...


@rpc.method('compare_errors')
def compare_errors() -> dict:
    """Новые типы исключений в B которых не было в A."""
    ...
```

#### G3. UI: Archive Comparison page

**Path:** `/comparison`
**Sidebar:** "Сравнение" — было `compare` disabled, теперь enabled

**Layout:**

Top panel:
```
┌──────────────────────────────────────────────────────────────┐
│  Архив A (Baseline)        │  Архив B (Compared)              │
│  УТ 11.5.18.230            │  УТ 11.5.18.235                  │
│  📁 D:\logs\before-release │  📁 D:\logs\after-release        │
│  12 mln events             │  14 mln events                   │
│  загружен 14:30            │  загружен 15:12                  │
│  [Сменить...]              │  [Сменить...]                    │
└──────────────────────────────────────────────────────────────┘
```

Summary panel (high-level diff):
```
┌──────────────────────────────────────────────────────────────┐
│  Общий обзор изменений                                       │
│  ┌──────────────┬──────────┬──────────┬─────────────┐      │
│  │ Метрика      │ Baseline │ Compared │ Изменение   │      │
│  ├──────────────┼──────────┼──────────┼─────────────┤      │
│  │ События      │ 12.4M    │ 14.2M    │ +14.5% ↑    │      │
│  │ Длительность │ 4.5 hrs  │ 5.8 hrs  │ +28% ↑ 🔴   │      │
│  │ Исключения   │ 234      │ 387      │ +65% ↑ 🔴   │      │
│  │ Дедлоки      │ 12       │ 47       │ +291% ↑ 🔴  │      │
│  │ Средн. время │ 12ms     │ 18ms     │ +50% ↑ 🔴   │      │
│  └──────────────┴──────────┴──────────┴─────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

Tabs внизу:
- **Slow Queries Diff** — таблица: query, baseline avg, compared avg, delta. Sorted by regression magnitude. Highlight rows where delta > +50% (regression) or < -30% (improvement)
- **Errors Diff** — новые типы exceptions, исчезнувшие, увеличившиеся в частоте
- **Process Roles Diff** — изменения распределения нагрузки между rphost/rmngr/etc
- **Duration Histogram Diff** — overlay двух гистограмм
- **Contexts Diff** — какие 1С-модули/процедуры стали медленнее

Каждый tab — interactive, с drill-down.

**Acceptance Phase G:**
- Можно загрузить два разных архива (например один из реальных 12 GiB и synthetic generated)
- Summary panel показывает корректные diff metrics
- Slow Queries Diff показывает regressions ranked по силе
- Click на regressed query → drawer с side-by-side execution stats baseline vs compared

### Phase H — Export

#### H1. Backend RPC

```python
@rpc.method('export_view_data')
def export_view_data(
    archive_id: str,
    view_name: str,
    filters: dict,
    format: str,  # 'csv' | 'xlsx' | 'json'
) -> dict:
    """Generates export file, returns path to download."""
    
    # 1. Run the view's query with current filters
    # 2. Generate file in temp dir
    # 3. Return path + size
    
    if format == 'csv':
        path = _generate_csv(...)
    elif format == 'xlsx':
        path = _generate_xlsx(...)  # use openpyxl
    elif format == 'json':
        path = _generate_json(...)
    
    return {"path": str(path), "size_bytes": path.stat().st_size}
```

#### H2. Frontend

В каждом view — button "Экспорт..." в header, dropdown CSV/XLSX/JSON.

Click → RPC call → backend generates → Tauri opens "Save As..." dialog → file сохранён в указанное место.

**Acceptance Phase H:**
- CSV export работает для всех 6 views
- XLSX содержит правильное formatting (headers bold, numeric columns aligned right)
- JSON содержит structured data + metadata

### Phase I — Sidebar update

Открыть views в Sidebar (раньше все были disabled с tooltip "Module N").

**До (Sprint 1):**
```
LIVE: oql (active), dashboard, apdex, workbench (all disabled)
ANALYZE: queries, locks, cluster, indexes, profiler (all disabled)
CONFIG: health, compare, predictive (all disabled)
MANAGE: resolution, multibase, knowledge, alerts, reports, mobile (all disabled)
```

**После (Sprint 2):**
```
LIVE: (empty - it was for Module 2)
ANALYZE: 
  - sql-console (active) — переименовано из oql
  - slow-queries (active)
  - locks (active)
  - process-roles (active, new id)
  - duration (active, new id)
  - errors (active, new id)
  - activity (active, new id)
CONFIG:
  - comparison (active)
MANAGE:
  - templates (active, new id) — управление SQL templates
  - saved (active, new id) — saved queries management
```

Disabled остаются: dashboard, apdex, workbench (Module 2 features), indexes, profiler (Module 4), cluster, health, predictive (Module 5+), resolution, multibase, knowledge, alerts, reports, mobile.

Tooltips для disabled: "Доступно в следующих модулях" (без указания конкретного Module N — мы pivot'нули roadmap).

### Phase J — Onboarding & UX polish

#### J1. Welcome screen (при первом запуске или если нет загруженных архивов)

```
┌─────────────────────────────────────────────────┐
│                                                 │
│         🔍 1C-Optimyzer                         │
│                                                 │
│   Инструмент анализа технологического           │
│   журнала 1С                                    │
│                                                 │
│   Чтобы начать:                                 │
│                                                 │
│   📁 Перетащите папку с логами ТЖ сюда          │
│      или                                        │
│   [ Выбрать папку... ]                          │
│                                                 │
│   Поддерживаемые форматы:                       │
│   - папки rphost_*/rmngr_*/ragent_*/1cv8*_*     │
│   - файлы YYMMDDHH.log внутри них               │
│                                                 │
│   Также можно загрузить:                        │
│   [ Демо-данные ] (synthetic, 100MB)            │
│                                                 │
└─────────────────────────────────────────────────┘
```

Кнопка "Демо-данные" — загружает synthetic-generated archive (есть в Sprint 1 `tests/fixtures/synthetic/generate_tj_logs.py`) — для пользователей которые хотят посмотреть как работает tool **до** того как идти за реальными логами.

#### J2. Empty state в каждой view (когда archive не загружен)

Каждая view имеет centered empty state: "Загрузите папку с логами, чтобы увидеть [Top Slow Queries / Locks Timeline / etc.]"

#### J3. Loading state

Когда RPC вызов в процессе — view показывает skeleton (subtle pulse-animation).

#### J4. Error states

Если RPC падает (SQL syntax error, DuckDB timeout, etc.) — readable error message + retry button.

#### J5. Keyboard shortcuts

Документировать в About / Help modal:
- Ctrl+K — Command palette
- Ctrl+Enter в SQL editor — execute query
- Ctrl+E — export current view
- Ctrl+1..9 — переключение между views

### Phase K — Real-data Acceptance Gate

`backend/tests/test_sprint2_real_data.py`:

```python
@pytest.mark.skipif(not REAL_FOLDER_PATH or not Path(REAL_FOLDER_PATH).exists(),
                    reason="OPTIMYZER_REAL_FOLDER_PATH not set")
class TestSprint2Acceptance:
    """Acceptance gate Sprint 2 на 12 GiB real archive.
    
    Critical: каждая view должна работать < 3 секунды.
    """
    
    def test_all_views_perform_under_3_seconds(self):
        # Load real archive
        # For each of 6 pre-built views: измерить время
        # Assert все < 3s
        pass
    
    def test_sql_executor_handles_complex_query(self):
        # Сложный JOIN/GROUP BY/window function
        pass
    
    def test_cross_filtering_propagates_correctly(self):
        # Set filters in one view, verify others получают filtered data
        pass
    
    def test_export_csv_for_slow_queries(self):
        # Export → проверить корректность файла
        pass
    
    def test_multi_archive_comparison_basic(self):
        # Загрузить два разных synthetic-archives (можно сгенерировать)
        # Run comparison
        # Assert корректный diff
        pass
```

---

## 4. Definition of Done — Sprint 2

| # | Criterion | Verification |
|---|---|---|
| 1 | OQL код удалён полностью (нет references в active codebase) | `git grep -i oql` returns only docs |
| 2 | SQL executor работает с read-only DuckDB | pytest |
| 3 | SQL validator блокирует INSERT/UPDATE/DELETE/DDL | pytest |
| 4 | CodeMirror SQL editor с autocomplete колонок | manual |
| 5 | Schema RPC возвращает все колонки events table | manual |
| 6 | Все 6 pre-built views работают: Slow Queries, Locks, Roles, Duration, Errors, Activity | manual + tests |
| 7 | Каждая view имеет filter controls + drill-down drawer | manual |
| 8 | Cross-filtering работает: фильтр из одной view применяется ко всем | manual |
| 9 | FilterBar показывает active filters с возможностью remove | manual |
| 10 | Multi-archive comparison: можно загрузить два архива одновременно | manual |
| 11 | Comparison summary показывает diff metrics с корректными цифрами | tests |
| 12 | Slow Queries Diff показывает regressions и improvements | manual |
| 13 | Templates library — 10+ SQL templates с категориями | pytest |
| 14 | Export CSV/XLSX/JSON работает из каждой view | manual |
| 15 | Welcome screen при первом запуске | manual |
| 16 | Empty/loading/error states в каждой view | manual |
| 17 | Sidebar показывает все Sprint 2 views как enabled | manual |
| 18 | Charts library: BarChart, LineChart, Heatmap, Histogram, Scatter, Donut работают | manual demo page |
| 19 | pytest суммарно ≥ 280 (Sprint 1 had 197, +80+ minimum) | CI |
| 20 | Conventional commits | git log |
| 21 | SPRINT_2_REPORT.md, ADR-015..019 обновлены | files |
| 22 | **ACCEPTANCE GATE:** Каждая view работает < 3 сек на 12 GiB архиве | env-gated pytest |
| 23 | **ACCEPTANCE GATE:** Cross-filtering propagation работает end-to-end | manual + pytest |
| 24 | **ACCEPTANCE GATE:** Multi-archive comparison на двух real archives | manual |
| 25 | **DEMO READINESS:** записан 5-7 минутный screen recording showing all features for portfolio | mp4 file |
| 26 | OPUS_HANDOVER_SPRINT_2.md подготовлен | file |

**Пункты 22, 23, 24, 25** — обязательные blocking gates. Sprint 2 не закрыт без них.

---

## 5. Что НЕ в Sprint 2 (явно отложено)

- **AI Co-pilot / natural language to SQL** — Module 2 (требует Anthropic API integration)
- **Real-time agents** — Module 2 (требует central server)
- **Investigation Workbench** (Sprint 1 design экран) — Module 3 (требует deep diff/timeline visualization)
- **BSL Profiler** — Module 4 (требует BSL parsing)
- **Production .msi installer** — Sprint 3 (если будет)
- **Onboarding tour overlay** — Sprint 3
- **License / public release** — Sprint 3 + decision

---

## 6. Дисциплина

- **Conventional commits**: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `test(scope):`, `docs:`, `chore:`
- **Один phase = атомарная единица работы** + коммит(ы)
- **Real-data testing обязателен**: на 12 GiB архиве проверять каждую view перед закрытием phase
- **Performance regression**: если view работает > 3 сек — оптимизировать (EXPLAIN ANALYZE, добавить индексы, переписать query) перед закрытием
- **Не оптимизировать преждевременно**: но не игнорировать medленность которая делает tool unusable

---

## 7. Замечания для Claude Code

- **Backward compatibility с Sprint 1 saved_queries**: если в saved_queries таблице есть legacy OQL queries — сохранить как `legacy_oql_*`, не показывать в UI, но не удалять (на всякий случай)
- **DuckDB read-only mode**: используется `duckdb.connect(path, read_only=True)`. Это **главная защита** от destructive queries даже если SQL validator пропустит что-то
- **Charts должны рендериться на Sprint 0 dataset**: для demo / acceptance test'ов используем synthetic generator. Synthetic data должна включать **достаточно разнообразия** для каждой view (несколько event_types, несколько process_roles, errors, deadlocks). Если synthetic generator из Sprint 1 не достаточен — расширить
- **Cross-filtering performance**: при изменении filter — re-fetch только active view (текущая), не все 6 одновременно. Other views re-fetch при switch на них. Это **lazy evaluation**.
- **Multi-archive memory**: две DuckDB одновременно = удвоение RAM. Должно работать на dev machine с 16 GB RAM. Если падает на 32 GB архивах — это для Sprint 3.

---

## 8. Финальное

Sprint 2 — **переход от Sprint 1's foundation к production-ready product**.

После Sprint 2 у Сергея:
- Полноценный performance investigation workbench
- Portfolio piece, готовый к demo на собеседовании
- Tool который можно применять в production (на работодателя) с первого дня

Стартуй: branch `feat/sprint-2-investigation-workbench`, Phase A → K последовательно. Удачи.

Главное — Sprint 2 закрывает Module 1 как **commercially viable product**. После него либо доводим до публикации (Sprint 3 — installer + onboarding + launch), либо tool остаётся как portfolio + internal tool в найме. Оба исхода — successful.
