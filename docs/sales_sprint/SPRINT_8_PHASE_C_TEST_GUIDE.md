# Sprint 8 Phase C — Полная инструкция по тестированию

> Документ для **Сергея** — пошаговая проверка PG antipatterns engine + интеграции в PlanAnalyzer.
> Используется для manual demo session после Phase C.

---

## 0. Подготовка окружения

### 0.1. Запуск Optimyzer

```powershell
cd D:\1C-Optimyzer
.\start.bat
```

Дождитесь полной загрузки UI (открывается Tauri window).

### 0.2. (Опционально) Запуск server для AI

Для тестирования AI интеграции с antipatterns:

```powershell
# В отдельном окне PowerShell
cd D:\1C-Optimyzer\server
.\start.ps1  # или manual: uvicorn api.main:app --port 8001
```

В `server/.env` должен быть валидный `ANTHROPIC_API_KEY=sk-...`. Без него AI карточка покажет «AI отключён» — это OK для тестов antipatterns без AI.

### 0.3. (Опционально) PG connection для re-EXPLAIN

Если хотите тестировать re-EXPLAIN через pev2:

1. Откройте **Настройки → Подключения → PostgreSQL**
2. Добавьте: `host=localhost, port=5432, database=pgBase, user=postgres, password=1111`
3. Нажмите «Проверить» — должно вернуть «PG 18.1-2.1C, 1С-build ✓»

---

## 1. Automated тесты (быстрая проверка backend)

Выполните перед manual тестами:

```powershell
# Backend tests — 80 sql_antipatterns + 25 legacy T-SQL
D:\1C-Optimyzer\backend\.venv\Scripts\python.exe -m pytest `
  D:\1C-Optimyzer\backend\tests\sql_antipatterns\ `
  D:\1C-Optimyzer\backend\tests\sql\test_antipatterns.py `
  -v
```

**Expected:** `105 passed in ~2s`.

```powershell
# Server tests — Phase C AI integration
cd D:\1C-Optimyzer\server
.\.venv\Scripts\python.exe -m pytest tests\test_ai_explain_pg_plan.py -v
```

**Expected:** `20 passed`.

Если хоть один тест fail — это блокер manual тестирования.

---

## 2. Manual тест #1 — Smoke test через Python

Быстрая проверка что engine работает изолированно (без UI):

```powershell
D:\1C-Optimyzer\backend\.venv\Scripts\python.exe -c "
from optimyzer_backend.sql_antipatterns import detect_antipatterns

