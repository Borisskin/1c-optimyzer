# Discovery промпт для Claude Code — Sprint 7 Tools Inventory

> **Цель:** thorough инвентаризация всех 1С-инструментов, skills, MCP servers, external tools доступных на машине Сергея + проектных assets. Это **обязательная подготовка** перед Sprint 7 (Execution Plan Analyzer). Результат — основа для написания финального Sprint 7 promt.
>
> **Контекст:** Сергей — solo 1С-разработчик 15+ лет. Pivot к Premium продукту (9 900 ₽/мес). Главное правило: **максимально использовать всё что уже есть**, не строить велосипеды.

---

## Принципы исследования

1. **Active discovery, не пассивный список.** Каждый найденный tool — попытаться его реально использовать на тестовом сценарии. Не «нашёл SSMS на машине» а «SSMS установлен, открыл, сгенерировал .sqlplan, файл сохраняется в формате X».

2. **Practical applicability к Sprint 7.** Sprint 7 = Execution Plan Analyzer. Каждый tool оценивать через призму: **поможет ли это в импорте/генерации/визуализации/анализе execution plans MS SQL и PostgreSQL**.

3. **Sergei's setup в первую очередь.** Не теоретическая инвентаризация Windows, а **что реально доступно на этой конкретной машине**.

4. **Не игнорировать existing project assets.** В проекте уже накоплено много: 60+ skills из Sprint 3.5, tj-simulator, реальные архивы ТЖ, Configuration parser. Может быть это и есть основа Sprint 7, не opensource.

5. **Если найдено что-то неожиданно полезное** — отметить отдельно с пометкой «может изменить план Sprint 7».

---

## Что инвентаризировать (4 категории)

### Категория 1: PowerShell skills в `.claude/skills/`

В Sprint 3.5 было создано 60+ PowerShell скриптов для работы с 1С-инструментами. Они **могут быть забыты** в текущем планировании, но потенциально решают задачи Sprint 7.

**Что сделать:**

1. **Перечислить все файлы в `.claude/skills/`** с короткими описаниями назначения (из docstring каждого скрипта)

2. **Категоризировать по применимости к Sprint 7:**
   - **Прямо применимо** — может использоваться для plan analyzer
   - **Косвенно применимо** — может использоваться для тестирования / генерации test data
   - **Не применимо** — другая область

3. **Особенно искать скрипты для:**
   - Генерация SQL запросов из метаданных 1С
   - Извлечение запросов из модулей конфигурации
   - Работа с COM-объектом 1С:Предприятие
   - Подключение к SQL Server через 1С (если есть)
   - Парсинг XML 1С
   - Тестирование производительности
   - Симуляция нагрузки

4. **Реально запустить 5-10 наиболее применимых скриптов** и проверить что они работают на текущей машине Сергея (не просто читать код).

5. **Идентифицировать gaps** — какие задачи в Sprint 7 НЕ закрываются existing skills и нужно дописывать.

### Категория 2: MCP servers доступные Claude Code

У Claude Code есть набор подключённых MCP servers. Они могут давать прямой программный доступ к инструментам без subprocess wrapping.

**Что сделать:**

1. **Перечислить все активные MCP servers** — что у тебя доступно прямо сейчас в этой сессии? Названия серверов, что они делают.

2. **Особенно искать:**
   - **SQL Server MCP** — если есть, можно напрямую отправлять T-SQL запросы, получать execution plans, без bundling planview как subprocess
   - **PostgreSQL MCP** — то же для PG
   - **PerformanceStudio MCP** — упоминался в research отчёте, у него есть встроенный MCP server для AI-assisted plan review
   - **1С MCP** — если кто-то из сообщества сделал MCP для 1С (autocomplete? metadata query? COM bridge?)
   - **Database / SQL общие MCP** — для outsourcing query parsing / plan analysis
   - **File system / Shell MCP** — для прогона CLI tools
   - **GitHub MCP** — если есть для удобной работы с opensource проектами

3. **Для каждого найденного MCP** — попробовать **реальный вызов** одного из методов и показать пример работы. Не просто «есть SQL Server MCP», а «SQL Server MCP может выполнить вот этот запрос и вернуть execution plan вот в таком формате».

4. **Особое внимание** — если PerformanceStudio MCP доступен напрямую через MCP клиент, это **радикально упрощает** Sprint 7 — не нужно bundling .NET binary как subprocess, можно использовать через MCP.

### Категория 3: External tools на машине Сергея

Реально установленные на машине вещи которые могут помочь.

**Что сделать:**

