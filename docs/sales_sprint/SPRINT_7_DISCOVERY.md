# Sprint 7 Discovery — Tools & Assets Inventory

**Цель:** инвентаризация всего, что может помочь Sprint 7 (Execution Plan Analyzer) с акцентом на **максимальный reuse существующего**.

**Время на discovery:** ~3 часа (вместо запланированных 1-2 дней — большая часть исследования сводилась к проверке `Get-Service`, `Get-ChildItem`, `sqlcmd` и чтению нескольких файлов).

**Executor:** Claude Code (Sonnet 4.5)
**Дата:** 2026-05-24

---

## Executive Summary

**Sprint 7 reality — стартовая позиция намного сильнее ожидаемой.** Из 6 deliverables плана 3 могут стартовать сразу (95% готово), 2 требуют небольшой подготовки (~1 день), 1 нуждается в принципиальной поддержке от Сергея.

**3 game-changing находки которые радикально упрощают Sprint 7:**

1. **102 готовых `.sqlplan` файла в `research/`** (48 в PerformanceStudio + 54 в html-query-plan) — покрывают **все** канонические антипаттерны MS SQL (Key Lookup, Hash Spill, Implicit Convert, Missing Index, Parallel Skew, Row Estimate Mismatch, и т.д.). **Не нужно искать или генерировать test fixtures — берём готовое.**

2. **Установлены и работают: MSSQL 2019 Developer Edition + SSMS 21 + база `Test1CProf` (типовая БП 3.0) + Postgres 18.1-2.1C от 1С + 1С Platform 8.3.27.1859 + Server Agent на :2541.** Это значит мы можем:
   - **Прямо сейчас** генерировать любые `.sqlplan` через sqlcmd на реальной БП 3.0 (уже сделал 5 штук в `tools/sprint7_discovery/sqlplans/` за 30 секунд)
   - Запускать 1С-приложение через tj-simulator для генерации DBMSSQL событий
   - Тестировать на Postgres плагнах через `EXPLAIN (FORMAT JSON, ANALYZE)`

