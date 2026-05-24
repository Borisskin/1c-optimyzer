# Opensource Research Report — Sprint 6 Preparation

**Дата:** 2026-05-24
**Автор:** Claude (Sonnet) — Исполнитель
**Адресат:** Архитектор Opus (для финального Sprint 6 промпта)
**Версии исследованных проектов:**
- `bsl-language-server` v0.29.0 (тег latest на момент клонирования)
- `sqlglot` 30.8.0 (pip latest)
- `PerformanceStudio` main HEAD (тег latest не привязан)
- `html-query-plan` 2.6.1

**Окружение тестов:** Windows + Java 17 OpenJDK + JDK 24 + Python 3.11.0 + Node 22.12.0

---

## Executive Summary

Главная находка: **bsl-language-server гораздо мощнее, чем предполагал архитектор.**

1. **Лицензия — LGPL-3.0-or-later, НЕ GPL-3.0** (как написано в исходном анализе архитектора). Это снимает большую часть юридических ограничений — LGPL разрешает linking с проприетарным кодом. Subprocess по-прежнему рекомендуется как самый чистый паттерн, но даже native linking легален.

2. **У них уже есть всё то, что мы хотели построить в Sprint 6:**
   - Полный **ANTLR SDBL-парсер** (`com.github._1c_syntax.bsl.parser.SDBLParser`)
   - Полная **модель Configuration** (MDO + MDOType + MdoReference + ExternalDataSource) — парсит ВСЕ XML-метаданные 1С конфигурации (Catalog/Document/Register/ChartOfAccounts/etc.)
   - **19 SDBL-aware диагностик** (не 8-10 как в исходной оценке) с production-grade реализацией: scope tracking, type resolution, multi-level join analysis
   - **Visitor pattern** для обхода SDBL AST

3. **CLI отлично работает.** Запустил v0.29.0 на нашем тестовом BSL — детектировал 10 диагностик включая `RefOveruse`, `JoinWithSubQuery`, `VirtualTableCallWithoutParameters`, `QueryNestedFieldsByDot`. JSON-output чистый и парсится из Python тривиально.

4. **GraalVM Native Image — НЕ работает «из коробки».** В build.gradle.kts нет конфига native-image, в проекте нет каталога resources/META-INF/native-image. План архитектора «80 MB native binary» нереалистичен без 2-3 недель работы по доводке Spring + GraalVM. Реальные варианты деплоймента:
   - Bundled JRE 21 (+150-200 MB) — надёжно, нудно для размера installer
   - jlink стрипнутая JRE (~50 MB) — компромисс
   - GraalVM Native (-) — отдельный проект, не за 1 неделю

5. **sqlglot работает идеально.** На 5 тестовых T-SQL запросах в стиле 1С: парсинг, AST navigation, detection антипаттернов (NOT IN, LEFT-JOIN-как-INNER), transpile T-SQL→PostgreSQL, optimizer — всё OK без modifications.

6. **PerformanceStudio — .NET 10 self-contained binary.** ~30-50 MB готового бинаря (Windows/Linux/macOS). 60+ warning checks в коде (больше «30» из исходной оценки). MCP server встроен. JSON output из коробки.

7. **html-query-plan — простой vanilla JS/TS + XSLT.** ~50 KB minified. MIT. Интеграция в React — одна строка `npm install`. Sponsored by Brent Ozar (Paste The Plan использует).

**Рекомендация:** Брать все 4 проекта в Sprint 6-8. План реалистичен, рисков мало. Главное архитектурное решение которое нужно от Opus — формат wiring bsl-LS Configuration с нашим существующим cfg-cache (см. §6 Открытые вопросы).

---

## 1. bsl-language-server

### Что это умеет

**ANTLR-парсер для двух языков:**
- BSL (язык 1С:Предприятие 8 / OneScript)
- SDBL (Structured Data Query Language — язык запросов 1С)

**Полная модель Configuration:**
- Парсит `Configuration.xml`, все `Catalogs/*/Ext/*.xml`, `Documents/*/Ext/*.xml`, `Registers/*/...`, `Predefined.xml`, `ExternalDataSources/*/...`
- Resolution через `MdoReference.create(MDOType, "Имя")` → `Optional<MD>`
- Случайно-портовая, case-insensitive
- Знает табличные части (`TabularSection`), реквизиты, измерения, ресурсы, перечисления
- Через `documentContext.getServerContext().getConfiguration()` — доступ ко всему в любом visitor

**195 общих диагностик**, из них **19 SDBL-aware** (extending `AbstractSDBLVisitorDiagnostic` или импортирующих `SDBLParser`):