1. **Проверить установлены ли:**
   - **SQL Server** (LocalDB / Developer Edition / Express) — есть в PATH? какая версия? есть ли тестовая база?
   - **SSMS (SQL Server Management Studio)** — можно ли запустить через CLI? есть ли возможность экспорта .sqlplan?
   - **Azure Data Studio** — альтернатива SSMS
   - **DataGrip / другие JetBrains tools** — могут давать execution plans для разных движков
   - **DBeaver** — universal database tool, поддерживает SQL Server + PostgreSQL
   - **PostgreSQL** server — есть локально? какой версии? psql в PATH?
   - **pgAdmin / pgBouncer** — управление PG
   - **1С:Предприятие 8** — установлена платформа? какая версия? есть ли возможность запускать через COM из PowerShell?
   - **OneScript** — opensource runtime для BSL, может пригодиться для прогона BSL вне 1С
   - **EDT (Enterprise Development Tools)** от 1С — IDE для разработчиков

2. **Для каждого найденного tool** — указать:
   - Версия
   - Путь установки
   - Доступен ли из CLI / можно ли запустить программно
   - Application для Sprint 7 (генерация .sqlplan? тестирование? визуализация?)

3. **Особенно проверить SQL Server LocalDB:**
   - Установлен ли?
   - Можно ли создать тестовую базу размером 100-1000 MB с разнообразными запросами для тестирования?
   - Можно ли через `sqlcmd` / Invoke-Sqlcmd / Python pyodbc генерировать execution plans программно?

4. **Если SQL Server не установлен** — оценить usable варианты:
   - Установка SQL Server Developer Edition (бесплатно для dev) — оценить сложность
   - SQL Server в Docker container — есть ли Docker на машине?
   - Использовать готовые .sqlplan примеры (есть в research/PerformanceStudio/test_data/?)
   - Тестовые серверы в облаке — overkill для разработки

### Категория 4: Существующие project assets

В проекте уже много накопленных вещей которые могут служить test data / reference / база.

**Что сделать:**

1. **Архивы ТЖ Сергея:**
   - Какие есть в `research/` или других папках?
   - Размеры, период, конфигурация
   - **Содержат ли DBMSSQL события с .Plan полем?** — это критически важно для Sprint 7
   - Можно ли извлечь execution plans из существующих ТЖ архивов?

2. **Configuration XML:**
   - `C:\BUFFER\SCHEME` — это БП 3.0 (упоминалось в Sprint 5)
   - Какие ещё конфигурации доступны?
   - Можно ли получить XML других конфигураций (УТ, ERP) для разнообразия тестов?

3. **Sprint 5 Configuration parser:**
   - Можно ли использовать его для **автоматической генерации SDBL запросов** из метаданных? Например: «возьми любой документ из БП 3.0, сгенерируй тестовый SELECT по нему»
   - Это даст test corpus для regression testing Sprint 7

4. **tj-simulator** (Sprint 3.5):
   - Что он умеет сейчас?
   - Можно ли расширить для генерации archive с заранее известными execution plans?

5. **Existing test fixtures:**
   - `research/PerformanceStudio/` — есть тестовые .sqlplan?
   - `research/testdata/` — что там полезного?
   - `backend/tests/fixtures/` — какие SDBL/SQL уже накоплены?
   - `tests/golden/` — Sprint 5 golden cases

### Категория 5: Reality check для Sprint 7 deliverables

Sprint 7 промпт будет содержать конкретные deliverables. Проверь реалистичность **каждого** из них с учётом найденных tools:

**Deliverable 1: Импорт .sqlplan файлов через UI drag-and-drop**
- Нужны .sqlplan для тестирования. Откуда возьмём? (SSMS Generate Actual Plan / DataGrip Show Execution Plan / programmatically from sqlcmd?)
- Найди **минимум 10 разных .sqlplan** для разных типов запросов (SELECT/INSERT/UPDATE/DELETE, simple/complex, с JOINs, с subqueries, etc.)

**Deliverable 2: Auto-extraction плана из DBMSSQL.Plan событий ТЖ**
- Проверь: **есть ли реально** в архивах Сергея ТЖ-события с заполненным .Plan?
- Какой формат хранится в .Plan? Это XML, base64, что-то другое?
- 1С сохраняет в ТЖ полные планы или только сжатые/обрезанные?

**Deliverable 3: SSMS-style visualization через html-query-plan**
- html-query-plan уже в research/. Можно ли прямо сейчас открыть его demo в браузере с реальным .sqlplan?
- Качество визуализации устраивает?

**Deliverable 4: PerformanceStudio integration**
- Скачать готовый бинарь PerformanceStudio (~30 MB) с их Releases
- Прогнать `planview analyze` на 3-5 реальных .sqlplan файлах
- Изучить JSON output реально, не теоретически
- Понять формат warnings, severity, и т.д.

**Deliverable 5: PostgreSQL plans через pev2**
- Есть ли PostgreSQL на машине?
- Можно ли сгенерировать `EXPLAIN (FORMAT JSON, ANALYZE)` output для тестов?
- pev2 demo в браузере с реальным PG plan — попробовать

