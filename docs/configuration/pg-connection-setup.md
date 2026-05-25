# Настройка PostgreSQL подключения для интерактивных планов

> Sprint 8 Phase B (v0.8.0-pg-core-internal).
>
> Опциональная функция: даёт **интерактивную визуализацию** PG execution plans
> через [pev2](https://github.com/dalibo/pev2). Без неё PG-планы из ТЖ архива
> показываются как текст + AI-объяснение (Path A) — это базовый сценарий
> работает всегда.

## Зачем это нужно

При импорте PostgreSQL execution plan из ТЖ архива (DBPOSTGRS события)
Optimyzer получает план в **текстовом формате** — тот же что выдаёт
`EXPLAIN ANALYZE` в `psql`. Это работает и **без** PG подключения:
вы видите план с syntax-highlighted операторами + AI-объяснение.

Чтобы получить **интерактивную диаграмму** (как в [PgAdmin → Explain Visualizer](https://pgadmin.org)),
нужен JSON-формат плана (`EXPLAIN (FORMAT JSON, ANALYZE)`). 1С такой формат
в ТЖ **не** пишет (только текст). Поэтому Optimyzer **повторно выполняет**
EXPLAIN на стороне PG — для этого нужно подключение к вашей базе.

```
  ТЖ архив                  PG база (опционально)
  ┌────────────┐            ┌──────────────────┐
  │ DBPOSTGRS  │            │  re-EXPLAIN      │
  │ planSQLText│ → AI       │  FORMAT JSON     │
  │ (текст)    │            │  ANALYZE         │
  └────────────┘            └──────────────────┘
       │                            │
       ↓                            ↓
   PgPlanTextView          Pev2PlanVisualization
   (syntax highlight       (интерактивная
    + AI hotspots)          диаграмма pev2)
```

## Безопасность

**ВАЖНО:** Optimyzer выполняет реальный `EXPLAIN (FORMAT JSON, ANALYZE)`
на вашей PG базе. `ANALYZE` означает что запрос **реально выполнится** —
для SELECT это безопасно (нет side effects, мы оборачиваем в transaction).

**Optimyzer не разрешает re-EXPLAIN для запросов модификации данных:**

| Тип запроса | Разрешён re-EXPLAIN? | Почему |
|---|---|---|
| `SELECT`, `WITH ... SELECT` | ✅ Да | Read-only, side effects нет |
| `INSERT`, `UPDATE`, `DELETE` | ❌ Нет | EXPLAIN ANALYZE их выполнит реально |
| `MERGE`, `TRUNCATE`, DDL | ❌ Нет | Изменяют схему |
| `BEGIN`, `COMMIT`, `SET`, `COPY` | ❌ Нет | Управление сессией / I/O |
| `WITH x AS (UPDATE ...) SELECT` | ❌ Нет | Modifying CTE — изменяет данные |

Safety check выполняется **до** установки соединения с PG — недопустимые
запросы отвергаются с пояснением в UI.

**Рекомендация:** создайте отдельного PostgreSQL пользователя с правами
только `SELECT`:

```sql
CREATE USER optimyzer_readonly WITH PASSWORD 'strong-pass-here';
GRANT CONNECT ON DATABASE pgBase TO optimyzer_readonly;
GRANT USAGE ON SCHEMA public TO optimyzer_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO optimyzer_readonly;
-- На будущие таблицы:
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO optimyzer_readonly;
```

Это даёт двойную защиту: даже если Optimyzer случайно пропустит unsafe
запрос (regression bug), PG откажет в выполнении из-за нехватки прав.

## Где хранится пароль

Пароль PG подключения **никогда** не сохраняется в plaintext:
- В SQLite metadata.sqlite хранится только metadata (host/port/db/user)
  + ключ для keychain (`password_keychain_key`)
- Сам пароль — в **OS keychain**:
  - Windows: Windows Credential Manager (`Credential Manager → Web Credentials`)
  - macOS: Keychain Access (service `1c-optimyzer-pg`)
  - Linux: secret service (Gnome Keyring / KWallet через D-Bus)

При удалении подключения через UI пароль удаляется и из keychain.

## Как настроить

### 1. Откройте Настройки

В верхней панели приложения — иконка ⚙️ → вкладка **PostgreSQL**.

### 2. Нажмите «+ Добавить»

Заполните форму:

| Поле | Пример | Примечание |
|---|---|---|
| Имя | `Production pgBase` | Любое — для UI |
| Host | `localhost` | Адрес PG сервера |
| Port | `5432` | Стандартный PG порт |
| Database | `pgBase` | Имя БД (case-sensitive) |
| Username | `optimyzer_readonly` | Read-only пользователь (см. выше) |
| Password | `…` | Пароль — сохранится в keychain |

### 3. Нажмите «Проверить»

Optimyzer пробует подключиться и показывает `PostgreSQL <ver>...` либо
сообщение об ошибке. **Не сохраняйте пока подключение не проверено.**

### 4. Сохраните

Сохранённое подключение появится в списке. Первое сохранённое автоматически
помечается как **default** — оно используется когда вы нажимаете кнопку
«Получить интерактивный план» без явного выбора connection.

Если у вас несколько баз — назначайте default той, с которой работаете
чаще всего. Изменить default можно кнопкой «Сделать default».

### 5. Используйте в Plan Analyzer

1. Откройте экран **Анализ плана** → tab **Из архива ТЖ**
2. Выберите PostgreSQL план (badge `PG`)
3. В появившемся `PgPlanTextView` нажмите **«Получить интерактивный план»**
4. Optimyzer выполнит EXPLAIN (FORMAT JSON, ANALYZE) → вы увидите
   pev2 интерактивную диаграмму

## Troubleshooting

### «no_default_connection»

Не настроено ни одного PG подключения. Откройте Настройки → PostgreSQL →
Добавить.

### «invalid_password» / «invalid_auth»

Пароль изменился на стороне PG. Удалите подключение и создайте заново
(пароль из keychain тоже сотрётся).

### «database_not_found»

База с указанным именем не существует. Проверьте написание (PG case-sensitive,
`pgBase` ≠ `pgbase`).

### «connection_failed» / Network errors

Проверьте:
- PG service запущен: `pg_isready -h localhost -p 5432`
- Файрволл не блокирует подключение
- `pg_hba.conf` разрешает подключение с вашего адреса
- В `postgresql.conf`: `listen_addresses = '*'` (или конкретно IP)

### «unsafe_query»

Optimyzer отказал re-EXPLAIN потому что в SQL обнаружены DML/DDL keywords.
Это **намеренно** — pev2 visualization доступна только для SELECT-запросов.
Для INSERT/UPDATE/DELETE/etc используйте текстовый план + AI explanation
(базовый сценарий, не требует PG connection).

### «keychain_unavailable»

OS keychain недоступен. На Linux нужен secret service daemon
(gnome-keyring-daemon или KWallet). На Windows / macOS — должно работать
из коробки.

## Удаление подключения

Кнопка «Удалить» в карточке подключения:
1. Удаляет запись из `metadata.sqlite`
2. Удаляет пароль из OS keychain

Это **необратимая** операция — Optimyzer спросит подтверждение через
системный prompt.

## Полное удаление всех PG данных

```powershell
# Удалить все PG connections из metadata.sqlite:
$db = "$env:APPDATA\1c-optimyzer\metadata.sqlite"
# (нет CLI utility — придётся вручную через DB Browser или sqlite3)

# Очистить все entries в Windows Credential Manager:
cmdkey /list | Select-String "1c-optimyzer-pg"
# Удалить найденные:
cmdkey /delete:"<target>"
```

## Технические детали

- **Driver:** [asyncpg](https://github.com/MagicStack/asyncpg) (Apache 2.0)
- **Keychain:** Python [keyring](https://github.com/jaraco/keyring) (MIT)
- **Visualization:** [pev2](https://github.com/dalibo/pev2) (BSD)
  + Vue 3 (MIT) через `defineCustomElement` → Web Component
- **Re-EXPLAIN format:** `EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE)`
- **Session settings:** Optimyzer применяет 1С-style settings перед EXPLAIN:
  ```sql
  SET LOCAL enable_mergejoin = off;
  SET LOCAL cpu_operator_cost = 0.001;
  ```
  чтобы план был идентичен тому что выдаёт 1С PG сборка.
- **Timeout:** 30 секунд по дефолту (configurable через RPC параметр).
- **Transaction:** EXPLAIN выполняется внутри transaction; в случае любой
  ошибки — автоматический rollback.

---

**Связанные документы:**
- [`docs/onboarding/enable-plansqltext.md`](../onboarding/enable-plansqltext.md) — как настроить ТЖ для сбора PG planов
- [`docs/sales_sprint/SPRINT_8_PHASE_A_PG_DISCOVERY.md`](../sales_sprint/SPRINT_8_PHASE_A_PG_DISCOVERY.md) — discovery PG environment
- [`docs/sales_sprint/SPRINT_8_PHASE_B_REPORT.md`](../sales_sprint/SPRINT_8_PHASE_B_REPORT.md) — отчёт об имплементации