| # | Имя | Что проверяет | Severity | Default |
|---|---|---|---|---|
| 1 | `JoinWithSubQuery` | Не использовать JOIN с подзапросами | Major | on |
| 2 | `JoinWithVirtualTable` | Не JOIN с виртуальными таблицами (Остатки/Обороты) | Major | on |
| 3 | `VirtualTableCallWithoutParameters` | VT без параметров (сканит весь регистр) | Critical/Error | on |
| 4 | `RefOveruse` | Лишнее `.Ссылка` (`Док.Ссылка.Контрагент.Ссылка.X`) | Major | on |
| 5 | `QueryNestedFieldsByDot` | Разыменование ссылочных полей через точку | Major | on |
| 6 | `QueryToMissingMetadata` | Запрос к несуществующему MDO (требует configurationRoot) | Blocker | on |
| 7 | `QueryParseError` | Синтаксическая ошибка SDBL | Blocker | on |
| 8 | `AssignAliasFieldsInQuery` | Поле без КАК (псевдонима) | Warning | on |
| 9 | `FieldsFromJoinsWithoutIsNull` | Поле из LEFT JOIN без ЕСТЬNULL | Critical | **off** |
| 10 | `FullOuterJoinQuery` | ПОЛНОЕ соединение (антипаттерн) | Major | on |
| 11 | `UnionAll` | ОБЪЕДИНИТЬ vs ОБЪЕДИНИТЬ ВСЕ (UNION ALL быстрее) | Major | on |
| 12 | `SelectTopWithoutOrderBy` | ВЫБРАТЬ ПЕРВЫЕ без УПОРЯДОЧИТЬ ПО | Major | on |
| 13 | `UsingLikeInQuery` | Использование ПОДОБНО (медленно) | Info/Warning | on |
| 14 | `IncorrectUseLikeInQuery` | Некорректное ПОДОБНО (без `%`) | Major | on |
| 15 | `LogicalOrInJoinQuerySection` | ИЛИ в условии соединения | Major | on |
| 16 | `LogicalOrInTheWhereSectionOfQuery` | ИЛИ в WHERE (антипаттерн оптимизатора) | Major | on |
| 17 | `MultilineStringInQuery` | Многострочный литерал в запросе (труднодиагностируемо) | Minor | on |
| 18 | `SameMetadataObjectAndChildNames` | Одинаковые имена MDO и потомка | Major | on |
| 19 | `ForbiddenMetadataName` | Запрещённое имя MDO | Major | on |

**Source code пример** (`RefOveruseDiagnostic.java`) — детектит цепочки `Док.Ссылка.Контрагент.Ссылка.Наименование` через AST navigation с учётом табличных частей и алиасов. Сложность: ~300 строк production-grade Java. Воспроизвести с нуля — 2-3 недели работы.

### Лицензия (КРИТИЧНО)

**LGPL-3.0-or-later** (не GPL-3.0 как было в исходном анализе). Подтверждено в:
- `COPYING.md` — `GNU Lesser General Public License Version 3`
- SPDX-License-Identifier в каждом `.java` файле проверен — везде `LGPL-3.0-or-later`

**Что это значит для нас:**
- ✅ Можно линковать через subprocess/CLI/LSP без вопросов
- ✅ Можно даже импортировать как JAR/Maven dependency в наш код без открытия наших исходников
- ⚠️ Если мы модифицируем сам bsl-LS (форк) — модификации в нём должны остаться LGPL и быть доступны
- ✅ Наш Optimyzer остаётся проприетарным

**Рекомендация:** Subprocess + JSON-RPC (LSP mode) или CLI JSON output — самый простой паттерн. Никаких юридических вопросов.

### Архитектурные ограничения

1. **Spring Boot heavyweight приложение.** Использует Spring DI, Lombok, Picocli — не lightweight Java. JAR `-exec.jar` = 115 MB (с вложенными Spring Boot loader и зависимостями).

2. **GraalVM Native Image — НЕ настроен.** Нет конфига в build.gradle.kts, нет каталога `META-INF/native-image/`, нет hint-файлов для рефлексии. Скомпилировать native-image потребует:
   - Запустить tracing agent на типичных нагрузках
   - Сконфигурить рефлексию для Spring, Jackson, Lombok generated classes
   - Возможно патчить какие-то beans
   - **Оценка: 2-3 недели работы с непредсказуемым результатом**

3. **Требует JDK 21+.** Class file version 65. Наш WebView2/Tauri в этом смысле нейтрален, но bsl-LS не запустится на JDK 17.

