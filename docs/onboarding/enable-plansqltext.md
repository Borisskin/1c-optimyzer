# Включение SQL execution plans в технологическом журнале 1С (MS SQL + PostgreSQL)

> Чтобы Optimyzer мог автоматически импортировать execution plans из ТЖ архивов
> (а не только из вручную сохранённых `.sqlplan` файлов из SSMS), нужно
> один раз сказать платформе 1С регистрировать планы при каждом долгом SQL
> запросе. Работает одинаково для MS SQL Server и для PostgreSQL.

## TL;DR

```powershell
# В корне репозитория Optimyzer:
.\scripts\patch-logcfg-for-plans.ps1
# UAC спросит admin → Yes → скрипт сам сделает backup + правку + restart ragent
```

После этого новые **DBMSSQL** (MSSQL) и **DBPOSTGRS** (PostgreSQL) события в ТЖ
будут содержать поле `planSQLText` с текстовым представлением плана. Optimyzer
покажет их во вкладке «Из архива ТЖ» в экране **Анализ плана** с автоматическим
определением движка и адекватным рендером.

---

## Что это вообще такое

Технологический журнал 1С (ТЖ) — это текстовые `.log` файлы, в которые платформа
пишет служебные события: SQL запросы, дедлоки, исключения, серверные вызовы.

По умолчанию для database событий пишется только текст SQL (`Sql='...'` /
`Sql="..."`) — **без** плана выполнения. Чтобы платформа писала ещё и план,
в `logcfg.xml` нужны три вещи:

```xml
<config xmlns="http://v8.1c.ru/v8/tech-log">
    <log location="C:\1C-TechLog" history="72">
        <!-- 1. event filter — для каких событий собираем -->
        <event>
            <eq property="name" value="DBMSSQL"/>
            <gt property="duration" value="10"/>
        </event>
        <event>
            <eq property="name" value="DBPOSTGRS"/>
            <gt property="duration" value="10"/>
        </event>

        <!-- 2. property — указываем что хотим plansqltext в JSON -->
        <property name="all"/>
        <property name="plansqltext"/>
    </log>

    <!-- 3. master-switch на уровне config, НЕ внутри log -->
    <plansql/>
</config>
```

**КРИТИЧНО:** `<plansql/>` должен быть **child of `<config>`**, не `<log>`!
Если ставить внутрь `<log>` — платформа тихо игнорирует и planSQLText не пишется.
Проверено десятью неудачными попытками во время Sprint 7 discovery, итог:
`<plansql/>` — это master-switch механизма сбора планов, и платформа ищет его
именно на уровне `<config>`.

После этого каждое матчащее DBMSSQL/DBPOSTGRS событие будет содержать дополнительное
поле `planSQLText`:
- **MSSQL**: текстовый план в формате `SET SHOWPLAN_TEXT ON` SQL Server'а
- **PostgreSQL**: вывод `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` PG (с `Planning Time`/`Execution Time` и пр.)

## Зачем это нужно Optimyzer

Sprint 7 (для MSSQL) и Sprint 8 Phase B (для PG) дали экран **Анализ плана** с тремя путями импорта:

1. **Импорт файла** — `.sqlplan` файл (как из SSMS «Save Execution Plan As...»)
2. **Вставить XML/TEXT** — paste plan из буфера
3. **Из архива ТЖ** — автоматически из DBMSSQL/DBPOSTGRS событий загруженного архива (требует `<plansql/>`)

Третий путь — самый удобный для повседневной работы:
- Не нужно открывать SSMS / pgAdmin
- Не нужно вручную сохранять каждый план
- Можно проанализировать все долгие запросы из реального production-снапшота
- Optimyzer автоматически отличает MSSQL от PostgreSQL по событию и применяет
  правильный рендер + AI prompt со знанием движка

## Как включить (3 способа)

### Способ 1: Скрипт (рекомендуется)

```powershell
.\scripts\patch-logcfg-for-plans.ps1
```

