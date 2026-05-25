# PostgreSQL support — руководство пользователя

Optimyzer поддерживает оба движка СУБД 1С: **MS SQL Server** и **PostgreSQL** (в т.ч. 1С-сборка PostgreSQL). Это руководство покрывает PG-specific настройку и использование.

---

## 1. Включение planSQLText в logcfg.xml

Чтобы Optimyzer мог читать планы PG-запросов из tech journal, нужно настроить сбор события `DBPOSTGRS` с полем `planSQLText`.

В `logcfg.xml` добавить:

```xml
<event>
  <eq property="Name" value="DBPOSTGRS"/>
  <ge property="Duration" value="10000"/>
  <property name="all"/>
</event>
```

Автоматизация — в проекте есть готовый скрипт:

```powershell
.\scripts\patch-logcfg-for-plans.ps1
```

Скрипт идемпотентен: если событие уже настроено — не дублирует. После запуска перезапускать 1С не нужно (logcfg перечитывается раз в 60 секунд).

---

## 2. Подключение PG базы для re-EXPLAIN (опционально)

Re-EXPLAIN — это feature который позволяет получить интерактивную визуализацию плана через pev2. Без подключения PG базы Optimyzer покажет только текстовый план из ТЖ.

### 2.1. Добавить PG connection в Settings

1. **Настройки → Подключения → PostgreSQL → Добавить**
2. Заполнить: host, port (default 5432), database, username, password
3. Нажать «Проверить» — Optimyzer выполнит `SELECT version()` чтобы убедиться что connection работает
4. Сохранить

Пароль хранится в OS keychain (Windows Credential Manager / macOS Keychain / Linux secret service), **не в plaintext SQLite** (см. ADR-044).

### 2.2. Рекомендации по безопасности

Создайте отдельного PG пользователя для Optimyzer с **read-only** правами:

```sql
CREATE USER optimyzer_readonly WITH PASSWORD 'strong-password';
GRANT CONNECT ON DATABASE pgbase TO optimyzer_readonly;
GRANT USAGE ON SCHEMA public TO optimyzer_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO optimyzer_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO optimyzer_readonly;
```

Optimyzer дополнительно блокирует DML/DDL на уровне `safety.py` (см. `backend/src/optimyzer_backend/pg/safety.py`) — `INSERT/UPDATE/DELETE/DROP/CREATE` будут отклонены до отправки в PG.

### 2.3. Re-EXPLAIN flow

После подключения, в PlanAnalyzer при импорте плана PG-запроса появится кнопка **«Получить интерактивный план»**. Она:
1. Берёт `sql_text` из импортированного ТЖ event
2. Делает safety check — отклоняет всё кроме SELECT/WITH
3. Открывает транзакцию с `SET LOCAL enable_mergejoin = off`, `SET LOCAL cpu_operator_cost = 0.001`, `SET LOCAL statement_timeout`
4. Запускает `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`
5. Возвращает JSON план → рендерит через pev2 (Vue Web Component)

---

## 3. Анализ плана PG-запроса