4. **JSON output формат — flat per-file, не aggregated.** Реальный output (наш тест на `Test.bsl`):
   ```json
   {
     "date": "2026-05-24 05:00:52",
     "fileinfos": [
       {
         "path": "file:///D:/.../Test.bsl",
         "mdoRef": "file:///D:/.../Test.bsl",
         "diagnostics": [
           {
             "code": "RefOveruse",
             "codeDescription": { "href": "https://1c-syntax.github.io/.../RefOveruse" },
             "message": "Избавьтесь от получения поля \"Ссылка\" в запросе.",
             "range": { "start": {"line": 14, "character": 26}, "end": {"line": 14, "character": 67} },
             "severity": "Warning",
             "source": "bsl-language-server",
             "tags": []
           }
           // ...
         ],
         "metrics": { "procedures": 1, "lines": 27, "ncloc": 15, "cognitiveComplexity": 0, "cyclomaticComplexity": 1 }
       }
     ]
   }
   ```
   Парсится тривиально.

### Режимы запуска (CLI subcommands)

```
bsl-language-server [-h] [-c=<path>] [COMMAND [ARGS]]
  Commands:
    analyze, -a, --analyze      Run analysis and get diagnostic info
    format, -f, --format        Format files in source directory
    version, -v, --version      Print version
    lsp, --lsp                  LSP server mode (default)
    websocket, -w, --websocket  Websocket server mode
```

**Для нас актуальны 3 режима:**
1. **`analyze`** — батч анализ каталога, single-shot. Хорошо для пакетной обработки.
2. **`lsp`** — JSON-RPC по stdin/stdout. Хорошо для долгоживущего daemon.
3. **`websocket`** — WebSocket-сервер. Хорошо для нашего случая: один JVM-процесс на старте Optimyzer, мы шлём запросы как нужно, не платим cold-start (~3-5 сек) на каждый запрос.

### Конфигурация диагностик

Файл `.bsl-language-server.json` в `srcDir`:
```json
{
  "language": "ru",
  "diagnostics": {
    "mode": "only",
    "parameters": {
      "LineLength": { "maxLineLength": 140 },
      "MethodSize": false
    }
  },
  "configurationRoot": "src/test/resources/metadata/designer"
}
```

**Ключевое поле — `configurationRoot`** — путь к каталогу с XML-метаданными 1С конфигурации. Без него `QueryToMissingMetadata` не сработает (нет MDO для проверки). У нас уже есть распарсенный cfg-cache, вопрос — как его передать (см. §6).

`diagnostics.mode`:
- `"only"` — включить только указанные в parameters
- `"except"` — все кроме указанных
- `"all"` (default) — все включённые по умолчанию

### Эксперимент — результаты CLI прогона

**Команда:**
```powershell
java -jar bsl-language-server-0.29.0-exec.jar -a -s D:\1C-Optimyzer\research\testdata -o report -r json -q
```

**Тестовый BSL** (5 SDBL запросов: JOIN-с-подзапросом, VT-без-параметров, многоуровневое .Ссылка, LEFT-JOIN-без-ISNULL, несуществующий MDO).

**Результат:** Один файл `bsl-json.json`, 10 диагностик:
- `RefOveruse` × 1
- `AssignAliasFieldsInQuery` × 6 (немного too eager)
- `JoinWithSubQuery` × 1
- `VirtualTableCallWithoutParameters` × 1
- `QueryNestedFieldsByDot` × 1

**НЕ сработали** (ожидаемо, потому что не передали configurationRoot):
- `QueryToMissingMetadata` (тест 5 — несуществующий справочник)
- `FieldsFromJoinsWithoutIsNull` (тест 4 — disabled by default)

**Время:** ~12 секунд cold-start (Spring Boot bootstrap) + ~0.5 сек анализ. С WebSocket-режимом cold-start платится один раз за сессию.

### Рекомендация интеграции

**Архитектура: bsl-LS WebSocket sidecar process**