Скрипт:
- Делает backup `logcfg.xml.backup.YYYYMMDD-HHMMSS`
- Парсит XML с сохранением форматирования (комментариев, отступов)
- Чистит legacy `<plan>` / `<plansql>` / `<plansqltext>` элементы (от старых экспериментов)
- Добавляет `<event name="DBPOSTGRS">` если ещё нет (для PG баз)
- Добавляет `<property name="plansqltext"/>` внутрь `<log>`
- Добавляет `<plansql/>` на уровне `<config>` как sibling `<log>`
- Перезапускает `1C:Enterprise 8.3 Server Agent (x86-64)`

Сам себя поднимет до admin через UAC. Параметры:

```powershell
# DRY RUN — показать что будет сделано без изменений
.\scripts\patch-logcfg-for-plans.ps1 -DryRun

# Без рестарта сервиса (полезно если сейчас идёт работа в Конфигураторе)
.\scripts\patch-logcfg-for-plans.ps1 -NoRestart

# Нестандартный путь к logcfg
.\scripts\patch-logcfg-for-plans.ps1 -LogcfgPath "D:\1C\conf\logcfg.xml"
```

### Способ 2: Вручную через блокнот

1. Открой `C:\Program Files\1cv8\conf\logcfg.xml` в блокноте от админа
2. Сделай резервную копию (Save As с другим именем)
3. Добавь:
   - Для MSSQL: `<event><eq property="name" value="DBMSSQL"/><gt property="duration" value="10"/></event>`
   - Для PG: `<event><eq property="name" value="DBPOSTGRS"/><gt property="duration" value="10"/></event>`
   - Внутрь `<log>`: `<property name="plansqltext"/>`
   - На уровне `<config>` (sibling `<log>`): `<plansql/>`
4. Сохрани (encoding **UTF-8 без BOM** — некоторые версии платформы не читают BOM)
5. Перезапусти сервис: `Get-Service '1C:Enterprise 8.3 Server Agent (x86-64)' | Restart-Service -Force`

### Способ 3: Через ИТС-документацию