**Deliverable 6: AI explanation плана**
- Если cloud AI orchestration уже работает (Sprint 6 Phase D) — можно ли просто расширить prompts на план-уровень?
- Тестовый prompt: вот план, объясни на русском что в нём плохо

---

## Что делать с найденным

Особенно фокусируйся на **снижении scope** Sprint 7:

- **Если** PerformanceStudio MCP доступен напрямую через MCP — **выкинуть** Phase «bundle planview binary» из Sprint 7
- **Если** SQL Server LocalDB есть и работает — **выкинуть** Phase «найти .sqlplan примеры», легко генерируем
- **Если** какие-то existing skills уже делают часть работы — переиспользовать
- **Если** в проекте уже есть test data — не генерировать новую

Цель: **Sprint 7 promt должен быть на 30-50% короче** благодаря reuse.

---

## Что НЕ делать в этой discovery

1. **Не интегрировать ничего** в основной проект — только разведка
2. **Не писать production код** — только тестовые вызовы и эксперименты
3. **Не модифицировать** existing skills / опенсорс проекты в `research/`
4. **Не тратить более 1-2 дней** — глубина важнее ширины, но не углубляйся в кроличьи норы
5. **Не оценивать opensource** который уже исследовался в `OPENSOURCE_RESEARCH_REPORT.md` — это уже сделано

---

## Формат финального отчёта

Создать `docs/sales_sprint/SPRINT_7_DISCOVERY.md` со структурой:

```markdown
# Sprint 7 Discovery — Tools & Assets Inventory

## Executive Summary

[2-3 абзаца: что нашли, что радикально меняет план Sprint 7, что подтверждает план]

## 1. PowerShell Skills (.claude/skills/)

### Полный каталог
[Таблица: имя | описание | категория | применимость к Sprint 7]

### Применимые к Sprint 7
[Список с детальным описанием каждого + результаты actual test runs]

### Gaps — что нужно дописать
[Что НЕ закрывается существующими skills для задач Sprint 7]

## 2. MCP Servers

### Активные сейчас
[Список с их capabilities]

### Применимые к Sprint 7
[Какие могут заменить subprocess wrapping]

### Особенные находки
[Например — если PerformanceStudio MCP доступен напрямую, это game-changer]

## 3. External Tools на машине

### Установлено
[Таблица: tool | version | path | applicability]

### НЕ установлено, но было бы полезно
[Список с оценкой сложности установки]

### Test results
[Что реально удалось запустить и какой output получили]

## 4. Project Assets

### Архивы ТЖ
[Список с метаданными, наличием DBMSSQL.Plan]

### Configuration XML
[Какие конфы доступны]

### Existing test fixtures
[Что переиспользуем]

### Sprint 5 Configuration parser — applicability
[Можно ли использовать для генерации test SDBL?]

## 5. Reality Check для Sprint 7 Deliverables

[Каждый deliverable из плана Sprint 7 — проверен на feasibility]

## 6. Рекомендации для Sprint 7 promt

### Что переиспользовать
[Конкретные skills, MCP, tools, project assets]

### Что упростить/выкинуть
[Phases из текущего плана которые не нужны благодаря найденному]

### Что добавить
[Чего не было в плане но обнаружилось как полезное]

### Открытые вопросы для архитектора
[Что требует решения Opus перед написанием Sprint 7 promt]
```

---

## Stop rule

Finished когда:
- [ ] Каталог skills полностью просмотрен и каталогизирован
- [ ] MCP servers перечислены и applicable из них протестированы
- [ ] External tools проверены, минимум 3 наиболее важных протестированы
- [ ] Project assets каталогизированы
- [ ] 6 deliverables Sprint 7 reality-checked
- [ ] Отчёт `SPRINT_7_DISCOVERY.md` написан и запушен в main

После push — отчитайся одним сообщением со ссылкой на отчёт. Архитектор (Opus) прочитает и напишет Sprint 7 promt с учётом находок.

---

## Особое напутствие

Сергей зафиксировал жёсткое правило: **МАКСИМАЛЬНО использовать всё что уже есть**, не строить велосипеды если есть готовые tools. Это значит — discovery работа должна быть **thorough, not superficial**.

Если нашёл что-то неожиданное (например, у тебя есть MCP к 1С Cloud Sandbox, или установлен EDT с готовым query analyzer) — отметь отдельно с пометкой **«CRITICAL FINDING»**. Это поможет архитектору значительно упростить Sprint 7.

Время на discovery: **1-2 дня максимум**. Если затягивается дольше — что-то идёт не так, останавливайся и спрашивай.

---

**Подготовил:** Claude Opus 4.7 (Architect)
**Для:** Claude Code (executor)
**Дата:** 2026-05-24
**Версия:** Sprint 7 Discovery v1
**Длительность:** 1-2 дня
**Следующий шаг после discovery:** Sprint 7 promt от архитектора с учётом найденного