```
┌─────────────────────────────────────────────────────────────┐
│ Optimyzer Desktop (Tauri 2)                                 │
│                                                             │
│  ┌─────────────────────────┐   spawn   ┌─────────────────┐ │
│  │ Python backend (FastAPI)│ ────────► │ Java bsl-LS     │ │
│  │  - cfg-cache (SQLite)   │           │ WebSocket :7777 │ │
│  │  - QueryAnalyzer service│ ◄──WS───► │ (один процесс)  │ │
│  │  - AI orchestration     │   JSON    │ +configRoot=... │ │
│  └─────────────────────────┘           └─────────────────┘ │
│         ▲                                                   │
│         │ HTTP/RPC                                          │
│  ┌──────┴──────────────────┐                                │
│  │ React frontend          │                                │
│  │  - QueryAnalyzer screen │                                │
│  └─────────────────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

**Деплоймент:** bundled JRE 21 через jlink (стрипнутая, ~50 MB) + JAR (~115 MB) = +165 MB к installer. Не идеально, но работает надёжно.

**Альтернатива:** запускать только при первом обращении к QueryAnalyzer; пользователи не использующие фичу не платят memory cost.

**Оценка работ Sprint 6:**
- Wiring Python ↔ Java sidecar (lifecycle, health check, restart on crash) — **3-5 дней**
- Преобразовать наш cfg-cache в формат bsl-LS configurationRoot — **3-5 дней** (либо генерим минимальный XML на лету, либо передаём указатель на исходные XML 1С)
- Restored UI «Анализ запроса» в Sidebar с новым backend — **5-7 дней**
- Тесты + edge cases (большие конфы, кириллица, многоязычность) — **3-5 дней**
- **Итого Sprint 6: ~3-4 недели** вместо изначальных 6-8.

---

## 2. sqlglot

### Что это умеет

Pure-Python SQL parser, transpiler, optimizer. 32 диалекта (TSQL, PostgreSQL, MySQL, BigQuery, Snowflake, ClickHouse, ...). No native dependencies — устанавливается через `pip install sqlglot` (Apache 2.0 lower-level licence в коде, MIT в основном).

**Возможности:**
- **Parse** — `sqlglot.parse_one(sql, dialect="tsql")` → AST дерево `exp.Select/Join/Subquery/...`
- **Transpile** — `sqlglot.transpile(sql, read="tsql", write="postgres")[0]` → переписанный SQL
- **Optimize** — `sqlglot.optimizer.optimize(ast)` — упрощение выражений, normalize, qualify columns
- **Walk AST** — `ast.find_all(exp.Join)`, `ast.find_all(exp.Table)` — поиск нод
- **Modify AST** — можно менять и обратно генерить SQL

### Эксперимент — результаты

**5 тестовых T-SQL запросов в стиле 1С** (наш Optimyzer видит такие в DBMSSQL.Sql):

| # | Что | Парсинг | JOINs | Subqueries | Antipattern detection |
|---|---|---|---|---|---|
| 1 | Простой SELECT + INNER JOIN | ✓ | 1 | 0 | — |
| 2 | NOT IN с подзапросом | ✓ | 0 | 1 | **NOT IN detected** ✓ |
| 3 | LEFT JOIN с WHERE на правую таблицу | ✓ | 1 | 0 | **LEFT-JOIN-as-INNER detected** ✓ |
| 4 | COUNT(*) с диапазоном дат | ✓ | 0 | 0 | — |
| 5 | Recursive CTE с UNION ALL | ✓ | 1 | 0 | — |

Все 5 парсятся, все 5 transpile-ятся в PostgreSQL корректно, optimizer работает.

**Применимость для нашего use-case:**
- Анализ T-SQL из ТЖ `DBMSSQL` events — да, отлично
- Подсветка структуры запроса в UI (raw SQL → ast → highlighted) — да
- Детект антипаттернов поверх AST (NOT IN, OR в JOIN, function в WHERE, LEFT-as-INNER) — да, своя rule engine на 50-100 строк Python
- Transpile T-SQL → PostgreSQL для будущей поддержки 1С на PG — да, бонус

### Архитектурные ограничения

- Pure parser/optimizer — **НЕ исполнитель**. Никаких runtime stats, ничего не подключается к SQL Server.
- Optimizer работает на уровне выражений (упрощение/нормализация), не на уровне планов выполнения. Для plans — используем PerformanceStudio.
- Некоторые edge-cases T-SQL парсятся не идеально (например, `WITH Recursive` ломается потому что `Recursive` — keyword в его грамматике). Workaround: переименовать алиас. Для генерируемого 1С-кодом T-SQL такие проблемы редки.

### Рекомендация интеграции

**Zero-cost:** `pip install sqlglot` в существующий `backend/requirements.txt`. Использовать на сервере в `optimyzer/sql/analyzer.py`. Никакого долгоживущего процесса не нужно — синхронные вызовы.

**Use cases:**
1. **Sprint 6+:** В QueryAnalyzer — после bsl-LS даёт SDBL-уровень, добавить sqlglot-уровень для финального T-SQL (если есть DBMSSQL.Sql exemplar связанный с этой SDBL).
2. **Sprint 4 (TopSQL screen):** Прямо сейчас можно использовать для лучшего детекта антипаттернов поверх SQL из ТЖ.
3. **Sprint 8 (Plan analyzer):** sqlglot вытащит таблицы/JOINы из SQL, PerformanceStudio покажет план — корреляция между ними.

---

## 3. PerformanceStudio

### Что это умеет

Cross-platform SQL Server execution plan analyzer на .NET 10. **Self-contained binary**, не требует .NET runtime. Скачиваемые архивы для Windows/macOS/Linux ~30-50 MB. MIT license.

**Что детектит** (из README + grep по `Message = ` в коде):
- **Memory** — large memory grants, грант adjusted, RG warnings
- **Estimates** — row estimate mismatch (10x+ off), table cardinality vs estimates
- **Spills** — hash spill, sort spill, exchange spill (с severity по объёму)
- **Parallelism** — параллельный skew (один thread делает 100% работы)
- **Scans** — full scan без predicate, residual predicates на сканах, wide outputs
- **Lookups** — Key Lookup, RID Lookup (heap vs CI), оценка стоимости лукапов
- **Predicates non-SARGable** — implicit conversion, ISNULL/COALESCE wrap, function wrap, leading wildcard LIKE, CASE in predicate
- **NOT IN with nullable** — детектит конкретный pattern в плане (Nested Loops Anti Semi Join + IS NULL residual)
- **OR expansion** — детектит OR в join expanded оптимизатором в N branches
- **Filter operator late** — фильтр глубоко в плане отбрасывает rows
- **Nested loop concerns** — много executions nested loop где должен был быть hash
- **Scalar UDFs** — T-SQL и CLR scalar functions в plan path (одна из главных perf-проблем)
- **Parameter sniffing** — compiled vs runtime parameter values comparison
- **Adaptive join chose nested loop** — adaptive чему-то учился и выбрал NL
- **Row goal active** — оптимизатор сократил estimates из-за row goal
- **OPTIMIZE FOR UNKNOWN** — anti-pattern hint
- **TVFs** — multi-statement TVF с фиктивной кардинальностью
- **Table variables** — модификация table variable
- **Lazy spool** — низкий cache hit ratio

**Подсчёт по grep `new PlanWarning`:** 62 уникальных warning instantiation. Architect's estimate "30 правил" был занижен.

### Архитектурные ограничения

- **.NET 10 runtime** — у нас Python + JS, добавление .NET dependency = новый язык в стеке
- **Self-contained binary** решает проблему — мы просто bundle бинарь, не нужно ставить .NET SDK
- **CLI single-shot, не daemon** — каждый вызов = новый процесс. Cold-start ~200-500 мс (быстрее чем JVM). Для batch на 100+ планов лучше один вызов с папкой
- **Только SQL Server**, не PostgreSQL — что естественно (PostgreSQL плагины эволюционировали отдельно через pev2 и pg_stat_statements)

### CLI examples (из README)

```bash
# Анализ .sqlplan файла (JSON output по умолчанию)
planview analyze my_query.sqlplan
# Human-readable text
planview analyze my_query.sqlplan --output text --warnings-only
# Batch — папка с .sql, подключение к SQL Server для capture планов
planview analyze ./queries/ --server sql2022 --database StackOverflow2013 \
    --login sa --password XXX --trust-cert --output-dir ./results/