Полная справка по конфигурированию ТЖ:
[its.1c.ru → Тех. журнал → Структура logcfg.xml](https://its.1c.ru/db/v8323doc#bookmark:adm:TI000000211)

## Что проверить после

1. **Файл изменился:**
   ```powershell
   Select-String -Pattern '<plansql' -Path 'C:\Program Files\1cv8\conf\logcfg.xml'
   Select-String -Pattern 'DBPOSTGRS' -Path 'C:\Program Files\1cv8\conf\logcfg.xml'
   ```

2. **Сервис работает:**
   ```powershell
   Get-Service '1C:Enterprise 8.3 Server Agent (x86-64)'
   # → Status: Running
   ```

3. **Планы появляются в архиве** — запусти любой долгий SQL запрос
   (например через `tj-simulator` или проведи несколько документов в 1С),
   подожди 30 секунд, проверь свежий `.log` файл в `C:\1C-TechLog\rphost_NNNN\`:
   - Для MSSQL базы должны быть `DBMSSQL,...planSQLText='...'`
   - Для PG базы должны быть `DBPOSTGRS,...planSQLText="..."`
     (внимание: PG использует double-quotes, MSSQL — single-quotes)

## Особенности PostgreSQL баз 1С

Дополнительные нюансы для PG (открыты в Sprint 8 Phase A discovery):

1. **Event name отличается**: для PG — `DBPOSTGRS`, для MSSQL — `DBMSSQL`. Это
   значит существующие архивы с фильтром только на DBMSSQL **не содержат**
   PG events. После правки logcfg нужно собрать новый архив.

2. **Quoting**: PG значения в double-quotes (`"..."`), MSSQL — в single-quotes (`'...'`).
   Парсер Optimyzer (tj_parser.py) обрабатывает оба варианта прозрачно.

3. **planSQLText формат**: PG пишет EXPLAIN ANALYZE BUFFERS VERBOSE текстом
   (с `Planning Time`/`Execution Time`/`Buffers: shared hit=N`), MSSQL —
   текстовый план SHOWPLAN_TEXT (с indent `|--`). Это разные форматы — Optimyzer
   автоматически определяет какой движок по событию и применяет правильный рендер.

4. **1С запускает PG со специальными настройками**:
   - `SET enable_mergejoin = off` (Merge Join отключён — оптимизатор его не выбирает)
   - `SET cpu_operator_cost = 0.001` (cost numbers в 5× меньше дефолта PG)
   - `SET lock_timeout = 20000` (20 сек таймаут блокировок)

   Это значит cost-numbers в PG planах от 1С нельзя сравнивать с типовыми
   «плохой план если cost > X» thresholds. Optimyzer'у AI prompt передаёт этот
   контекст автоматически.

## Troubleshooting

### «Доступ запрещён» при правке logcfg

Запускай PowerShell от админа (UAC). Скрипт сам поднимется — но если запускаешь
вручную через блокнот, открывай его правой кнопкой → «Запуск от имени админа».

### Сервис не находится

Возможные причины:
- Установлен 32-bit (`1C:Enterprise 8.3 Server Agent (x86)` без `-64`)
- Установлена кластерная версия с другим именем
- 1С работает в файловом режиме (нет сервиса вообще — ТЖ от клиента)

Перезапусти руками: открой `services.msc`, найди службу с «1C» в имени, Stop → Start.

В файловом режиме (без серверной части) `<plansql/>` тоже работает, но события
пишет клиент — рестарт не нужен, достаточно перезапустить 1С:Предприятие.

### planSQLText не появляется в архиве

Проверь:
- Запрос длится дольше фильтра в `<event>` (по умолчанию `duration > 10` = 100 мс)
- Для PG баз — в logcfg есть `<event>` с `name="DBPOSTGRS"` (старые версии
  patch-logcfg добавляли только DBMSSQL — обнови скрипт через `git pull`)
- Архив пишется в правильное место (`<log location="...">` совпадает с тем где ищешь)
- Прошло достаточно времени с момента запроса (ТЖ flush может занимать секунды)
- `<plansql/>` на уровне `<config>`, не внутри `<log>` (typical bug)
- Архив не из старой сессии — ragent должен был перезапуститься после правки

### XML парсер сломался

Если скрипт жалуется на структуру — у тебя нестандартный logcfg.xml. Восстанови из
backup:

```powershell
$backup = Get-ChildItem 'C:\Program Files\1cv8\conf\' -Filter 'logcfg.xml.backup.*' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item $backup.FullName 'C:\Program Files\1cv8\conf\logcfg.xml' -Force
```

И сделай правку вручную (Способ 2).

### Сессии 1С разорвались при рестарте

Это ожидаемое поведение — `Restart-Service -Force` останавливает ragent, что
обрывает все активные соединения (Предприятие, Конфигуратор, фоновые задания).

Чтобы избежать — используй флаг `-NoRestart`, потом перезапусти ragent в удобное
время (вечером / на выходных).

## Откат

```powershell
# Найти свежий backup
$backup = Get-ChildItem 'C:\Program Files\1cv8\conf\' -Filter 'logcfg.xml.backup.*' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Восстановить
Copy-Item $backup.FullName 'C:\Program Files\1cv8\conf\logcfg.xml' -Force

# Перезапустить ragent
Restart-Service '1C:Enterprise 8.3 Server Agent (x86-64)' -Force
```

## Влияние на размер архива

Включение `<plansql/>` добавляет план в каждое матчащее DBMSSQL/DBPOSTGRS
событие — типично 1-5 KB текстом (большие планы могут быть 50+ KB). При фильтре
`duration > 10` (100 мс) и нормальной нагрузке это даёт +10-30% к размеру ТЖ архива.

Если место критично — поставь более строгий фильтр в `<event>`:

```xml
<event>
    <eq property="name" value="DBMSSQL"/>
    <gt property="duration" value="100"/>   <!-- 1 секунда вместо 100 мс -->
</event>
<event>
    <eq property="name" value="DBPOSTGRS"/>
    <gt property="duration" value="100"/>
</event>
```

Тогда планы будут писаться только для **реально медленных** запросов (>1 сек),
что обычно и интересно в performance-аудите.

---

**Связанные документы:**
- [`scripts/patch-logcfg-for-plans.ps1`](../../scripts/patch-logcfg-for-plans.ps1) — сам скрипт
- [Sprint 7 Phase D] — auto-extract DBMSSQL.Plan из ТЖ (MSSQL only)
- [Sprint 8 Phase B] — auto-extract DBPOSTGRS.planSQLText из ТЖ (PostgreSQL)
