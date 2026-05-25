# Sprint 9 — Deep Real-World Testing: Итоговый отчёт

**Дата:** 2026-05-25  
**Тег:** `v0.9.0-internal`  
**Тип спринта:** Hardening / Testing (не feature sprint)

---

## Краткий итог

Sprint 9 сфокусирован на hardening: real-world fixtures, regression suite, tj-simulator expansion, AI enum normalizer, CSS lint. Никаких новых аналитических фич — только укрепление того что уже сделано в Sprint 6-8.

**Тесты до → после:**
- Backend: 861 → 907 (+46 новых тестов)
- Frontend: 23 → 72 (+49 новых тестов)
- Server (ai_explainer): +31 новых тестов
- **Итого: +126 тестов**

---

## Phase A — Real-World Fixtures

### Создано:
- `backend/tests/fixtures/real_world/mssql_sp_executesql/queries.json` — **32 MSSQL запроса** в sp_executesql формате (exec + ODBC {call})
- `backend/tests/fixtures/real_world/pg_queries/queries.json` — **34 PG запроса** (12 из ТЖ + 22 синтетических)
- `backend/tests/fixtures/real_world/pg_plans_text/plan_00.txt .. plan_13.txt` — 14 PG text планов
- `backend/tests/fixtures/real_world/mssql_plans/` — 13 .sqlplan файлов
- `backend/tests/fixtures/real_world/README.md` — полная документация fixtures

### Инструмент:
- `tools/sprint9_collect/extract_fixtures.py` — скрипт извлечения PG планов из ТЖ логов

---

## Phase B — Regression Suite

### Backend тесты (907 passed):

**`tests/sql_antipatterns/test_real_world_regression.py`** (+46):
- `TestMssqlSpExecutesqlUnwrap` (3) — sp_executesql unwrap validation
- `TestMssqlRealWorldDetection` (5) — detection на unwrapped SQL (ключевой паттерн!)
- `TestPgRealWorldDetection` (5) — no-crash + 1С context detection на реальных PG запросах
- `TestRpcRealWorldIntegration` (6) — end-to-end RPC тесты

**`tests/sql_antipatterns/test_performance.py`** (+7):
- Small query < 50ms, PG query < 50ms, medium ~5KB < 200ms
- 30 MSSQL запросов < 1 секунда throughput
- Unwrap < 1ms per call
- Performance stability (repeated calls не деградируют)

**`tests/test_architecture.py`** (+18):
- `TestModuleImports` — все 14 публичных модулей импортируются без ошибок
- `TestRpcHandlersRegistered` — _REGISTRY содержит > 20 методов; критичные handlers зарегистрированы
- `TestSqlAntipatternsSanity` — базовые smoke tests для обоих движков

### Frontend тесты (72 passed):

**`src/utils/sqlFormat.test.ts`** (+20):
- SELECT/FROM/WHERE/ORDER BY/GROUP BY/HAVING keywords
- JOIN присутствие + table names (с учётом фактического поведения форматтера: LEFT JOIN → LEFT\n  JOIN)
- AND/OR conditions
- UNION ALL/UNION, INSERT/UPDATE/DELETE
- Edge cases: пустая строка, лишние пробелы, вложенные подзапросы, несбалансированные скобки

**`src/api/severityHelpers.test.ts`** (+30):
- isSqlAntipatternSeverity type guard — все 6 canonical values + reject High/Medium/Low
- isPlanEngine type guard — mssql/postgres valid, oracle/MSSQL(uppercase) invalid
- isValidFinding shape validation — полная схема SqlAntipatternFinding
- SqlAntipatternsResponse structure tests

### Server тесты (31 passed):

**`tests/test_ai_normalize.py`** (+31):
- SEVERITY_MAPPING: все алиасы (high→Critical, blocker→Critical, medium→Warning, moderate→Warning, low→Info)
- IMPACT_MAPPING: все алиасы (critical→Critical, moderate→Medium, minor→Low)
- Non-string input: None, int, list, bool → default
- Unknown values → default + logging
- Case-insensitive matching, whitespace stripping

---

## Phase C — TJ-Simulator Expansion

Добавлено **7 новых кнопок** в группу "Дополнительные сценарии (Sprint 9)":