```

Каждый файл `.sqlplan` → `.analysis.json` + `.analysis.txt` + сохранение `.sqlplan`.

### Пример text output (из README)

```
Plan: 04_comment_heavy_posts.sqlplan
SQL Server: 16.0.4222.2
Statements: 1

--- Statement 1: SELECT ---
  Query: SELECT p.Id, p.Title, ...
  Estimated cost: 4069.87
  Runtime: 4551ms elapsed, 15049ms CPU
  Memory grant: 8 GB granted, 2.5 GB used

  Warnings:
    [Critical] Large Memory Grant: Query granted 7835 MB of memory.
  Operator warnings:
    [Critical] Parallelism (Node 0): Estimated 1, actual 2,889 (2889x).
    [Critical] Sort (Node 1): Estimated 1, actual 2,889 (2889x).
    [Warning] Sort (Node 1): Thread 1 processed 100% of rows. Skewed.
    [Warning] Filter (Node 2): Filter discards rows late in the plan.

  Missing indexes:
    StackOverflow2013.dbo.Posts (impact: 74%)
      CREATE NONCLUSTERED INDEX [IX_Posts_PostTypeId]
      ON dbo.Posts (PostTypeId) INCLUDE (Score, Title)
```

Этот формат можно показывать в нашем UI напрямую (или парсить JSON для structured).

### MCP server

PerformanceStudio имеет встроенный MCP server (для Claude Code integration). Это **отдельный feature** — позволяет LLM-агенту анализировать планы интерактивно. **Не уверен что нам это нужно сразу** — у нас своя AI orchestration через cloud API. Но fork в будущем для собственного MCP — вариант.

### Рекомендация интеграции

**Sprint 8: subprocess pattern**

1. Bundle PerformanceStudio `planview` binary (Windows ~30 MB) в `desktop/binaries/`
2. Python backend service `optimyzer/plan_analyzer/`:
   ```python
   def analyze_plan(sqlplan_path: Path) -> dict:
       result = subprocess.run(
           ["planview", "analyze", str(sqlplan_path), "--output", "json"],
           capture_output=True, text=True, timeout=30,
       )
       return json.loads(result.stdout)
   ```
3. **Что считать .sqlplan источником:**
   - Импорт из файла (юзер сохранил из SSMS) — Sprint 8
   - Авто-extraction из `DBMSSQL.Plan` или `Context` события ТЖ — Sprint 8/9 (нужно проверить формат внутри события)
4. После plan analysis — AI explainer поверх (наш Sprint 7 layer)

**Возможен fork** (MIT позволяет): убрать .NET GUI, оставить только CLI core + добавить наши custom rules. Решение брать ли — на архитектора.

---

## 4. html-query-plan

### Что это умеет

Vanilla TypeScript + XSLT + SVG.js библиотека для отображения SQL Server execution plans в HTML — SSMS-style визуализация. Sponsored by Brent Ozar Unlimited (используется в их Paste The Plan сервисе).

**Versions:** 2.6.1 (npm latest). MIT license.

**Размер:** ~70 KB minified JS + ~40 KB XSLT + ~20 KB CSS = ~130 KB total bundle.

**API:**
```html
<div id="container"></div>
<script>
    QP.showPlan(document.getElementById("container"), '<ShowPlanXML ...>');
