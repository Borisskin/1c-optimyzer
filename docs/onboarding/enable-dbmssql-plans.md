# Включение SQL execution plans в технологическом журнале 1С

> Чтобы Optimyzer мог автоматически импортировать execution plans из ТЖ архивов
> (а не только из вручную сохранённых `.sqlplan` файлов из SSMS), нужно
> один раз сказать платформе 1С регистрировать планы при каждом долгом SQL
> запросе.

## TL;DR

```powershell
# В корне репозитория Optimyzer:
.\scripts\patch-logcfg-for-plans.ps1
# UAC спросит admin → Yes → скрипт сам сделает backup + правку + restart ragent
```

После этого новые DBMSSQL события в ТЖ будут содержать поле `planSQLText` с
текстовым представлением плана. Optimyzer покажет их во вкладке «Из архива ТЖ»
в экране **Анализ плана**.

---

## Что это вообще такое

Технологический журнал 1С (ТЖ) — это бинарные `.log` файлы, в которые платформа
пишет служебные события: SQL запросы, дедлоки, исключения, серверные вызовы.

По умолчанию для DBMSSQL событий пишется только текст SQL (`Sql='...'`) — без
плана выполнения. Чтобы платформа писала ещё и план, в `logcfg.xml` нужно
добавить **пустой элемент `<plan/>`** внутрь `<log>`:

```xml
<log location="C:\1C-TechLog" history="72">
    <event>
        <eq property="name" value="DBMSSQL"/>
        <gt property="duration" value="10"/>
    </event>
    <property name="all"/>
    <plan/>   <!-- ← это включает регистрацию планов -->
</log>
```

После этого каждое матчащее DBMSSQL событие будет содержать дополнительное
поле `planSQLText` — план в текстовом формате (тот же что показывает SSMS
при `SET SHOWPLAN_TEXT ON`).

## Зачем это нужно Optimyzer

Sprint 7 добавил **Анализ плана** — экран с тремя путями импорта:

1. **Импорт файла** — `.sqlplan` файл (как из SSMS «Save Execution Plan As...»)
2. **Вставить XML** — paste plan XML из буфера
3. **Из архива ТЖ** — автоматически из DBMSSQL событий загруженного архива (требует `<plan/>`)

Третий путь — самый удобный для повседневной работы:
- Не нужно открывать SSMS
- Не нужно вручную сохранять каждый план
- Можно проанализировать все долгие запросы из реального production-снапшота

## Как включить (3 способа)

### Способ 1: Скрипт (рекомендуется)

```powershell
.\scripts\patch-logcfg-for-plans.ps1
```

Скрипт:
- Делает backup `logcfg.xml.backup.YYYYMMDD-HHMMSS`
- Парсит XML с сохранением форматирования (комментариев, отступов)
- Проверяет — нет ли уже `<plan/>` (idempotent)
- Добавляет `<plan/>` если нет
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
2. Сделай резервную копию (Ctrl+S «Save As» с другим именем)
3. Найди закрывающий тег `</log>`
4. Перед ним добавь строку: `        <plan/>`
5. Сохрани (encoding **UTF-8 без BOM** — некоторые версии платформы не читают BOM)
6. Перезапусти сервис: `Get-Service '1C:Enterprise 8.3 Server Agent (x86-64)' | Restart-Service -Force`

### Способ 3: Через ИТС-документацию

Полная справка по конфигурированию ТЖ:
[its.1c.ru → Тех. журнал → Структура logcfg.xml](https://its.1c.ru/db/v8323doc#bookmark:adm:TI000000211)

## Что проверить после

1. **Файл изменился:**
   ```powershell
   Select-String -Pattern '<plan' -Path 'C:\Program Files\1cv8\conf\logcfg.xml'
   ```

2. **Сервис работает:**
   ```powershell
   Get-Service '1C:Enterprise 8.3 Server Agent (x86-64)'
   # → Status: Running
   ```

3. **Планы появляются в архиве** — запусти любой долгий SQL запрос
   (например через `tj-simulator` кнопка 5 «DBMSSQL»), подожди 30 секунд,
   проверь свежий `.log` файл в `C:\1C-TechLog\rphost_NNNN\` —
   должен быть `planSQLText='...'`.

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

В файловом режиме (без серверной части) `<plan/>` тоже работает, но события
пишет клиент — рестарт не нужен, достаточно перезапустить 1С:Предприятие.

### planSQLText не появляется в архиве

Проверь:
- Запрос длится дольше фильтра в `<event>` (по умолчанию `duration > 10` = 100 мс)
- Архив пишется в правильное место (`<log location="...">` совпадает с тем где ищешь)
- Прошло достаточно времени с момента запроса (ТЖ flush может занимать секунды)
- `<property name="all"/>` присутствует (без него поле может не попасть в JSON)
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

`<plan/>` для каждого матчащего DBMSSQL события добавляет план — типично 1-5 KB
текстом (большие планы могут быть и 50 KB). При фильтре `duration > 10` (100 мс)
и нормальной нагрузке это даёт +10-30% к размеру ТЖ архива.

Если место критично — поставь более строгий фильтр в `<event>`:

```xml
<event>
    <eq property="name" value="DBMSSQL"/>
    <gt property="duration" value="100"/>   <!-- 1 секунда вместо 100 мс -->
</event>
```

Тогда планы будут писаться только для **реально медленных** запросов (>1 сек),
что обычно и интересно в performance-аудите.

---

**Связанные документы:**
- [`scripts/patch-logcfg-for-plans.ps1`](../../scripts/patch-logcfg-for-plans.ps1) — сам скрипт
- [Sprint 7 Phase D] — auto-extract DBMSSQL.Plan из ТЖ