После импорта плана из ТЖ (или paste'а EXPLAIN output) Optimyzer параллельно запускает:

1. **SQL antipatterns engine** (мгновенно, локально) — карточка «Антипаттерны SQL» с 15 PG-specific детекторами
2. **AI explanation** (по кнопке, ~10-20 секунд) — Claude Sonnet 4.5 с PG-specific промптом + 1С знаниями (enable_mergejoin=off, mchar/mvarchar, naming convention)

Antipatterns передаются в AI как `detected_antipatterns` context — Claude учитывает их в рекомендациях и НЕ дублирует.

### 3.1. Каталог 15 PG антипаттернов

| # | Code | Severity | Что обнаруживает |
|---|---|---|---|
| 1 | `offset_without_limit` | Warning | `OFFSET N` без LIMIT — лишнее сканирование |
| 2 | `large_offset_pagination` | Warning/Critical | Глубокое OFFSET (>1000 — Warning, >10000 — Critical) |
| 3 | `ilike_without_trgm` | Warning | `ILIKE '%text%'` без pg_trgm — Seq Scan |
| 4 | `like_with_leading_wildcard` | Warning | `LIKE '%text'` — недоступен b-tree |
| 5 | `not_in_with_subquery_pg` | Warning | `NOT IN (SELECT ...)` — NULL-trap + slow |
| 6 | `jsonb_without_gin` | Info | JSONB операции — намёк проверить GIN |
| 7 | `cast_in_where_predicate` | Warning | CAST/функция на колонке — non-SARGable |
| 8 | `union_instead_of_union_all` | Info | UNION с implicit SORT+UNIQUE |
| 9 | `subquery_in_select_list` | Warning | Correlated subquery в SELECT (N+1) |
| 10 | `distinct_on_large_result` | Info | DISTINCT + JOIN — часто дубликаты от 1:N |
| 11 | `implicit_type_cast` | Warning | `int_col = '123'` — implicit cast ломает индекс |
| 12 | `select_star_with_join` | Info | `SELECT * + JOIN` — лишние колонки |
| 13 | `order_by_random_with_limit` | Warning/Critical | `ORDER BY RANDOM()` — full sort |
| 14 | `missing_where_on_update_delete` | **Critical** | `UPDATE/DELETE без WHERE` — массовая операция |
| 15 | `mchar_vs_text_comparison` | Warning | 1С: mismatched mchar vs text типы |

### 3.2. 1С-context awareness

Engine автоматически определяет 1С-context по таблицам (`_reference\d+`, `_document\d+`, ...) и типам (`mchar`, `mvarchar`). В 1С-context:

- **`like_with_leading_wildcard`** — severity снижается до Info (1С часто использует для подстрочного поиска)
- **`select_star_with_join`** — детектор отключается (1С НИКОГДА не делает SELECT *)
- **`cast_in_where_predicate`** — пропускает cast в mchar/mvarchar/fulleq (1С-extension типы)
- **`implicit_type_cast`** — пропускает `_Fld\d+` колонки (стандартные 1С идентификаторы)
- **`mchar_vs_text_comparison`** — активен ТОЛЬКО в 1С context

В UI показывается badge «1С-контекст» в карточке антипаттернов.

---

## 4. Troubleshooting

### Q: «PG connection недоступно» при тесте

Проверьте:
- PG service запущен (`Get-Service postgresql-x64-*`)
- `pg_hba.conf` разрешает подключения от вашего IP
- Username + password правильные
- Firewall не блокирует порт 5432

### Q: «re-EXPLAIN: unsafe_query»

`safety.py` блокирует всё кроме SELECT/WITH. Если получаете эту ошибку на SELECT — проверьте что в SQL нет CTE с UPDATE/DELETE внутри.

### Q: «AI explanation: ai_not_configured»

Добавьте `ANTHROPIC_API_KEY=sk-...` в `.env` файл сервера и перезапустите server. См. `server/README.md`.

### Q: pev2 не загружается

pev2 + Vue runtime бандлятся в frontend (~185 KB gz). Если виден только текстовый план — обновите Optimyzer (`v0.8.0-internal` и новее).

### Q: Запрос не парсится — `parse_error` badge

Возможные причины:
- Запрос обрезан в логах TJ (max length ~10000 символов в 1С)
- Engine неправильный (выбран PG для T-SQL запроса от MSSQL connector)
- Очень экзотический PG синтаксис

Для multi-engine баз: в QueryAnalyzer / PlanAnalyzer можно вручную сменить engine через dropdown.

---

## 5. Связанные документы

- `docs/onboarding/enable-plansqltext.md` — настройка ТЖ для сбора планов
- `docs/configuration/pg-connection-setup.md` — детальный setup PG подключения
- `docs/DECISIONS.md` — ADR-041..048 (архитектурные решения Sprint 8)
- `docs/sales_sprint/SPRINT_8_FINAL_REPORT.md` — итоговый отчёт Sprint 8