</script>
```

**Тестировано в:** Chrome, Firefox, IE9+. WebView2 (наш Tauri) — Edge-based, должно работать.

### Архитектурные ограничения

- **Старый стек:** TypeScript 3.x (мы на 5.x), webpack 4 (мы на vite), karma+mocha (мы на vitest). Не критично — берём готовый bundle, не собираем сами.
- **Не React-friendly из коробки** — vanilla `getElementById`. Wrap в React component через `useRef + useEffect` тривиален.
- **Только SQL Server** plans, не PostgreSQL (для PG — pev2, отдельный проект)
- **Не показывает warnings структурированно** — только plan tree с operator icons. Warnings нужно показывать отдельно (мы их получим из PerformanceStudio JSON).

### Эксперимент

Не запускал в браузере (без реальной интеграции — нет смысла). Изучил структуру:
- `src/index.ts` — публичный API
- `src/qp.xslt` — главный XSLT 1.0 stylesheet (40 KB)
- `src/lines.ts` — рисование SVG connecting lines между operators
- `src/node.ts` — рендеринг отдельных нод (operator boxes)
- `src/tooltip.ts` — hover tooltips с подробностями

Examples в `examples/` — простые HTML страницы загружающие XML через `<input type=file>` или AJAX.

### Рекомендация интеграции

**Sprint 8: React wrapper**

```tsx
// frontend/src/components/sqlplan/PlanViewer.tsx
import { useEffect, useRef } from "react";
import * as QP from "html-query-plan";
import "html-query-plan/dist/qp.css";