# Каждый из 15 PG детекторов
queries = [
    ('SELECT * FROM _document201 OFFSET 100', 'offset_without_limit'),
    ('SELECT * FROM tbl OFFSET 50000 LIMIT 10', 'large_offset_pagination'),
    (\"SELECT id FROM tbl WHERE n ILIKE '%abc%'\", 'ilike_without_trgm'),
    (\"SELECT id FROM tbl WHERE n LIKE '%abc'\", 'like_with_leading_wildcard'),
    ('SELECT id FROM tbl WHERE id NOT IN (SELECT y FROM other)', 'not_in_with_subquery_pg'),
    (\"SELECT id FROM tbl WHERE data @> '{}'::jsonb\", 'jsonb_without_gin'),
    (\"SELECT id FROM tbl WHERE LOWER(name) = 'abc'\", 'cast_in_where_predicate'),
    ('SELECT a FROM t1 UNION SELECT a FROM t2', 'union_instead_of_union_all'),
    ('SELECT id, (SELECT MAX(x) FROM other WHERE other.fk = main.id) FROM main', 'subquery_in_select_list'),
    ('SELECT DISTINCT a FROM t1 JOIN t2 ON t1.id=t2.id', 'distinct_on_large_result'),
    (\"SELECT * FROM tbl WHERE id = '123'\", 'implicit_type_cast'),
    ('SELECT * FROM a JOIN b ON a.id=b.id', 'select_star_with_join'),
    ('SELECT * FROM tbl ORDER BY RANDOM() LIMIT 10', 'order_by_random_with_limit'),
    ('UPDATE tbl SET a = 1', 'missing_where_on_update_delete'),
    ('DELETE FROM tbl', 'missing_where_on_update_delete'),
]
for q, expected in queries:
    findings = detect_antipatterns(q, engine='postgres')
    codes = [f.code for f in findings]
    print(f\"{'OK' if expected in codes else 'FAIL'} {expected}\")
"
```

**Expected:** 15 строк, все `OK`.

---

## 3. Manual тест #2 — UI с paste'нутым SQL планом

### 3.1. Открыть PlanAnalyzer

`Ctrl+P` или Sidebar → **Анализатор плана**.

### 3.2. Вставить PG план

Tab «Вставить XML» → вставить:

```
EXPLAIN ANALYZE
SELECT _IDRRef, _Description
FROM _Reference15
WHERE _Description ILIKE '%test%'
OFFSET 5000 LIMIT 10
```

Жмёте «Анализировать».

### 3.3. Что должно появиться

1. **Карточка «AI-объяснение плана»** — idle state с кнопкой «Получить AI объяснение»
2. **Карточка «Антипаттерны SQL (N)»** — N ≥ 2:
   - Engine badge: **PostgreSQL** (зелёный)
   - 1С-context badge: **1С-контекст** (жёлтый) — потому что `_Reference15` matched
   - Находки (click для раскрытия):
     - `ilike_without_trgm` — Warning
     - `large_offset_pagination` — Warning
     - `like_with_leading_wildcard` — Info (downgrade в 1С context)
3. **Plan text view** ниже — сырой план

### 3.4. Раскрыть findings

Кликните на каждый — должны увидеть:
- **«Что произошло»** — описание
- **«Почему это проблема»** — rationale
- **«Что сделать»** — recommendation
- **snippet** — фрагмент SQL (если есть)

### 3.5. Запустить AI (опционально)

Нажмите «Получить AI объяснение» в верхней карточке. Через 5-15 секунд:
- AI **НЕ должен** дублировать `ilike_without_trgm` / `large_offset_pagination` в hotspots
- AI **должен** расширить контекст плана (например про Seq Scan, Buffers, Memoize)
- В summary должна быть ссылка на 1С-контекст (`_Reference15` = Справочник)

---

## 4. Manual тест #3 — Импорт PG плана из ТЖ архива

### 4.1. Предусловие — есть архив ТЖ с DBPOSTGRS events

Если нет — сначала включите:

```powershell
# Включает <plansql/> для DBPOSTGRS события (idempotent)
.\scripts\patch-logcfg-for-plans.ps1

# Сгенерировать нагрузку через tj-simulator (если нет реальной)
# или просто использовать существующий архив
```

### 4.2. Загрузить архив

Sidebar → **Архивы** → **Открыть архив/папку** → выберите архив с DBPOSTGRS events.

### 4.3. PlanAnalyzer → Tab «Из архива ТЖ»

- В фильтре «Движок» выберите **PostgreSQL** (или «Все»)
- Должен быть список планов с badge **PG** (зелёный)
- Кликните любой план

### 4.4. Что должно появиться

Аналогично п. 3.3 — только источник: `ТЖ архив · event #N · PostgreSQL`. **Антипаттерны SQL** карточка автоматически анализирует SQL запроса.

### 4.5. Запустить re-EXPLAIN (требует PG connection)

В `PgPlanTextView` будет кнопка **«Получить интерактивный план»**. Нажмите:
- Optimyzer открывает транзакцию с 1С-PG настройками
- Делает `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`
- Возвращает JSON → рендерит через pev2
- В UI появляется интерактивная диаграмма плана (можно навигировать по операторам)

Внизу — кнопка «← Вернуться к текстовому плану» для отката.

---

## 5. Manual тест #4 — 1С-context awareness

### 5.1. Запрос с 1С таблицами

```sql
SELECT _IDRRef
FROM _Document201
WHERE _Fld11355 = 'test'
  AND _Description::mvarchar = $1::mvarchar
ORDER BY _Date DESC
LIMIT 100
```

**Expected:**
- 1С-context badge показывается
- `mchar_vs_text_comparison` НЕ flagged (обе стороны mvarchar — это правильно)
- `cast_in_where_predicate` НЕ flagged для `::mvarchar` (1С-aware skip)
- `implicit_type_cast` НЕ flagged для `_Fld11355 = 'test'` (1С _Fld* skip)
- `select_star_with_join` ничего не показывает (нет SELECT *)

### 5.2. Запрос смешивающий mchar и text

```sql
SELECT _IDRRef
FROM _Reference15
WHERE _Description::mchar = '1'::text
```

**Expected:**
- 1С-context badge показывается
- `mchar_vs_text_comparison` flagged — Warning
- `cast_in_where_predicate` НЕ flagged

### 5.3. Запрос без 1С context

```sql
SELECT * FROM users a JOIN orders b ON a.id = b.user_id
```

**Expected:**
- 1С-context badge **НЕ показывается**
- `select_star_with_join` flagged — Info

---

## 6. Manual тест #5 — T-SQL backward compatibility

Через PlanAnalyzer — Tab «Вставить XML»:

```sql
SELECT * FROM dbo.[_Reference15]
WHERE _IDRRef NOT IN (SELECT _RecorderRRef FROM dbo.[_AccumRg200])
```

**Expected:**
- Engine badge: **MS SQL** (синий)
- 1С-context badge показывается (`_reference15` matched через regex с dbo. префиксом)
- Находки:
  - `not_in_with_subquery` — Major (legacy T-SQL детектор)
  - `select_star` — Minor

---

## 7. Performance smoke test

Открыть browser DevTools (Ctrl+Shift+I в Tauri) → Network tab.

Импортировать любой план → проверить timing вызова `sql_antipatterns.detect`:

**Expected:** ≤ 100ms даже на сложных запросах.

---

## 8. Проверка documentation

### 8.1. Файлы есть на диске

```powershell
ls D:\1C-Optimyzer\docs\sales_sprint\SPRINT_8_FINAL_REPORT.md
ls D:\1C-Optimyzer\docs\user-guide\postgresql-support.md
ls D:\1C-Optimyzer\docs\DECISIONS.md
```

### 8.2. Git tag присутствует

```powershell
cd D:\1C-Optimyzer
git tag -l "v0.8.0*"
git log --oneline v0.8.0-internal | head -5
```

**Expected:**
```
v0.8.0-internal
v0.8.0-pg-core-internal
```

---

## 9. Что фиксировать как баг

Создайте файл `docs/sales_sprint/SPRINT_8_BUGS.md` если найдёте:

- ❌ Crash в любом сценарии (PlanAnalyzer / RPC / AI)
- ❌ Antipattern не обнаруживается там где должен (false negative)
- ❌ Antipattern flagged там где не должен (false positive — особенно для 1С context)
- ❌ AI ответ дублирует уже обнаруженные antipatterns (Claude не следует инструкции)
- ❌ pev2 не рендерит JSON / показывает ошибку
- ❌ re-EXPLAIN таймаут / не подключается
- ❌ UI глитч (badge не показывается, expand не работает, etc)

Формат записи:
```markdown
## Bug #N — [короткое описание]
**Severity:** Critical / High / Medium / Low
**Шаги воспроизведения:**
1. ...
**Expected:** ...
**Actual:** ...
**Screenshot:** (если есть)
```

---

## 10. Финальный чеклист

После прохождения всех manual тестов проверьте:

- [ ] Все 15 PG детекторов работают (тест #2)
- [ ] PlanAnalyzer показывает карточку antipatterns с paste'нутым SQL (тест #3)
- [ ] Импорт из ТЖ архива работает + antipatterns детектятся (тест #4)
- [ ] re-EXPLAIN → pev2 работает (опционально, требует PG connection)
- [ ] 1С-context awareness работает (тест #5)
- [ ] T-SQL backward compat не сломан (тест #6)
- [ ] AI integration: ответ учитывает detected antipatterns (опционально)
- [ ] Performance < 100ms на типичном запросе (тест #7)
- [ ] Documentation на диске + tag pushed (тест #8)

Если всё ✓ — Sprint 8 фактически закрыт, можно переходить к Sprint 9.