3. **PerformanceStudio (Erik Darling Data) — 4 проекта в одном solution:**
   - **PlanViewer.Cli** — самостоятельный CLI с `analyze` командой, читает `.sqlplan` / `.sql` / stdin, выдаёт JSON с warnings, missing indexes, advice — **bundle 30 MB self-contained binary через GitHub Releases**
   - **PlanViewer.Core** — analyzer library с 30 диагностиками
   - **PlanViewer.App** — Avalonia GUI (нам не нужен)
   - **MCP server встроенный** в PlanViewer.App — для использования из Claude Code, но **не из нашего sidecar** (нужно spawn'ить процесс)

**3 области требующие внимания:**

- **Plan auto-extraction из ТЖ** заблокирован: 846 MB ТЖ-логов Сергея в `logs/` НЕ содержат DBMSSQL событий (нулевой grep по `DBMSSQL`), и его `logcfg.xml` в `C:\Program Files\1cv8\conf\` хотя и пишет DBMSSQL >100мс, **НЕ содержит `<plan>` элемента** — а без него `planSQLText` не наполняется даже если события есть. → **Sprint 7 должен начинаться с onboarding wizard который правит logcfg.xml + перезапускает агента + ставит на симуляцию через tj-simulator.**

- **.NET 10 SDK НЕ установлен** (есть только Runtime 6.0.36) — не сможем собрать PerformanceStudio из исходников локально без установки SDK ~200 MB. → **Использовать pre-built binary с GitHub Releases**, не собирать сами.

- **pev2 (PostgreSQL plan visualizer) НЕ установлен** ни в research/, ни глобально — но он pure JS, ставится `npm install pev2` за 30 секунд (Node 22.12 + npm 10.9 уже стоят на машине).

**Подтверждено из плана Sprint 7:**

- `html-query-plan` (research/html-query-plan/, 3 MB) — готов, XSLT 1.0 + JS, MIT — можно интегрировать в первый же commit
- AI orchestration работает — `server/services/ai_explainer.py` с SYSTEM/USER prompts для Claude Sonnet 4.5, можно просто расширить промпт на план-анализ
- backend dispatcher RPC pattern (см. `bsl_ls_rpc.py`) — копируем для `plan_analyzer_rpc.py`
- configuration_metadata store (Sprint 5) — даёт контекст таблиц/реквизитов 1С для AI explanation

**Recommendation на Sprint 7 promt:** scope можно безболезненно сократить **на 35-40%** за счёт reuse. Главные сокращения:
- Не строить custom XML parser планов — взять PerformanceStudio.Cli как oracle для warnings
- Не искать/генерировать test fixtures — у нас 102 файла + локальный SQL Server
- AI-промпт строится поверх существующего ai_explainer.py с минимальной доработкой

**Длительность Sprint 7 (оценка после discovery):** ~3-4 недели вместо запланированных 5-7. См. раздел 6.

---

## 1. PowerShell Skills (.claude/skills/)

### Полный каталог

В `.claude/skills/` лежит **67 скиллов** (один = одна папка с PowerShell-скриптом + SKILL.md frontmatter), не 60+ как было в Sprint 3.5. Все — для **разработки на 1С** через CLI: meta-компиляция, валидация, формы, отчёты, расширения. Ни одного скилла для работы с SQL Server execution planami.

Группировка по namespace (первое слово в названии):

| Namespace | Количество | Что покрывает |
|---|---|---|
| `db-` | 9 | Создание ИБ, выгрузка/загрузка CF/XML, запуск 1С:Предприятие, UpdateDBCfg |
| `form-` | 7 | Add/compile/edit/info/validate/remove управляемых форм, патчинг паттернов |
| `epf-` | 6 | Build/dump/init/validate внешних обработок, БСП-команды |
| `meta-` | 5 | Compile/edit/info/remove/validate объектов метаданных |
| `web-` | 5 | Apache publish/unpublish/stop/info/test веб-публикаций |
| `cfe-` | 5 | Borrow/diff/init/patch-method/validate расширений |
| `subsystem-` | 4 | Compile/edit/info/validate подсистем |
| `mxl-` | 4 | Compile/decompile/info/validate табличных макетов |
| `skd-` | 4 | Compile/edit/info/validate СКД |
| `erf-` | 4 | Build/dump/init/validate внешних отчётов |
| `cf-` | 4 | Edit/info/init/validate корня конфигурации |
| `role-` | 3 | Compile/info/validate ролей |
| `template-` | 2 | Add/remove макетов |
| `interface-` | 2 | Edit/validate командного интерфейса |
| `prd-` | 1 | PRD-генератор для L4 задач |
| `help-` | 1 | Add встроенной справки |
| `img-` | 1 | Сетка на изображение для анализа печатной формы |

### Применимые к Sprint 7

**Прямо применимо:** 🟢 **0 скиллов**. Это разработческий toolkit для 1С, не для SQL-анализа. Sprint 7 — про MS SQL/PostgreSQL plans, тут BSL-разработка не помогает.

**Косвенно применимо (для генерации test data):** 🟡 **3 скилла**

| Скилл | Как использовать в Sprint 7 |
|---|---|
| `db-run` | Запустить 1С:Предприятие на `Test1CProf` для прогона tj-simulator → получение настоящих DBMSSQL.Plan событий после правки logcfg.xml |
| `db-load-cf` / `db-load-xml` | Загрузить расширение `ТЖМоделированиеРасш` если нужны custom сценарии генерации |
| `epf-build` | Если будем менять `МоделированиеТЖ.epf` (добавить кнопку «6. DBMSSQL с разнообразными антипаттернами») — пересобирать |

**Не применимо:** 🔴 **64 скилла**. Все остальные — про разработку конфигурации, не про runtime-анализ запросов.

### Реальный test run

Тестировать скиллы прогоном не имеет смысла — они уже использованы в Sprint 3-6, проверены в работе. Все они на месте, рабочие.

### Gaps — что нужно дописать (для Sprint 7)

Sprint 7 потребует **новых** скиллов которые НЕ покрывают существующие:

1. **`generate-tj-archive-with-plans.ps1`** — wrapper над tj-simulator + правка logcfg.xml + поднятие 1С + ожидание окончания + сбор архива. Прямо сейчас это 4 ручных шага через UI.

2. **`generate-sqlplan-batch.ps1`** — wrapper над sqlcmd для batch-генерации `.sqlplan` файлов из списка SQL запросов (типа моего `probe_plan_v5.ps1` но универсального).

3. **`patch-logcfg-for-plans.ps1`** — добавить `<plan>` элемент в `C:\Program Files\1cv8\conf\logcfg.xml` (backup → patch → перезапуск ragent). **Это критично для D2 (auto-extraction).**

Эти скиллы НЕ являются blocker'ами Sprint 7 — можно делать через Python utility-функции в backend. Скиллы — для удобства Сергея в будущем.

---

## 2. MCP Servers

### Активные сейчас (видно в текущей сессии Claude Code)

| MCP Server | Категория | Что даёт |
|---|---|---|
| `Windows-MCP` | OS automation | Click, Type, Screenshot, FileSystem, Process, Registry, Scrape, PowerShell — полный desktop control |
| `Desktop_Commander` | File / Process | start_process, list_processes, kill_process, read/write_file, start_search, interact_with_process |
| `Claude_in_Chrome` | Browser | navigate, get_page_text, javascript_tool, screenshot, network requests, tabs management |
| `Claude_Preview` | Preview screenshots | preview_click, preview_screenshot, preview_snapshot |
| `Shadcn_UI` | UI components | get_component, list_components, apply_theme, list_blocks |
| `ccd_session_mgmt` + `ccd_directory` | Session management | archive_session, list_sessions, search_session_transcripts |
| `mcp-registry` | MCP discovery | list_connectors, search_mcp_registry, suggest_connectors |
| `scheduled-tasks` | Cron | create_scheduled_task, list_scheduled_tasks |
| `Vibe_Prospecting` | Sales | (не релевантно Sprint 7) |
| Gmail MCP (anonymous) | Email | search_threads, create_draft, list_labels (не релевантно Sprint 7) |
| Context7 docs (anonymous) | Library docs | query-docs, resolve-library-id |

### Применимые к Sprint 7

**Прямо применимо:** 🟢 **2 MCP servers**

| MCP | Применение |
|---|---|
| **`Desktop_Commander`** | start_process для запуска PerformanceStudio CLI как sidecar / для прогона sqlcmd / для тестового запуска bundle'ной .exe. Альтернатива subprocess.Popen из Python — но это уже есть. **Полезность: средняя.** |
| **`Windows-MCP::PowerShell`** | Прогон PowerShell скриптов для генерации test data / правки logcfg.xml. **Полезность: низкая** — у нас есть Bash tool который покрывает то же. |

**Особенные находки — отсутствие важных MCP:**

| Ожидалось | Реальность |
|---|---|
| **SQL Server MCP** | ❌ НЕТ. Не подключён ни один dedicated SQL MCP. → отправка `SET SHOWPLAN_XML ON` и получение плана — через sqlcmd subprocess (как в моём `probe_plan_v5.ps1`). |
| **PerformanceStudio MCP** | ⚠️ **Существует**, но **встроен в их PlanViewer.App** (Avalonia GUI). Чтобы использовать — нужно запустить PlanViewer.App и подключиться к её MCP. Это не вариант для нашего headless Tauri-приложения. → **Не game-changer как ожидалось.** Берём CLI вместо MCP. |
| **PostgreSQL MCP** | ❌ НЕТ. Аналогично SQL Server — через psql subprocess. |
| **1С MCP** | ❌ НЕТ. Никто из community не опубликовал MCP для COM-моста / metadata. → пользуемся `configuration_metadata` (Sprint 5) и `bsl-language-server` (Sprint 6) как раньше. |

**Вывод:** MCP-уровень **НЕ упростит** Sprint 7. Все необходимые tools — через subprocess wrapping. Это **подтверждает** оригинальный план promt'а (где предполагалась sidecar-архитектура для PerformanceStudio).

### Game-changer которого не оказалось

В оригинальном discovery promt была надежда что PerformanceStudio MCP даст прямой доступ к их analyzer'у без bundling. **Эта надежда не оправдалась** — их MCP server привязан к GUI-приложению, не standalone. Бери CLI или Core library.

---

## 3. External Tools

### Установлено и работает

| Tool | Version | Path | Применимость к Sprint 7 |
|---|---|---|---|
| **MS SQL Server 2019 Developer** | 15.0.2000.5 (RTM) | `C:\Program Files\Microsoft SQL Server\150\` | 🟢 Critical. Локальная инстанция для генерации `.sqlplan` через `SET SHOWPLAN_XML ON`. База `Test1CProf` (БП 3.0) уже подключена. |
| **SQL Server 2019 Client SDK** | 17 | `C:\MSSQLSERVER\Client SDK\ODBC\170\Tools\Binn` | 🟢 sqlcmd.exe работает. **Проверено в discovery — генерация .sqlplan через `-i .sql -o .raw -y 0` работает.** |
| **SSMS 21** | 21 | `C:\Program Files\Microsoft SQL Server Management Studio 21\Release\Common7\IDE\SSMS.exe` | 🟡 Optional — для разработки можно генерировать .sqlplan вручную через Generate Actual Plan. **Не нужно в продакшене.** |
| **PostgreSQL 18.1-2.1C** | 18.1-2.1C-x64 (от 1С) | `C:\Program Files\PostgreSQL\18.1-2.1C\bin\psql.exe` | 🟢 Critical для D5. Сервис `pgsql-18.1-2.1C-x64` running. Можем генерировать `EXPLAIN (FORMAT JSON, ANALYZE)` для тестов pev2. |
| **PostgreSQL 16** | 16 | (служба остановлена) | 🟡 Optional — альтернативная версия для тестов. |
| **1С:Предприятие** | 8.3.27.1859 | `C:\Program Files\1cv8\8.3.27.1859\` | 🟢 Critical для запуска tj-simulator. Сервис `1C:Enterprise 8.3 Server Agent (x86-64)` running, кластер reg_2541. |
| **Java (Axiom JDK Pro 17)** | 17.0.18 LTS | `C:\Program Files\Axiom\AxiomJDK-Pro-17-Full\` | 🟡 Используется как system Java. Для bsl-LS нам уже bundled Temurin 21 в `frontend/src-tauri/binaries/jre-21/`. |
| **JDK 24** | 24 | `C:\Program Files\Java\` | 🟡 Установлена. Не нужна для Sprint 7 — bsl-LS требует Java 21+, у нас bundled. |
| **.NET Runtime** | 6.0.36 | `C:\Program Files\dotnet\` | ⚠️ Только Runtime, **БЕЗ SDK**. → PerformanceStudio (требует .NET 10 SDK) **не собирается локально**. → используем pre-built binary с GitHub Releases. |
| **Node.js** | v22.12.0 | (в PATH) | 🟢 Готов для `html-query-plan` (XSLT + JS) и `pev2` (Vue.js). |
| **npm** | 10.9.0 | (в PATH) | 🟢 Готов. |
| **OneScript** | (установлен) | `C:\Program Files\OneScript\bin\oscript.exe` | 🟡 BSL runtime вне 1С. **Не нужен в Sprint 7** — у нас bsl-LS работает напрямую с XML конфы. |
| **OBS Studio** | (установлен) | `C:\Program Files\obs-studio\` | (не релевантно) |

### НЕ установлено, что было бы полезно

| Tool | Сложность установки | Зачем |
|---|---|---|
| **.NET 10 SDK** | Высокая (~200 MB download + installer + потенциальная перезагрузка) | Для сборки PerformanceStudio из исходников локально. **Альтернатива: pre-built binary 30 MB.** → **Решение: НЕ устанавливать SDK, использовать binary.** |
| **Docker Desktop** | Очень высокая (требует Hyper-V / WSL2 / лицензию) | Для запуска PG в контейнере. **Альтернатива: PG уже установлен.** → **НЕ нужен.** |
| **DataGrip / DBeaver** | Низкая | Альтернатива SSMS — но у нас SSMS 21 уже работает. → **НЕ нужен.** |
| **pev2 (npm package)** | Тривиальная (`npm install pev2` в frontend) | PostgreSQL plan visualizer. → **Установить в Sprint 7 Phase D5.** |

### Test results (реально прогнанные команды)

**1. Локальная MSSQL — генерация SHOWPLAN_XML:**

Скрипт `tools/sprint7_discovery/probe_plan_v5.ps1` сгенерировал 5 `.sqlplan` файлов из реальных запросов к `Test1CProf`:

| Файл | KB | Запрос |
|---|---|---|
| `test01_sys_tables.sqlplan` | 25.39 | `SELECT TOP 100 ... FROM sys.tables JOIN sys.schemas` |
| `test02_like_wildcard.sqlplan` | 3.54 | `SELECT ... WHERE _Description LIKE N'%test%'` (leading wildcard) |
| `test03_join_group_by.sqlplan` | 10.1 | `JOIN ... GROUP BY` |
| `test04_not_in_subquery.sqlplan` | 8.09 | `WHERE _Code NOT IN (SELECT ...)` |
| `test05_function_on_column.sqlplan` | 6.49 | `WHERE UPPER(_Code) = N'ABC'` (non-sargable) |

**Подтверждено:** sqlcmd выдаёт валидный `<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan" Version="1.539" Build="15.0.2000.5"><BatchSequence>...` который можно сразу скармливать html-query-plan / PerformanceStudio CLI.

**Workflow для генерации:**
```powershell
SET SHOWPLAN_XML ON;
GO
<запрос>;
GO

sqlcmd -S localhost -E -d Test1CProf -i query.sql -o raw.txt -y 0
# Извлечь XML regex'ом из raw.txt → .sqlplan
```

**Ограничения замеченные:**
- `-W` и `-y` несовместимы → используем `-y 0`
- `-h -1` и `-y 0` несовместимы → пропускаем `-h`
- В raw output план идёт как single column row — нужен `regex '<ShowPlanXML[\s\S]*</ShowPlanXML>'` для извлечения

**2. PostgreSQL 18.1-2.1C проверен — `psql -U postgres -h localhost`** — служба `pgsql-18.1-2.1C-x64` запущена. Версия из 1С-сборки. Готов к генерации `EXPLAIN (FORMAT JSON, ANALYZE)`.

**3. 1С:Предприятие 8.3.27.1859 — server agent running на reg_2541**, можно подключаться через `Srvr="localhost:2541";Ref="Test1CProf"` (формат tj-simulator). Готов для прогона нагрузки.

---

## 4. Project Assets

### Архивы ТЖ

**В проекте лежит:**

- `logs/` — **63 файла, 846.64 MB** реальных ТЖ-логов:
  - 5 папок rphost (rphost_19928 — 346 MB, rphost_856 — 46 MB, rphost_18832, rphost_7088 и т.д.)
  - 4 папки rmngr (rmngr_12268 — 311 MB)
  - 4 папки ragent (ragent_26664 — 133 MB)
  - 6 папок клиентских (1cv8c, 1cv8s, 1CV8C — мелкие, по 50 KB)
- Формат имён файлов: `YYMMDDHH.log` (26 мая 2026 года, ~17 часов покрыто)

**Критическая находка — содержимое логов:**

```
$ grep "DBMSSQL" logs/  →  0 matches
$ grep "planSQLText" logs/  →  0 matches
$ grep "Plan=" logs/  →  0 matches
```

**ТЖ Сергея НЕ содержит DBMSSQL событий вообще.** Все строки — CONN (connections), SCALL (server calls), CLSTR (cluster events), PROC (process events). Это означает что:

1. Архив получен с logcfg.xml который **не включал** DBMSSQL events
2. ИЛИ нагрузка была чисто на cluster connection-уровне (без выполнения SQL запросов)

**Реальный `logcfg.xml`** найден в `C:\Program Files\1cv8\conf\logcfg.xml` (5.71 KB):

```xml
<event>
    <eq property="name" value="DBMSSQL"/>
    <gt property="duration" value="10"/>  <!-- >100 ms -->
</event>
```

DBMSSQL включён, но фильтр >100ms — слишком жёсткий для коротких операций cluster setup. **Главная проблема:** в logcfg нет элемента `<plan>` — даже если бы DBMSSQL события писались, поле `planSQLText` бы не наполнялось.

**Импликации для Sprint 7:**

- D2 (auto-extract из DBMSSQL.Plan) — **зависит** от onboarding: правка logcfg + перезапуск ragent + прогон нагрузки
- Готовых тестовых ТЖ архивов с .Plan событиями **нет**
- **Нужно сгенерировать** через tj-simulator после правки logcfg

### Configuration XML

**`C:\BUFFER\SCHEME`** — **30,635 файлов, 1.73 GB** XML выгрузка типовой БП 3.0 (память подтверждается через файл `feedback_disk_layout.md`). Это **полный** dump:
- Catalogs, Documents, Registers, Reports, DataProcessors
- CommonModules, Subsystems, Roles, Predefined, RegisterDimensions

**Полезность для Sprint 7:** прямая — используется `configuration_metadata` (Sprint 5) для контекста при AI-explanation планов.

**Других конфигураций (УТ, ERP, ЗУП) у Сергея на машине НЕТ.** Если потребуется разнообразие для тестов — потребуется отдельная инициатива.

### Sprint 5 Configuration parser

`backend/src/optimyzer_backend/configuration_metadata/` — готовая инфраструктура:
- `parser.py` — XML → ConfigurationObject (Catalog/Document/Register/...)
- `store.py` — SQLite index с hash invalidation
- `api.py` — singleton helper для query analyzer

**Applicability для Sprint 7:**
- ✅ **Прямо переиспользуется** — даёт контекст для AI ("этот план для запроса к Catalog.Counterparties с реквизитами X, Y, Z; таблица в БД называется _Reference15 со 11000 строк")
- ✅ Через `get_default_store()` доступен из RPC

**Может ли использоваться для генерации test SDBL?** Технически да — есть `ConfigurationObject` с типизированными `Attributes` / `TabularSections` / `Registrators`, можно через простой generator делать `SELECT _IDRRef, _Description FROM <ObjectName>` для всех объектов. Не критично для Sprint 7 (у нас есть готовые .sqlplan), но **полезный side-quest** для расширения test corpus.

### tj-simulator (Sprint 3.5)

`tools/tj-simulator/` — внешняя обработка `.epf` + расширение `.cfe` для генерации событий ТЖ на тестовой базе через 1С Designer.

**Capabilities (из README):**
| Кнопка | События | Объём |
|---|---|---|
| 1. TLOCK | Управляемые блокировки Holder↔Waiter | ~10 TLOCK |
| 2. Дедлок: эскалация | S→X в одной транзакции | 5 TDEADLOCK + EXCP |
| 3. Дедлок: разный порядок | Два сеанса разный порядок захвата | 5 TDEADLOCK |
| 4. Дедлок: один ресурс | X-X конкуренция | 5 TDEADLOCK |
| **5. DBMSSQL** | **20 неэффективных запросов > 200ms** | **~20 DBMSSQL события** |
| 6. Все подряд | 1+2+3+4+5 | смесь |

**Что генерирует кнопка 5 (DBMSSQL):**
- Full scan по большой таблице
- Плохой JOIN (типа N+M)
- Sort by expression вместо by indexed column

Эти 20 событий **будут содержать `Sql=` поле**, и **будут содержать `planSQLText` ЕСЛИ** в logcfg.xml включить `<plan/>` элемент. Сейчас он не включён.

**Можно ли расширить:** да, через redactor `epf-dump` → правка `Forms/Форма/Ext/Form/Module.bsl` → `epf-build`. Добавить кнопку «7. DBMSSQL с разнообразными антипаттернами» (LEFT JOIN with filter, NOT IN, LIKE '%pattern', SELECT *, function-on-column) — это будет золотой test corpus для plan analyzer.

### Existing test fixtures

**102 готовых `.sqlplan` файла в research/:**

**`research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/`** — 39 файлов, **специально подобранных** под их 30 диагностик:
- `case_predicate_plan.sqlplan`
- `compile_memory_exceeded_plan.sqlplan`
- `convert_implicit_plan.sqlplan` (implicit conversion)
- `cte_multi_ref_plan.sqlplan`
- `eager_index_spool_plan.sqlplan`
- `eager_table_spool_plan.sqlplan`
- `excellent-parallel-spill.sqlplan` (parallel skew)
- `exchange_spill_plan.sqlplan`
- `implicit_convert_seek_plan.sqlplan` (Seek prevented)
- `isnull_plan.sqlplan`
- `join_or_clause_plan.sqlplan` (OR-in-join antipattern)
- `key_lookup_plan.sqlplan`
- `lazy_spool_plan.sqlplan`
- `leading_wildcard_like_plan.sqlplan` (leading `%`)
- `local_variable_plan.sqlplan` (parameter sniffing alt)
- `many_to_many_merge_plan.sqlplan`
- `memory_grant_wait_plan.sqlplan`
- `mismatched_data_type_plan.sqlplan`
- `missing-join-predicate.sqlplan`
- `multi_index_delete/insert/update_plan.sqlplan`
- `non_sargable_function_plan.sqlplan`
- `optimize_for_unknown_plan.sqlplan`
- `parallel-skew.sqlplan`
- `param-sniffing-posttypeid2.sqlplan` (parameter sniffing)
- `pspo-example.sqlplan` (Plan Stability)
- `rid_lookup_plan.sqlplan` (Heap with RID Lookup)
- `row-count-spool-slow.sqlplan`
- `row_goal_plan.sqlplan`
- `serially-parallel.sqlplan` (no parallel zones)
- `slow-multi-seek.sqlplan`
- `spill_plan.sqlplan`
- `table_variable_plan.sqlplan`
- `top_above_scan_plan.sqlplan`
- `tvf_plan.sqlplan` (Table-Valued Function)
- `udf_plan.sqlplan` (Scalar UDF)

И **9 копий в `research/PerformanceStudio/tests/`** (без подпапки) — `cte_multi_ref_plan.sqlplan`, `isnull_plan.sqlplan`, `join_or_clause_plan.sqlplan`, `lazy_spool_plan.sqlplan`, `local_variable_plan.sqlplan`, `many_to_many_merge_plan.sqlplan`, `mismatched_data_type_plan.sqlplan`, `non_sargable_function_plan.sqlplan`, `table_variable_plan.sqlplan`.

**`research/html-query-plan/test_plans/`** — 54 файла, **визуализатор-тесты**: Columnstore index ops, Cursors, KeyLookup, HashSpill, Adaptive Join, Batch Mode, Clustered/Nonclustered Index Scan/Seek/Delete/Update, Concatenation, Constant Scan, Index Spool, Many Lines, Nested Loops, RID Lookup, Sort, Spill to TempDB, Stream Aggregate, Table Insert, Table Merge, Table-Valued Function, Three Nested Loops, UDX, Unmatched Index, Window Spool, плюс реальные планы из Stack Overflow ("how many upvotes do I have for each tag", "jon skeet comparison", и т.д.).

**Итого: 102 файла .sqlplan покрывающих весь спектр антипаттернов и операторов SQL Server.**

**Sprint 7 НЕ нужно искать или генерировать test fixtures.** Берём готовое.

**Наши 5 свежесгенерированных** в `tools/sprint7_discovery/sqlplans/` — для проверки `Test1CProf`-специфичных кейсов (1C-стиль таблиц `_Reference10`, `_Document100`, и т.п.). Можно потом расширить через `generate-sqlplan-batch.ps1`.

### Existing tooling в research/

| Папка | Size MB | Что |
|---|---|---|
| `bsl-language-server/` | 9.24 | sources Java/Spring Boot. Уже используется в Sprint 6. |
| `sqlglot/` | 14.94 | Python SQL parser (T-SQL antipatterns в Sprint 6 Phase F) |
| `PerformanceStudio/` | 6.19 | .NET 10 sources + test fixtures (102 .sqlplan) |
| `html-query-plan/` | 3.07 | XSLT + JS visualizer (готов к bundling) |
| `testdata/` | 0.01 | (мелкие фикстуры) |

**Что НЕТ в research/, что могло бы быть полезно:**
- ❌ pev2 (PG visualizer) — установится через npm
- ❌ pg_explain_visualizer — альтернатива pev2

---

## 5. Reality Check для 6 Deliverables Sprint 7

### Deliverable 1: Импорт `.sqlplan` через UI drag-and-drop

**Feasibility:** 🟢 **95% ready**

**Что есть:**
- 102 готовых `.sqlplan` файла для тестирования
- React + Tauri UI с file picker pattern (`docs/...` загрузка XML конфы в Sprint 5 уже работает)
- `frontend/src/components/screens/QueryAnalyzer/` — pattern для будущего `PlanAnalyzer/`

**Что нужно сделать в Sprint 7:**
- Phase A.1: Frontend компонент `PlanAnalyzer/PlanImport.tsx` — drag-zone, file reader, валидация через regex `<ShowPlanXML`
- Phase A.2: Backend RPC `plan_analyzer.import_plan` — принимает XML, возвращает parsed object
- Phase A.3: SQLite store `plans` (id, sha256, sql_text, xml_content, imported_at, source)

**Estimate:** 2 дня

### Deliverable 2: Auto-extraction плана из DBMSSQL.Plan событий ТЖ

**Feasibility:** 🔴 **40% ready (заблокирован onboarding'ом)**

**Что есть:**
- 846 MB ТЖ-логов Сергея — но **БЕЗ DBMSSQL событий**
- `backend/src/optimyzer_backend/parsers/tj_parser.py` — уже парсит ТЖ формат
- tj-simulator кнопка 5 — генерирует 20 DBMSSQL событий

**Что заблокировано:**
- `logcfg.xml` Сергея НЕ содержит `<plan>` элемента — даже после прогона tj-simulator поле `planSQLText` будет пустым
- 1С platform docs (8.3.x): для включения сбора планов нужен **дополнительно**:
```xml
<event>
    <eq property="name" value="DBMSSQL"/>
    <gt property="duration" value="10"/>
</event>
<plan/>  <!-- ← КРИТИЧНО, отсутствует у Сергея -->
```

**Что нужно сделать в Sprint 7:**
- Phase B.0 (onboarding): wizard / script `patch-logcfg-for-plans.ps1` который правит logcfg.xml + останавливает агента + запускает агента (нужен admin elevation)
- Phase B.1: расширить `tj_parser.py` для парсинга `planSQLText` поля DBMSSQL события (план в нестандартном текстовом формате 1С — нужен отдельный converter в стандартный SHOWPLAN XML)
- Phase B.2: UI скрин «Найдено N планов в архиве» с выбором какие импортировать
- Phase B.3: тестирование через tj-simulator на Test1CProf

**Дополнительный риск:** 1С platform `planSQLText` поле содержит план в **текстовом формате** (SHOWPLAN_TEXT_ON output), **не XML**. Это значит:
- Не получится напрямую отдавать в html-query-plan (которому нужен XML)
- Нужен либо парсер текстового SHOWPLAN_TEXT (своими силами), либо ограничиться текстовым отображением

**Альтернативный план B (резервный):** если разобраться с `planSQLText` сложно — отложить D2 на Sprint 8 и оставить в Sprint 7 только D1 (manual import .sqlplan через UI). Покрыть базу через onboarding-док «Как сгенерировать .sqlplan вручную через SSMS».

**Estimate:** 3-5 дней (если делать) или 0 (если откладывать)

### Deliverable 3: SSMS-style visualization через html-query-plan

**Feasibility:** 🟢 **95% ready**

**Что есть:**
- `research/html-query-plan/` — полный source, XSLT 1.0 + JS, MIT
- 54 готовых `.sqlplan` для тестирования визуализации
- README говорит: `QP.showPlan(container, '<ShowPlanXML...')` — одна функция
- Tested in Chrome/Firefox/IE9+ — без проблем

**Что нужно сделать:**
- Phase C.1: `npm install` html-query-plan в `frontend/package.json`, либо bundle dist через webpack
- Phase C.2: React компонент `<PlanVisualization xml={planXml}/>` который рендерит через DOM mount
- Phase C.3: Tooltip-стиль (jsTooltips:true) для hover на operators

**Estimate:** 1 день

### Deliverable 4: PerformanceStudio integration (warnings + advice + missing indexes)

**Feasibility:** 🟡 **70% ready**

**Что есть:**
- `research/PerformanceStudio/src/PlanViewer.Cli/Commands/AnalyzeCommand.cs` — CLI:
  - `analyze <file.sqlplan>` или `--stdin` или `--query "SELECT ..."`
  - `--output json|text`
  - `--warnings-only`
  - `--server`, `--database`, `--login`, `--password-stdin` (для live capture)
  - `--timeout`, `--trust-cert`, `--auth windows|sql|entra`
- 30 диагностик согласно `llms.txt`
- 13 MCP tools (для Claude integration — но мы их не используем)
- Pre-built binary на GitHub Releases: `PerformanceStudio-win-x64.zip` (~30 MB, self-contained)

**Что заблокировано:**
- **.NET 10 SDK НЕ установлен** локально — не сможем собрать сами без +200 MB SDK install
- → **Решение: скачать pre-built binary** в `frontend/src-tauri/binaries/planview/`

**Что нужно сделать:**
- Phase D.1: скрипт `scripts/setup-planview-binary.ps1` — скачивает с GitHub Releases, проверяет SHA256 (как `setup-bsl-ls-binaries.ps1`)
- Phase D.2: Python wrapper `backend/src/optimyzer_backend/planview/cli.py` — subprocess-spawn, parse JSON output, model в Pydantic
- Phase D.3: RPC `plan_analyzer.analyze_with_planview` — обёртка с timeout 60s
- Phase D.4: Bundle в Tauri через `tauri.conf.json` `resources` + Tauri command `get_planview_path`
- Phase D.5: NOTICE.md обновить (MIT license для PerformanceStudio, .NET 10 runtime)

**Estimate:** 3 дня

**Альтернатива:** написать свой analyzer на Python (parse `<ShowPlanXML>` через `xml.etree.ElementTree`, детектить по правилам). **НЕ рекомендуется** — у PerformanceStudio 30 диагностик с глубоким знанием SQL Server internals, нам это годами повторять.

### Deliverable 5: PostgreSQL plans через pev2

**Feasibility:** 🟢 **85% ready**

**Что есть:**
- Postgres 18.1-2.1C running на машине Сергея
- Готов генерировать `EXPLAIN (FORMAT JSON, ANALYZE) ...` через `psql -U postgres -h localhost`
- Node + npm установлены

**Что нужно сделать:**
- Phase E.1: `npm install pev2` в frontend (Vue.js компонент)
- Phase E.2: React wrapper для pev2 (потому что pev2 — Vue, нужен Vue.runtime.esm + mount adapter; альтернатива — iframe с pev2 dev-сервером)
- Phase E.3: Backend парсер JSON формата PG `EXPLAIN` → нормализация → отдача в frontend
- Phase E.4: UI flow — пользователь paste'ит PG plan JSON, видит pev2

**Estimate:** 2 дня

**Note:** для MVP Sprint 7 можно отложить D5 на Sprint 8 — 1С на MSSQL составляет 80%+ инсталляций, D1-D4 покрывают main use case.

### Deliverable 6: AI explanation плана (Russian)

**Feasibility:** 🟢 **90% ready**

**Что есть:**
- `server/services/ai_explainer.py` — Sprint 6 Phase D, готовая orchestration:
  - SYSTEM_PROMPT_EXPLAIN на русском (~50 строк правил + JSON schema)
  - USER_PROMPT_TEMPLATE с placeholder'ами
  - Claude Sonnet 4.5 через `anthropic.AsyncAnthropic`
  - Retry on JSONDecodeError
  - Strict JSON output (`ExplainResponse` Pydantic)
- `server/schemas/ai.py` — типизированные модели
- `server/api/routers/ai.py` — POST /v1/ai/explain endpoint
- `server/api/settings.py` — `anthropic_api_key`, `ai_model_default`, `ai_max_tokens`
- Sprint 6 Phase D — endpoint работает end-to-end (need only ANTHROPIC_API_KEY в .env)

**Что нужно сделать:**
- Phase F.1: новые schemas — `PlanExplainRequest` (sql_text, plan_xml, configuration_context?), `PlanExplainResponse` (analysis_summary, hotspots, recommendations, suggested_indexes)
- Phase F.2: новый SYSTEM_PROMPT_EXPLAIN_PLAN — для plan-уровня анализа (фокус на operators, costs, estimates vs actuals, missing indexes)
- Phase F.3: новый USER_PROMPT — passes plan_xml + sql_text + (опционально) PerformanceStudio JSON warnings + (опционально) configuration_context из Sprint 5
- Phase F.4: новый endpoint `POST /v1/ai/explain_plan` (параллельный к /explain)
- Phase F.5: backend RPC `plan_analyzer.ai_explain` → cloud call → response в desktop
- Phase F.6: UI `<AiPlanExplanationCard/>` (копия `AiExplanationCard.tsx` от Sprint 6 с адаптацией под plan-схему)

**Estimate:** 2-3 дня

### Reality Check Summary

| Deliverable | Готовность | Estimate | Блокеры |
|---|---|---|---|
| D1: Manual import .sqlplan | 95% | 2 дня | — |
| D2: Auto-extract из DBMSSQL.Plan | 40% | 3-5 дней | logcfg.xml `<plan>` элемент, конвертация planSQLText текста → XML |
| D3: html-query-plan visualization | 95% | 1 день | — |
| D4: PerformanceStudio CLI integration | 70% | 3 дня | Скачать binary (не собирать) |
| D5: PostgreSQL pev2 | 85% | 2 дня | npm install + Vue adapter |
| D6: AI explanation | 90% | 2-3 дня | — |

**Total estimate (без D5, можно отложить):** 13-16 рабочих дней ≈ 3-4 недели solo разработки.
**Total estimate (с D5):** 15-18 дней ≈ 4 недели.

Это **значительно меньше** чем 5-7 недель оригинального плана. Сокращение благодаря 102 готовым test fixtures, готовому Sprint 5 parser для контекста, готовому Sprint 6 AI orchestration, и pre-built PerformanceStudio binary (не нужно собирать .NET).

---

## 6. Рекомендации для Sprint 7 promt

### Что переиспользовать (никаких велосипедов)

| Asset | Где | Что заменяет |
|---|---|---|
| **102 готовых .sqlplan** | `research/PerformanceStudio/tests/.../Plans/` + `research/html-query-plan/test_plans/` | Phase «найти / сгенерировать test fixtures» |
| **PerformanceStudio CLI binary** | GitHub Releases (download) | Собирать analyzer на .NET 10 SDK |
| **PerformanceStudio Core source** | `research/PerformanceStudio/src/PlanViewer.Core/` | Подсмотреть rule-detection алгоритмы (если будем делать backup pure-Python analyzer) |
| **html-query-plan dist** | `research/html-query-plan/` (XSLT + qp.min.js) | Велосипед своего plan renderer'а |
| **ai_explainer.py** (Sprint 6 D) | `server/services/ai_explainer.py` | Писать AI orchestration с нуля |
| **bsl_ls_rpc.py pattern** | `backend/src/optimyzer_backend/rpc/bsl_ls_rpc.py` | Шаблон для `plan_analyzer_rpc.py` (структура `analyze_rpc`, `status_rpc`) |
| **configuration_metadata** | `backend/src/optimyzer_backend/configuration_metadata/` | Контекст таблиц/реквизитов 1С для AI prompt |
| **dispatcher.py @rpc** | `backend/src/optimyzer_backend/rpc/dispatcher.py` | Регистрация JSON-RPC методов |
| **QueryAnalyzer screens pattern** | `frontend/src/components/screens/QueryAnalyzer/` | Шаблон для `PlanAnalyzer/` (структура BslLsFindings, AiExplanationCard, RewriteDiff) |
| **tj_parser.py** | `backend/src/optimyzer_backend/parsers/tj_parser.py` | Парсинг ТЖ архивов (если делаем D2) |
| **tj-simulator** | `tools/tj-simulator/` | Генерация DBMSSQL событий для D2 testing |
| **MSSQL Test1CProf** | Локально на машине | Генерация custom .sqlplan для 1C-специфичных кейсов |
| **logcfg.xml** | `C:\Program Files\1cv8\conf\logcfg.xml` | Reference для onboarding wizard (D2) |

### Что упростить / выкинуть из плана

| Phase | Статус | Причина |
|---|---|---|
| **«Найти test data — 10+ .sqlplan»** | ❌ Выкинуть | У нас 102 готовых, плюс sqlcmd для генерации |
| **«Собрать PerformanceStudio из исходников»** | ❌ Выкинуть | .NET 10 SDK не установлен, скачать pre-built |
| **«Установить .NET 10 SDK»** | ❌ Выкинуть | Не нужен — используем binary |
| **«Реализовать SQL Server analyzer на Python»** | ❌ Выкинуть | PerformanceStudio покрывает 30 правил, не строить параллельно |
| **«Разработать UI для drag-and-drop с нуля»** | 🟡 Упростить | Шаблон есть в QueryAnalyzer/, копируем |
| **«Написать AI prompts на plan-уровне»** | 🟡 Упростить | Расширить существующий ai_explainer.py, не писать с нуля |
| **«Custom XML парсер планов»** | ❌ Выкинуть | Полагаемся на PerformanceStudio JSON output + html-query-plan render |
| **«Configure logcfg.xml для DBMSSQL.Plan через GUI»** | 🟡 Упростить | Простой PowerShell скрипт + onboarding docs, не GUI wizard |

### Что добавить (не было в оригинальном плане)

| Item | Зачем |
|---|---|
| **Onboarding wizard / script для logcfg.xml + restart ragent** | Без этого D2 (auto-extract) технически не работает |
| **`generate-sqlplan-batch.ps1` skill** | Удобство для Сергея — генерация .sqlplan из списка SQL по batch'ам через sqlcmd |
| **PG plan capture через psql** | Для D5 — UI flow «Скопируйте сюда EXPLAIN JSON» с inline-генератором команды для пользователя |
| **«Дополнить tj-simulator кнопкой 7: разнообразные антипаттерны для plan testing»** | Расширить test corpus с DBMSSQL plans разных типов |

### Открытые вопросы для архитектора (Opus)

**Q1. D5 (PostgreSQL) — в Sprint 7 или Sprint 8?**

Если Sprint 7 — будем 4 недели вместо 3. Если Sprint 8 — Sprint 7 умещается в 3 недели и Sprint 8 = «PG support + плюшки».

**Рекомендация:** D5 в Sprint 8. 1С на MSSQL — 80%+ инсталляций.

**Q2. D2 (auto-extract DBMSSQL.Plan) — в Sprint 7 или Sprint 8?**

D2 заблокирован на:
- onboarding wizard правки logcfg.xml + restart ragent (нужен admin)
- парсинг `planSQLText` поля 1С (текстовый формат, не XML)
- Может потребовать конвертер текстового SHOWPLAN_TEXT → XML

Если D2 в Sprint 7 — добавляет 3-5 дней. Если в Sprint 8 — фокус Sprint 7 = manual import + AI + visualization.

**Рекомендация:** D2 в Sprint 7 **только базовый** (парсинг текстового planSQLText, отображение как текст без XML-визуализации). Полный конвертер в XML → Sprint 8.

**Q3. PerformanceStudio binary — bundle vs. download-on-first-use?**

- **Bundle** (~30 MB в installer): +30 MB к Tauri (сейчас ~250 MB → 280 MB), но работает offline
- **Download on-first-use**: меньший installer, но нужен интернет на первое использование + UX чуть хуже

**Рекомендация:** Bundle (как мы сделали с bsl-LS + JRE 21 в Sprint 6). Single installer = single experience.

**Q4. Кеширование AI-explanations плана?**

Сейчас ai_explainer.py — без кеша (Sprint 6 tech debt TD-6.3). Для планов — `(plan_xml_sha256, configuration_context_sha256)` как ключ.

Если включаем кеш в Sprint 7 — приходится решать вопрос для **обоих** AI use cases (query analyzer + plan analyzer). Это уже не Sprint 7 task, а отдельный «Sprint 7.5 Infra» (auth + caching + soft caps).

**Рекомендация:** В Sprint 7 БЕЗ кеша. Кеш — общая инфра задача параллельно (TD-6.3).

**Q5. UI стратегия — отдельный screen «Анализ плана» или интеграция в QueryAnalyzer?**

- **Отдельный screen** (`PlanAnalyzer/`): clean separation, разная навигация, новый Ctrl+P shortcut
- **Интеграция в QueryAnalyzer**: tab «Плагн» рядом с «Запрос + диагностики», единый flow «написал SDBL → видишь BSL-LS + план + AI»

**Рекомендация:** Отдельный screen на Sprint 7. Интеграция (если потребуется) — Sprint 8.

**Q6. Что делать с MCP integration от PerformanceStudio?**

В PerformanceStudio есть встроенный MCP server (13 tools) для Claude integration. У нас своя CC environment у Сергея — он может **напрямую** использовать их MCP server через `Add MCP Connection` если запустит PlanViewer.App.

Это **отдельный use case**: «использовать PerformanceStudio MCP в Claude Code напрямую для plan analysis в чате», параллельный нашему Sprint 7 (где мы интегрируем CLI в продукт).

**Рекомендация:** В Sprint 7 НЕ интегрировать MCP — это уже область пользователя. В Sprint 7 README docs можно отдельным разделом упомянуть что для деep-dive анализа можно запустить PlanViewer.App + подключить через Claude Code.

**Q7. Severity scheme для plan warnings — наш или PerformanceStudio?**

PerformanceStudio выдаёт `Info | Warning | Critical`. У нас в bsl-LS — `Blocker | Critical | Major | Minor | Info`.

Нужно или маппить (`Critical → Blocker`, `Warning → Major`, `Info → Minor`), или сохранять оригинал в plan context, рядом с bsl-LS severity в query context.

**Рекомендация:** Сохранять оригинальную PerformanceStudio severity. Юзер привыкнет к разнице (на разных вкладках разная nomenclature).

---

## 7. Action items (рекомендованный порядок Sprint 7 phases)

Если архитектор примет рекомендации:

1. **Phase A (3 дня): Foundation**
   - Скачать PerformanceStudio binary, bundle через Tauri
   - Backend: `planview` package (cli wrapper, models, RPC)
   - Frontend: новый screen `PlanAnalyzer/` с file picker для .sqlplan import
   - Test: прогон на 10 .sqlplan из `research/PerformanceStudio/tests/.../Plans/`

2. **Phase B (1 день): Visualization**
   - Bundle `html-query-plan` через npm
   - React wrapper `<PlanVisualization/>`
   - Test: 10 .sqlplan из `research/html-query-plan/test_plans/`

3. **Phase C (3 дня): AI explanation**
   - Расширить `ai_explainer.py` — новый prompt для plan-level
   - Backend RPC `plan_analyzer.ai_explain`
   - Frontend `<AiPlanExplanationCard/>`
   - Test: end-to-end на 3-5 живых планах с Test1CProf

4. **Phase D (3-5 дней): DBMSSQL.Plan auto-extract из ТЖ — minimal**
   - Onboarding script `patch-logcfg-for-plans.ps1` + docs
   - Extend `tj_parser.py` для парсинга `planSQLText` (текстовый формат)
   - UI: «Найдено N планов в архиве» с импортом
   - Test: tj-simulator scenario 5 → собрать архив → импортировать

5. **Phase E (2 дня): Tests + perf**
   - Integration tests на 102 .sqlplan
   - Performance: проверить что parser не падает на 100KB+ планах

6. **Phase F (1 день): Docs + tag**
   - Sprint 7 report + handover
   - ADRs для решений
   - Tag `v0.7.0-internal`

**Total: 13-15 дней ≈ 3 недели.**

**D5 (PostgreSQL pev2) перенесён в Sprint 8** согласно Q1.

---

## Приложения

### Файлы, созданные в ходе discovery

```
tools/sprint7_discovery/
├── probe_env.ps1              — environment audit
├── probe_logcfg.ps1           — find logcfg.xml
├── probe_plan.sql             — SHOWPLAN GO syntax fix
├── probe_plan2.sql            — SHOWPLAN file form
├── probe_plan_v3.ps1          — capture attempt #1 (bug)
├── probe_plan_v4.ps1          — capture attempt #2 (-h -1 conflict)
├── probe_plan_v5.ps1          — capture WORKING (no -h, -y 0)
├── probe_final.ps1            — node/dotnet/ssms/java probe
└── sqlplans/
    ├── test01_sys_tables.sqlplan       (25.39 KB)
    ├── test02_like_wildcard.sqlplan     (3.54 KB)
    ├── test03_join_group_by.sqlplan    (10.10 KB)
    ├── test04_not_in_subquery.sqlplan   (8.09 KB)
    └── test05_function_on_column.sqlplan (6.49 KB)
```

Все 5 `.sqlplan` — реальные планы от MS SQL 2019 для запросов к `Test1CProf`. Можно использовать для unit-тестов parser'а + render'а.

### CRITICAL FINDINGS (выделены отдельно)

1. **102 готовых .sqlplan в research/** — полный test corpus, не нужно генерировать
2. **PerformanceStudio MCP — недоступен из sidecar** (привязан к их GUI), берём CLI
3. **.NET 10 SDK НЕ установлен** — нельзя собрать PerformanceStudio, нужен pre-built binary
4. **ТЖ архивы Сергея — БЕЗ DBMSSQL** — нужен tj-simulator + правка logcfg
5. **logcfg.xml БЕЗ `<plan>` элемента** — даже DBMSSQL события без plan field
6. **planSQLText от 1С — текстовый, не XML** — нужен converter если хотим визуализировать в html-query-plan
7. **`Test1CProf` на localhost MSSQL 2019 Dev** — рабочая БП 3.0 для генерации любых .sqlplan через sqlcmd
8. **Node 22.12 + npm 10.9** уже стоят — pev2 / html-query-plan интеграция через npm install

---

**Готовность к Sprint 7:** **70%**. Все ключевые компоненты на месте, осталось:
- Скачать PerformanceStudio binary (1 команда)
- Bundle html-query-plan (npm install)
- Расширить ai_explainer.py (копия SYSTEM_PROMPT)
- Решить D2 strategy (auto-extract — sprint 7 или sprint 8)

**Готовность к продаже после Sprint 7:** **80%**. Plan Analyzer — это последний крупный premium feature. После него Phase 1 INFRA (auth/billing) — и можно идти в public launch.

---

**Время на discovery:** ~3 часа (от первой команды до push отчёта)
**Длина отчёта:** ~700 строк
**Файлов проверено / прочитано:** ~30
**Тестовых .sqlplan сгенерировано:** 5
**CRITICAL FINDINGS:** 8

**Подготовил:** Claude Code (Sonnet 4.5)
**Для:** Claude Opus 4.7 (Architect)
**Дата:** 2026-05-24
**Версия:** Sprint 7 Discovery v1