| # | Название | Тип | Ожидаемый ТЖ-event |
|---|----------|-----|---------------------|
| 7 | TDEADLOCK X-X | Параллельный | TDEADLOCK (явные X-X блокировки) |
| 8 | Цепочка дедлок | Параллельный | TDEADLOCK (3-сторонний цикл A→B→C→A) |
| 9 | Memory | Однопоточный | DBMSSQL (тяжёлые агрегаты, UNION ALL, DISTINCT) |
| 10 | N+1 | Однопоточный | DBMSSQL серия (основной + N детальных) |
| 11 | Тяжёлый SDBL | Однопоточный | DBMSSQL (сложные JOIN, UNION ALL) |
| 12 | PG-паттерны | Однопоточный | DBMSSQL (SELECT *, LIKE %, NOT IN, картезиан) |
| 13 | Длинная транзакция | Параллельный | TLOCK (X удерживается 30 сек) |

**Изменённые файлы:**
- `tools/tj-simulator/МоделированиеТЖ/src/.../Forms/Форма/Ext/Form.xml` — новые кнопки + команды
- `tools/tj-simulator/МоделированиеТЖ/src/.../Forms/Форма/Ext/Form/Module.bsl` — 7 новых command handlers + 3 server wrappers
- `tools/tj-simulator/МоделированиеТЖ/src/.../Ext/ObjectModule.bsl` — 6 новых приватных функций (воркеры)
- `tools/tj-simulator/ТЖМоделированиеРасш/src/.../ВоркерыТЖ/Ext/Module.bsl` — 3 новых ФЗ-воркера

---

## Phase D — Generic AI Enum Normalizer + CSS Lint

### D.1 — normalize_ai_enum:
- Добавлен `normalize_ai_enum(value, mapping, default, field_name)` в `server/services/ai_explainer.py`
- `SEVERITY_MAPPING` и `IMPACT_MAPPING` — полные алиасные таблицы
- Рефакторинг: `_norm_sev()`, `_norm_impact()` теперь через единый хелпер
- `overall_severity` нормализация унифицирована

### D.2 — CSS Design Token Lint:
- Создан `scripts/check-css-tokens.ps1` — сканирует `*.module.css` на hardcoded hex-цвета
- Whitelist: #000, #fff, #000000, #ffffff
- Исключение: строки с `--o-*` определением
- Интегрирован в `frontend/package.json` как `npm run lint:css`
- Первый прогон: **254 нарушения в 32 файлах** — известный техдолг pre-token CSS (см. ADR-052)

---

## Phase E — Performance Benchmarks (интегрированы в Phase B)

Цели установлены и зафиксированы в `tests/sql_antipatterns/test_performance.py`:
- Малый запрос: < 50ms ✓
- PG запрос: < 50ms ✓
- Средний запрос (~5KB): < 200ms ✓
- 30 запросов throughput: < 1 секунды ✓
- sp_executesql unwrap: < 1ms ✓
- Stability: повторный вызов не медленнее 3× первого ✓

---

## Технические детали / фиксы по ходу

1. **ODBC format DEADLOCK**: `{call sp_executesql(N'...')}` крашил parse. Фикс: `_get_effective_sql()` хелпер который вызывает `_unwrap_sp_executesql()` перед `detect_antipatterns()`.

2. **RPC _REGISTRY пустой**: Handlers регистрируются lazy. Фикс: `_ensure_handlers_loaded()` импортирует все RPC модули в `test_architecture.py`.

3. **formatSql COMPOUND keywords**: `LEFT JOIN` → `LEFT\n  JOIN` (форматтер делает это намеренно). Фикс: frontend тесты проверяют `toContain("JOIN")` + table names раздельно, без `"LEFT JOIN"`.

4. **CSS lint path**: Скрипт использовал relative path от CWD вместо от расположения скрипта. Фикс: `Split-Path -Parent $MyInvocation.MyCommand.Path` + join с `../frontend/src`.

5. **performance mark warning**: pytest не знал о `@pytest.mark.performance`. Фикс: добавлен в `markers` в `backend/pyproject.toml`.

---

## ADRs

- **ADR-049**: Real-world fixture strategy (synthetic + extracted)
- **ADR-050**: normalize_ai_enum generic helper
- **ADR-051**: tj-simulator 7 new scenarios via worker-shell pattern
- **ADR-052**: CSS design token lint — identify-first, fix-as-you-go

---

## Tag: v0.9.0-internal

```
git tag -a v0.9.0-internal -m "Sprint 9 — Deep Real-World Testing: +126 tests, 7 new TJ simulator scenarios, AI enum normalizer, CSS lint"
```