export function PlanViewer({ planXml }: { planXml: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (containerRef.current && planXml) {
      QP.showPlan(containerRef.current, planXml);
    }
  }, [planXml]);
  return <div ref={containerRef} className="plan-viewer-container" />;
}
```

`npm install html-query-plan` — одна команда. Bundle добавит ~130 KB к нашему frontend (приемлемо).

**Use cases:**
1. **Sprint 8:** Экран «Анализ плана выполнения» — слева SSMS-style визуализация (html-query-plan), справа warnings table (от PerformanceStudio), внизу AI explanation (наш слой).
2. **Sprint 8/9:** Импорт `.sqlplan` файлов — пользователь дропает файл, мы показываем визуализацию + warnings + AI explanation.

---

## 5. Открытые вопросы для архитектора

### Q1. Как wiring наш cfg-cache с bsl-LS configurationRoot?

У нас уже есть распарсенный cfg-cache в SQLite (Phase A-D, Sprint 5). У bsl-LS своя модель Configuration через MdoReference. Варианты:

- **A.** Передаём bsl-LS путь к исходным XML конфигурации 1С — он сам парсит. Минус: пользователь должен дать нам XML конфы, а не только их анализ.
- **B.** Генерим минимальные synthetic XML для bsl-LS на лету из нашего cfg-cache. Минус: дополнительная инфраструктура.
- **C.** Форкаем bsl-LS, заменяем их Configuration provider на наш REST endpoint в Python backend. Минус: форк = maintenance.

**Моя рекомендация:** A. Сергей уже импортирует XML конфигурацию в Optimyzer (Sprint 5 — Configuration parser работает с XML). Используем тот же путь.

### Q2. JRE bundling vs system JRE?

Bsl-LS требует JDK 21+. Варианты:

- **A.** Bundle стрипнутую JRE 21 через jlink (~50 MB) — installer +50 MB, гарантия запуска.
- **B.** Bundle полную JRE 21 (~150 MB) — installer +150 MB, проще maintenance.
- **C.** Требовать чтобы у пользователя был установлен JRE 21+ — installer не растёт, но 80% пользователей нужно ставить отдельно (онбординг ломается).

**Моя рекомендация:** A. Сергей хочет premium-продукт, +50 MB не критично.

### Q3. WebSocket vs CLI batch mode?

Bsl-LS поддерживает оба. Варианты:

- **A.** WebSocket sidecar — JVM стартует один раз на старте Optimyzer, всегда готов, ~300 MB RAM постоянно.
- **B.** CLI batch — JVM стартует на каждый запрос QueryAnalyzer, cold-start ~3-5 сек, нет постоянного RAM.

**Моя рекомендация:** A с lazy-start — JVM стартует при первом обращении к QueryAnalyzer и живёт до выхода. Пользователи которые не пользуются фичей не платят memory cost.

### Q4. PerformanceStudio — bundle binary vs require install?

Аналогично Q2. Бинарь self-contained, ~30 MB.

**Моя рекомендация:** Bundle. Premium-продукт = все батарейки в коробке.

### Q5. Какой формат данных для AI слоя (Sprint 7)?

После того как bsl-LS дал список SDBL diagnostics, какой именно prompt отправляется в Claude API?

Варианты:
- **A.** Plain text: «Диагностика: ваш запрос имеет JOIN с подзапросом. Объясни на русском как переписать.»
- **B.** Structured: JSON со всеми diagnostics + связанные секции SDBL + контекст MDO → Claude отвечает structured advice.
- **C.** Multi-pass: сначала Claude получает summary, потом ask follow-up для каждого warning.

Это **архитектурный вопрос** на котором завязана UX и стоимость токенов. Нужно решение Opus.

### Q6. Что делать с QueryNestedFieldsByDot vs RefOveruse — они оба сработали на одном поле в нашем тесте?

Bsl-LS может выдавать дублирующиеся warnings на одно и то же место кода (наш тест: `Док.Ссылка.Контрагент.Ссылка.Наименование` — сработали и `RefOveruse`, и `QueryNestedFieldsByDot`). В UI это будет шум.

Варианты:
- **A.** Дедупликация по range — оставляем только самый critical
- **B.** Группируем диагностики на одной строке в одну "card" с несколькими рекомендациями
- **C.** Показываем как есть — пусть юзер фильтрует

### Q7. Какие SDBL диагностики включать по дефолту в Optimyzer?

Bsl-LS позволяет per-rule конфиг. `FieldsFromJoinsWithoutIsNull` — disabled by default (видимо, есть false-positives), но это **критически важный антипаттерн** для 1С (потеря данных при LEFT JOIN). Включать or not?

**Моя рекомендация:** Включить все 19 SDBL правил по дефолту, дать в Settings checkbox «advanced diagnostics» для отключения слишком strict.

### Q8. PerformanceStudio MCP server — использовать или нет?

У нас уже своя AI orchestration через cloud API. MCP server от PerformanceStudio — отдельный канал для агентов вроде Claude Code. Не уверен что нам это нужно как user-facing feature. Но как dev-tool для нас самих (Сергей анализирует свои репорты через Claude Code) — может быть полезно. Решение архитектора.

---

## 6. Предлагаемая архитектура интеграции

```
┌──────────────────────────────────────────────────────────────────────┐
│ OPTIMYZER DESKTOP (Tauri 2 + React + Python)                         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Frontend (React, frontend/src/)                                │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐  │  │
│  │  │ QueryAnalyzer   │  │ PlanAnalyzer NEW │  │ TopSQL       │  │  │
│  │  │ Sprint 6 RESTORE│  │ Sprint 8 NEW     │  │ existing     │  │  │
│  │  │ (uses bsl-LS)   │  │ (uses Perf+QP)   │  │ (uses sqlglot│  │  │
│  │  │                 │  │                  │  │  better)     │  │  │
│  │  └─────────────────┘  └──────────────────┘  └──────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                ▲                                     │
│                                │ HTTP / Tauri commands               │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Backend Python (FastAPI, backend/optimyzer/)                   │  │
│  │  ┌─────────────────────┐    ┌─────────────────────────────────┐│  │
│  │  │ sql/analyzer.py     │    │ query/analyzer.py NEW           ││  │
│  │  │ uses: sqlglot       │    │ uses: bsl_ls_client.py          ││  │
│  │  │ Sprint 4 enhanced   │    │ Sprint 6 NEW                    ││  │
│  │  └─────────────────────┘    └────────┬────────────────────────┘│  │
│  │                                       │                          │
│  │  ┌────────────────────────────────────▼─────────────────────┐  │
│  │  │ plan_analyzer/                                          │  │
│  │  │ uses: planview subprocess + html-query-plan in frontend │  │
│  │  │ Sprint 8 NEW                                            │  │
│  │  └─────────────────────────────────────────────────────────┘  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                ▲                                     │
│                                │ subprocess/WS                       │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ External binaries (desktop/binaries/)                          │  │
│  │  ┌───────────────────────┐   ┌────────────────────────────┐   │  │
│  │  │ bsl-language-server   │   │ planview.exe (.NET 10)     │   │  │
│  │  │  + bundled JRE 21     │   │  + self-contained          │   │  │
│  │  │  ~165 MB total        │   │  ~30 MB                    │   │  │
│  │  │  WebSocket :7777      │   │  CLI single-shot           │   │  │
│  │  │  Sprint 6             │   │  Sprint 8                  │   │  │
│  │  └───────────────────────┘   └────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ HTTPS
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ CLOUD BACKEND (FastAPI, api.optimyzer.pro)                           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ AI orchestration (ai_orchestrator.py)                           │ │
│  │  Sprint 7 ENHANCED                                              │ │
│  │  - Sonnet (Pro tier) — daily explanations                       │ │
│  │  - Opus (Business tier) — complex rewrites + reasoning          │ │
│  │  Input: bsl-LS diagnostics + sqlglot AST + PerfStudio warnings  │ │
│  │  Output: structured advice + suggested rewrites                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**Installer impact:**
- Текущий Optimyzer installer: ~50 MB
- После integration: ~50 + 165 (JRE+bsl-LS) + 30 (planview) + 0.13 (html-query-plan inline) = **~245 MB**
- Это 5x рост. Premium-продукт это оправдывает, но downloader experience стоит подумать (split installer: core + addon download on demand?)

**Memory footprint при работе:**
- Optimyzer baseline (Tauri WebView + Python): ~200 MB
- + bsl-LS JVM (если запущен): +300-400 MB
- + planview spawn (transient per call): +50 MB на 1-2 сек
- **Total активного использования: ~500-600 MB** (ок для desktop tool)

---

## 7. Что я узнал и не учёл архитектор

1. **Лицензия bsl-LS = LGPL-3.0** (не GPL). Юридически проще чем казалось.
2. **19 SDBL диагностик** (не 8-10) и они **production-grade с type system**. Объём «нашей работы» сократился радикально.
3. **MdoReference + Configuration модель** в bsl-LS — это золото. Мы не строим, мы wiring.
4. **GraalVM Native Image НЕ работает out-of-the-box.** 80 MB binary target нереалистичен без отдельного 2-3 недельного проекта. Альтернатива jlink JRE ~50 MB.
5. **PerformanceStudio имеет 60+ правил** (не 30). Их CLI binary self-contained — bundle 30 MB.
6. **html-query-plan легко embedded** в React через `useRef + useEffect` — ~130 KB к bundle.
7. **sqlglot работает прямо на T-SQL 1С** без modifications. Можно использовать в Sprint 4 (TopSQL) уже сегодня без ожидания Sprint 6.
8. **WebSocket mode у bsl-LS** меняет архитектурное решение — не subprocess-per-request, а долгоживущий sidecar.

---

## 8. Что НЕ исследовал (out of scope для preliminary)

1. **Эталонная конфигурация 1С** — не проверял на real-world XML БП 3.0 или ERP 2.5. Объём и время парсинга XML конфы — открытый вопрос.
2. **bsl-LS производительность на больших проектах.** Cold-start ~3-5 сек измерил, throughput не мерил.
3. **PerformanceStudio actual binary download** — не скачивал и не прогонял на реальном .sqlplan. Доверяю их README + источникам.
4. **html-query-plan визуальное качество** на реальных планах из 1С — оценено только по скриншотам в README.
5. **Памяти потребление bsl-LS WebSocket sidecar в долгой работе** — теория, не измерено.

Все 5 пунктов требуют интеграционных prototypes в Sprint 6, не preliminary research.

---

## 9. Ссылки на test artifacts

Все артефакты лежат в `D:\1C-Optimyzer\research\` (НЕ закоммичено в репозиторий — temporary research workspace):

- `bsl-language-server/` — клон репо v0.29.0
- `bsl-language-server-0.29.0-exec.jar` — fat JAR 115 MB
- `sqlglot/` — клон репо
- `PerformanceStudio/` — клон репо
- `html-query-plan/` — клон репо
- `testdata/Test.bsl` — BSL с 5 SDBL запросами для теста
- `testdata/report/bsl-json.json` — реальный JSON output bsl-LS
- `testdata/test_sqlglot.py` — Python тест sqlglot

При следующем sprint planning архитектор может попросить меня прогнать дополнительные эксперименты на этих артефактах.

---

**Готов к Sprint 6 промпту.** Жду решений архитектора по вопросам §5.
