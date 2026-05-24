# Sprint 6 — Query Analyzer Restoration via bsl-language-server

> Восстановление и **значительный апгрейд** функциональности «Анализ запроса» через интеграцию с opensource проектом bsl-language-server. Это **главный premium-feature** Pro/Business тарифов.
>
> **Базовый источник:** Opensource Research Report от 2026-05-24 (`docs/sales_sprint/OPENSOURCE_RESEARCH_REPORT.md`)

---

## Контекст для исполнителя

**Кто работает:** Claude Code на машине Сергея (`D:\1C-Optimyzer\`).
**Что есть на входе:** v0.5.0 с **скрытым** QueryAnalyzer (commit `d993655` + `ec8de15` 3 недели назад). Backend RPC + semantic rules + Configuration parser **не тронуты, работают**. UI скрыт из Sidebar.
**Что было в Sprint 4-5:** собственный regex-based SDBL semantic validator с 8 правилами + Configuration parser БП 3.0 (1647 объектов, 10.09 сек).
**Почему скрыли:** regex-based подход фундаментально ограничен — не понимает scope подзапросов, type chasing, виртуальных таблиц. Decision был «precision >> recall, пока precision < 100% — не показываем».

**Что меняет Sprint 6:** интеграция с **bsl-language-server v0.29.0** (LGPL-3.0) даёт нам **19 production-grade SDBL диагностик** с полной MDO type resolution, scope tracking, type chasing. Наш собственный regex-валидатор полностью заменяется на bsl-LS как **первичный source of truth**. Наша же логика становится **AI orchestration слоем поверх** их диагностик.

**После Sprint 6:** QueryAnalyzer **снова видим в Sidebar**, **намного функциональнее** чем до hiding, является **главной демонстрируемой фичей Pro тарифа** (9 900 ₽/мес).

---

## Архитектурные решения (приняты архитектором, не пересматриваем)

Перед началом работы — все 8 открытых вопросов из preliminary research разрешены:

### Q1. Wiring cfg-cache с bsl-LS configurationRoot → Вариант A

bsl-LS получает **прямой путь к XML конфигурации 1С** через параметр `configurationRoot` в его `.bsl-language-server.json`. Юзер уже даёт нам XML через Settings → «Подключить конфигурацию» (Sprint 5 функция). **Наш cfg-cache (SQLite) остаётся** как самостоятельный быстрый lookup для наших собственных нужд (например, в UI для autocomplete) — но **для bsl-LS даём оригинальные XML**. Это устраняет проблему синхронизации двух источников правды.

### Q2. JRE bundling → Вариант B (полная JRE 21, не jlink, не GraalVM)

Bundle полная **Eclipse Temurin JRE 21** (~150 MB) с installer. Не делаем jlink — premium product = no compromises on reliability. GraalVM Native — out of scope (это отдельный 2-3 недельный проект с непредсказуемым результатом). Размер installer вырастет с ~50 MB до **~250 MB total**, Сергей подтвердил что это приемлемо.

### Q3. WebSocket vs CLI → Вариант A с lazy-start

**WebSocket sidecar** запускается при **первом** обращении к QueryAnalyzer (lazy-start). Живёт до выхода Optimyzer. RAM footprint ~300-400 MB (приемлемо). Пользователи которые не пользуются QueryAnalyzer не платят memory cost. Health-check каждые 30 сек, auto-restart at crash (max 3 retry, потом graceful fail с user notification).

### Q4. PerformanceStudio bundle → Bundle (но это Sprint 8, не сейчас)

В Sprint 6 не интегрируем — это для Sprint 8 (Plan Analyzer). Упоминаю чтобы понимать общий roadmap.

### Q5. Формат данных для AI слоя → Вариант B — Structured JSON

AI orchestration работает на **structured input → structured output**. Не plain text prompts.

**Input в AI:**
```json
{
  "query_sdbl": "ВЫБРАТЬ ...",
  "diagnostics": [
    {
      "code": "RefOveruse",
      "message": "Избавьтесь от .Ссылка",
      "range": {"start": {"line": 5, "character": 12}, "end": {"line": 5, "character": 35}},
      "severity": "Major",
      "snippet": "Док.Ссылка.Контрагент.Ссылка.Наименование"
    },
    ...
  ],
  "configuration_context": {
    "mdo_types_used": ["Document.РеализацияТоваровУслуг", "Catalog.Контрагенты"],
    "tabular_sections_used": [...],
    "registers_used": [...]
  },
  "related_tj_events": null  // или summary, если SDBL извлечён из ТЖ
}
```

**Output от AI:**
```json
{
  "explanation_summary": "Запрос имеет 3 проблемы производительности и одну архитектурную ошибку.",
  "issues": [
    {
      "title": "Лишнее .Ссылка в цепочке полей",
      "severity": "Major",
      "what": "В строке 5 цепочка .Ссылка.Контрагент.Ссылка дублирует разыменование",
      "why": "Каждое .Ссылка генерирует дополнительный JOIN в T-SQL...",
      "what_to_do": "Замените `Док.Ссылка.Контрагент.Ссылка.Наименование` на `Док.Ссылка.Контрагент.Наименование`",
      "linked_diagnostic_codes": ["RefOveruse"]
    },
    ...
  ],
  "suggested_rewrite": {
    "available": true,
    "sdbl": "ВЫБРАТЬ ..."
  }
}
```

**Зачем structured:** позволяет в UI показывать grouped cards вместо wall of text, кешировать детерминированно, multi-language готовность, лучше качество output, possible future Action Items integration.

### Q6. Дедупликация диагностик → Вариант B — Группировка в одну card

Если bsl-LS выдаёт 2+ diagnostics на одно и то же место кода (одинаковый или overlapping range) — **группируем в одну UI card** с несколькими сообщениями. Severity = max из группы. Это premium UX, не overload.

**Алгоритм:** два warnings считаются «overlapping» если их ranges пересекаются по AST node level (одна и та же expression). Группируем все overlapping в одну логическую issue.

### Q7. Какие SDBL правила включать → Все 19 + категоризация

Все 19 SDBL правил **включены по дефолту**. В UI группируем по severity:

- **Blocker / Critical** (всегда показываем): `QueryParseError`, `QueryToMissingMetadata`, `VirtualTableCallWithoutParameters`, `FieldsFromJoinsWithoutIsNull`
- **Major** (всегда показываем): `JoinWithSubQuery`, `JoinWithVirtualTable`, `RefOveruse`, `QueryNestedFieldsByDot`, `FullOuterJoinQuery`, `UnionAll`, `SelectTopWithoutOrderBy`, `IncorrectUseLikeInQuery`, `LogicalOrInJoinQuerySection`, `LogicalOrInTheWhereSectionOfQuery`, `SameMetadataObjectAndChildNames`, `ForbiddenMetadataName`
- **Warning / Info** (toggle в Settings, default OFF): `AssignAliasFieldsInQuery`, `UsingLikeInQuery`, `MultilineStringInQuery`

`FieldsFromJoinsWithoutIsNull` — bsl-LS disable by default, но мы **включаем принудительно** — это критически важный антипаттерн для 1С (потеря данных). Если будут false positives — отключим в follow-up.

### Q8. PerformanceStudio MCP server → Не используем

У нас своя AI orchestration через cloud API. MCP server отдельный канал для agent integrations — возможно в Year 2.

---

## Дополнительные архитектурные решения

### AI orchestration — через cloud backend

AI слой работает **через наш cloud backend** `api.optimyzer.pro`, **не напрямую** из desktop в Anthropic API. Endpoints:

- `POST /v1/ai/explain` — получить structured explanation для query + diagnostics
- `POST /v1/ai/rewrite` — получить переписанный запрос с reasoning

**Преимущества:**
- API key защищён на сервере, не утечёт через desktop
- Centralized caching (один и тот же запрос анализируется один раз для всех юзеров)
- Multi-model routing (Sonnet для Pro, Opus для Business)
- Usage tracking для soft caps
- Возможность fine-tuning prompts без релиза desktop

**В Sprint 6 backend на cloud делаем minimal:** один endpoint `/v1/ai/explain` с hardcoded Sonnet, без caching (это придёт в Phase 1 INFRA). На время разработки Sprint 6 — backend временно живёт на localhost у Сергея.

### Не форкаем opensource

- bsl-LS — используем upstream **v0.29.0** через subprocess. Никакого fork. Updates через downloading new versions.
- При баг репортах — сначала фиксим в нашем adapter (workaround), потом upstream PR если критично.
- PerformanceStudio (Sprint 8) — аналогично.

### sqlglot — добавляем как pre-dependency

`sqlglot 30.8.0` устанавливается в backend как dependency в Sprint 6 (через `pip install sqlglot`). Используется в **двух местах**:

1. **TopSQL screen** (улучшение existing) — detect антипаттернов в T-SQL из DBMSSQL событий
2. **QueryAnalyzer** — если в SDBL запросе есть связанный T-SQL exemplar (из ТЖ), показать его с подсветкой структуры + antipatterns

Это **бонус-интеграция** в рамках Sprint 6, не отдельный sprint.

### Восстановление UI — minimal diff

В UI **не** делаем radical redesign. Берём текущий код QueryAnalyzer (он живой в репо, просто скрыт), модифицируем по минимуму:

- Backend RPC заменяется на новый endpoint `/api/query/analyze` который обращается к bsl-LS sidecar
- Отображение findings — расширяется по новой структуре (groups, severity colors, expandable cards)
- AI Explanation card — наполняется новой structured data
- ConfigurationBadge — остаётся, но теперь его статус влияет на bsl-LS lifecycle (нет конфы → ограниченный анализ)

---

## Структура Sprint 6 (Phase A-H)

| Phase | Что делается | Длительность | Stop rule |
|---|---|---|---|
| **A** | Bundling bsl-LS + JRE 21 в installer | 3-4 дня | Optimyzer installer работает на чистой Windows VM |
| **B** | Python adapter — WebSocket client + JSON-RPC | 4-5 дней | Unit-тесты coverage > 80%, integration test на тестовом BSL |
| **C** | Configuration wiring — Settings UI + bsl-LS configurationRoot | 3-4 дня | E2E test: подключил Configuration → semantic validation работает |
| **D** | Cloud AI orchestration backend (`/v1/ai/explain`) | 3-4 дня | Endpoint работает на localhost, есть unit/integration tests |
| **E** | UI restoration + extension в desktop | 5-7 дней | E2E test: вставил SDBL → видишь findings + AI explanation |
| **F** | sqlglot integration в TopSQL + QueryAnalyzer T-SQL view | 3-4 дня | sqlglot работает в обоих местах, antipatterns detect-ятся |
| **G** | Tests + edge cases + performance | 3-5 дней | Backend tests > 500 (+50 за Sprint 6), frontend tests > 100 |
| **H** | Documentation + closure + tag v0.6.0-internal | 1-2 дня | docs/SPRINT_6_REPORT.md + handover для архитектора |

**Итого: 25-35 дней (5-7 недель)** последовательной работы.

Phase A-D могут идти **немного параллельно** (А и B независимы, можно начать B пока A в pending). C зависит от B. D независим от A-C (cloud backend). Но **последовательно — проще для mental load**, согласно решению с пересборкой стратегии.

---

# PHASE A — Bundling bsl-LS + JRE 21

## Цель

Optimyzer installer должен включать всё необходимое для запуска bsl-LS на чистой Windows машине без дополнительной установки Java.

## Структура deployment

```
D:\1C-Optimyzer\
└── desktop\binaries\
    ├── jre-21\              ← Eclipse Temurin JRE 21 для Windows x64
    │   ├── bin\
    │   │   ├── java.exe
    │   │   └── ...
    │   ├── conf\
    │   └── lib\
    └── bsl-ls\
        └── bsl-language-server-0.29.0-exec.jar   ← 115 MB fat JAR
```

При установке Optimyzer всё это **копируется в `%ProgramFiles%\Optimyzer\bin\`** или (для portable) рядом с .exe.

## Конкретные шаги

### Шаг 1. Скачать и проверить Eclipse Temurin JRE 21

Источник: https://adoptium.net/temurin/releases/?package=jre&version=21&os=windows&arch=x64

Скачать **Windows x64 JRE 21 LTS** (около ~50 MB ZIP, ~150 MB распакованный).

Проверить SHA256 checksum с сайта.

Распаковать в `D:\1C-Optimyzer\desktop\binaries\jre-21\`.

Проверить: `desktop\binaries\jre-21\bin\java.exe -version` → выводит `openjdk version "21.x.x"`.

### Шаг 2. Скачать bsl-language-server v0.29.0

Источник: https://github.com/1c-syntax/bsl-language-server/releases/tag/v0.29.0

Скачать `bsl-language-server-0.29.0-exec.jar`.

Положить в `D:\1C-Optimyzer\desktop\binaries\bsl-ls\bsl-language-server-0.29.0-exec.jar`.

Проверить: `desktop\binaries\jre-21\bin\java.exe -jar desktop\binaries\bsl-ls\bsl-language-server-0.29.0-exec.jar --version` → выводит `bsl-language-server 0.29.0`.

### Шаг 3. Добавить в Tauri bundling config

В `desktop\src-tauri\tauri.conf.json` секция `bundle.resources`:

```json
{
  "bundle": {
    "resources": [
      "binaries/jre-21/**/*",
      "binaries/bsl-ls/*.jar"
    ]
  }
}
```

Это обеспечит копирование при `tauri build`.

### Шаг 4. Tauri command для resolution пути

В `desktop\src-tauri\src\main.rs` добавить tauri command:

```rust
#[tauri::command]
fn get_bsl_ls_paths(app: tauri::AppHandle) -> Result<BslLsPaths, String> {
    let resource_dir = app.path_resolver()
        .resource_dir()
        .ok_or("Failed to resolve resource dir")?;
    Ok(BslLsPaths {
        java_executable: resource_dir.join("binaries/jre-21/bin/java.exe").to_string_lossy().into(),
        bsl_ls_jar: resource_dir.join("binaries/bsl-ls/bsl-language-server-0.29.0-exec.jar").to_string_lossy().into(),
    })
}

#[derive(serde::Serialize)]
struct BslLsPaths {
    java_executable: String,
    bsl_ls_jar: String,
}
```

Зарегистрировать в `tauri::Builder::default().invoke_handler(...)`.

### Шаг 5. License attribution

В `desktop\LICENSE` или `desktop\NOTICE.md` добавить:

```markdown
## Third-Party Components

### bsl-language-server
- License: LGPL-3.0-or-later
- Source: https://github.com/1c-syntax/bsl-language-server
- Used as: subprocess via WebSocket/JSON-RPC
- Modifications: none

### Eclipse Temurin JRE 21
- License: GPL-2.0 with Classpath Exception
- Source: https://adoptium.net/

### sqlglot
- License: MIT
- Source: https://github.com/tobymao/sqlglot
```

В UI добавить ссылку на `NOTICE.md` в About → Licenses.

### Шаг 6. Verify on clean Windows VM

**Stop rule Phase A:** установить Optimyzer на чистой Windows 11 VM (без preinstalled Java). Запустить. Settings → Аккаунт → нажать «test bsl-LS» (временная кнопка для проверки, удалить в Phase E). Должно успешно выйти на консоль bsl-LS версии.

## Acceptance criteria Phase A

- [ ] Eclipse Temurin JRE 21 распакован в `desktop\binaries\jre-21\` (~150 MB)
- [ ] bsl-language-server-0.29.0-exec.jar в `desktop\binaries\bsl-ls\` (~115 MB)
- [ ] Tauri command `get_bsl_ls_paths` возвращает корректные пути
- [ ] `tauri build` производит installer ~250 MB
- [ ] Installer работает на чистой Windows 11 VM
- [ ] NOTICE.md с attribution всех 4 opensource components
- [ ] About → Licenses в UI показывает ссылку на NOTICE.md

**Длительность:** 3-4 дня.

---

# PHASE B — Python adapter для bsl-LS

## Цель

Backend Python код взаимодействует с bsl-LS через WebSocket sidecar. Lazy-start, health-check, auto-restart, graceful shutdown.

## Структура

```
backend\optimyzer\
└── bsl_ls\
    ├── __init__.py
    ├── client.py          ← WebSocket client + lifecycle
    ├── lifecycle.py       ← spawn JVM, monitor, restart
    ├── protocol.py        ← JSON-RPC message types (LSP-based)
    ├── parser.py          ← парсинг output bsl-LS в наши Python модели
    ├── models.py          ← Pydantic models: Diagnostic, Range, Severity, ...
    └── tests\
        ├── test_lifecycle.py
        ├── test_protocol.py
        ├── test_parser.py
        └── fixtures\
            ├── sample_bsl_files\
            └── expected_outputs\
```

## Lifecycle (spawn / monitor / restart)

`lifecycle.py`:

```python
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

class BslLsLifecycle:
    def __init__(self, java_exe: Path, jar: Path, port: int = 7777):
        self.java_exe = java_exe
        self.jar = jar
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.crash_count = 0
        self.max_crashes = 3

    async def start(self) -> None:
        """Spawn JVM with bsl-LS in WebSocket mode."""
        if self.process and self.process.poll() is None:
            return  # already running
        self.process = subprocess.Popen([
            str(self.java_exe),
            "-jar", str(self.jar),
            "websocket",
            "--port", str(self.port),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Wait for "Server started" log line, or timeout
        await self._wait_ready(timeout_s=30)

    async def health_check(self) -> bool:
        """Check if JVM is alive and responsive."""
        if not self.process or self.process.poll() is not None:
            return False
        # Try WebSocket ping
        try:
            async with websockets.connect(f"ws://localhost:{self.port}", timeout=5) as ws:
                await ws.ping()
                return True
        except Exception:
            return False

    async def restart(self) -> None:
        """Stop and restart, with crash counter."""
        self.crash_count += 1
        if self.crash_count > self.max_crashes:
            raise RuntimeError(f"bsl-LS crashed {self.max_crashes} times, giving up")
        await self.stop()
        await asyncio.sleep(2)
        await self.start()

    async def stop(self) -> None:
        """Graceful shutdown."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
```

## Client (WebSocket + JSON-RPC)

`client.py`:

```python
import websockets
import json
from typing import Any

class BslLsClient:
    def __init__(self, port: int = 7777):
        self.port = port
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.request_id = 0

    async def connect(self) -> None:
        self.ws = await websockets.connect(f"ws://localhost:{self.port}")

    async def initialize(self, root_path: str, configuration_root: Optional[str] = None) -> dict:
        """LSP initialize request."""
        return await self._request("initialize", {
            "rootUri": f"file://{root_path}",
            "initializationOptions": {
                "configuration": {"configurationRoot": configuration_root} if configuration_root else {}
            }
        })

    async def analyze_bsl_text(self, bsl_content: str, file_uri: str = "inmemory:///query.bsl") -> list[dict]:
        """Open file with BSL content, get diagnostics."""
        # 1. didOpen
        await self._notify("textDocument/didOpen", {
            "textDocument": {"uri": file_uri, "languageId": "bsl", "version": 1, "text": bsl_content}
        })
        # 2. Request diagnostics (poll или wait for diagnostic notification)
        diagnostics = await self._wait_diagnostics(file_uri, timeout_s=10)
        # 3. didClose
        await self._notify("textDocument/didClose", {"textDocument": {"uri": file_uri}})
        return diagnostics

    async def shutdown(self) -> None:
        if self.ws:
            await self._notify("exit", {})
            await self.ws.close()
```

## Высокоуровневый wrapper

`__init__.py`:

```python
_singleton_client: Optional[BslLsClient] = None
_singleton_lifecycle: Optional[BslLsLifecycle] = None

async def get_bsl_client(java_exe: Path, jar: Path) -> BslLsClient:
    """Lazy-start bsl-LS WebSocket sidecar. Singleton per process."""
    global _singleton_client, _singleton_lifecycle
    if _singleton_client and await _singleton_client.is_alive():
        return _singleton_client
    _singleton_lifecycle = BslLsLifecycle(java_exe, jar)
    await _singleton_lifecycle.start()
    _singleton_client = BslLsClient()
    await _singleton_client.connect()
    await _singleton_client.initialize(root_path=str(Path.cwd()))
    return _singleton_client
```

## Models — Pydantic

`models.py`:

```python
from pydantic import BaseModel
from enum import Enum

class Severity(str, Enum):
    BLOCKER = "Blocker"
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    INFO = "Info"

class Position(BaseModel):
    line: int
    character: int

class Range(BaseModel):
    start: Position
    end: Position

class Diagnostic(BaseModel):
    code: str                   # "RefOveruse"
    code_description_href: str  # "https://1c-syntax.github.io/.../RefOveruse"
    message: str                # "Избавьтесь от .Ссылка"
    range: Range
    severity: Severity
    source: str                 # "bsl-language-server"
    tags: list[str]

class AnalyzeRequest(BaseModel):
    query_sdbl: str             # raw SDBL text
    configuration_root: Optional[str] = None
    enabled_rules: Optional[list[str]] = None  # if None, use defaults

class AnalyzeResult(BaseModel):
    diagnostics: list[Diagnostic]
    parse_success: bool
    analysis_duration_ms: int
```

## Parser — bsl-LS JSON output → our models

`parser.py` парсит JSON output bsl-LS (формат описан в research report §1) в `list[Diagnostic]`. Также:

- **Severity mapping:** LSP severity (1=Error, 2=Warning, 3=Info, 4=Hint) → наши Severity (Blocker, Critical, Major, Minor, Info). Mapping таблица в `parser.py`.
- **Дедупликация (Q6):** реализация группировки overlapping diagnostics → возвращается список с полем `grouped_codes` (list of all codes in this group). Один объект `Diagnostic` per group, severity = max.

## Tests Phase B

`backend\optimyzer\bsl_ls\tests\`:

1. **test_lifecycle.py** — spawn JVM, проверить процесс жив, health check, graceful stop. Mock JVM где возможно для скорости.
2. **test_protocol.py** — JSON-RPC message serialization, request/response correlation, error handling.
3. **test_parser.py** — fixture с реальным JSON output bsl-LS из research report → парсинг → проверка результата.
4. **test_integration.py** — real bsl-LS sidecar (если есть в env), прогон тестовых SDBL запросов, проверка diagnostics.

Coverage target: **> 80%** на новый код.

## Acceptance criteria Phase B

- [ ] `bsl_ls.client.get_bsl_client()` lazy-стартует sidecar
- [ ] WebSocket connection устанавливается, JSON-RPC handshake работает
- [ ] `analyze_bsl_text()` возвращает list of Diagnostic для тестового SDBL
- [ ] Health check возвращает True/False корректно
- [ ] Auto-restart at crash работает (тест: kill процесса, следующий request триггерит restart)
- [ ] Max 3 crashes — потом graceful fail с понятной ошибкой
- [ ] Graceful shutdown через atexit hook
- [ ] Tests pass with coverage > 80%
- [ ] Дедупликация overlapping diagnostics работает (group by range)
- [ ] Severity mapping корректный для всех 19 SDBL правил

**Stop rule Phase B:** Сергей запускает `pytest backend/optimyzer/bsl_ls/tests/ -v` → all green. Демо вызов `analyze_bsl_text("ВЫБРАТЬ * ИЗ Справочник.Контрагенты")` возвращает diagnostics в Python REPL.

**Длительность:** 4-5 дней.

---

# PHASE C — Configuration wiring

## Цель

Юзер подключает свою конфигурацию 1С (XML выгрузка из Конфигуратора) через Settings. bsl-LS получает путь к этой конфигурации и активирует semantic validation против реальных MDO.

## Что уже есть (из Sprint 5)

- UI «Подключить конфигурацию» в Settings → Конфигурация (Sprint 5)
- Backend парсинг XML конфигурации в SQLite cfg-cache
- `ConfigurationBadge` в QueryAnalyzer показывает статус «Подключена / Не подключена»

## Что добавляем в Phase C

### Шаг 1. Хранение пути к Configuration XML

Сейчас Sprint 5 хранит **распарсенные данные** в SQLite. Также нужно хранить **оригинальный путь** к XML каталогу (чтобы передать bsl-LS).

Добавить в `cfg_cache.db` таблицу `connected_configuration`:

```sql
CREATE TABLE IF NOT EXISTS connected_configuration (
    id INTEGER PRIMARY KEY,
    xml_root_path TEXT NOT NULL,       -- e.g. "C:\BUFFER\SCHEME"
    configuration_name TEXT,           -- e.g. "БП 3.0"
    configuration_version TEXT,        -- e.g. "3.0.39.57"
    objects_count INTEGER,
    parsed_at DATETIME,
    last_used_at DATETIME
);
```

При подключении конфигурации (Settings → «Указать папку выгрузки...») — записываем путь + метаданные.

### Шаг 2. Передача configurationRoot в bsl-LS

При `BslLsClient.initialize()` передаём `configurationRoot` из текущего connected configuration:

```python
async def get_bsl_client_for_query() -> BslLsClient:
    client = await get_bsl_client(java_exe, jar)
    config = get_connected_configuration()  # из SQLite
    if config and Path(config.xml_root_path).exists():
        await client.set_workspace_configuration({
            "configurationRoot": config.xml_root_path
        })
    return client
```

Если конфигурация не подключена — bsl-LS работает **без** `configurationRoot`. Это значит:
- Синтаксические правила работают (RefOveruse, JoinWithSubQuery, etc.)
- Semantic правила **не работают** (QueryToMissingMetadata требует MDO)

В UI показываем banner: «Подключите конфигурацию для семантической валидации».

### Шаг 3. Reload на изменение конфигурации

Если юзер переключает на другую конфигурацию (или обновляет существующую) — bsl-LS sidecar нужно **уведомить**:

```python
async def reload_configuration(new_xml_path: str) -> None:
    client = await get_bsl_client()
    await client.send_notification("workspace/didChangeConfiguration", {
        "settings": {"configurationRoot": new_xml_path}
    })
```

### Шаг 4. UI badge в QueryAnalyzer

ConfigurationBadge показывает:

- **Подключена: БП 3.0 (1647 объектов)** — зелёный
- **Не подключена** — желтый, с кнопкой «Подключить»
- **Ошибка чтения XML** — красный, с подсказкой

### Шаг 5. Edge cases

- Юзер удалил папку с XML — graceful degradation: badge становится «Не подключена», bsl-LS работает без configRoot
- Юзер переключил конфигурацию во время activeанализа — кешированные diagnostics инвалидируются
- XML очень большой (ERP 2.5 ~5000 объектов) — async parsing с прогрессом

## Acceptance criteria Phase C

- [ ] Таблица `connected_configuration` в SQLite
- [ ] При подключении конфигурации путь сохраняется
- [ ] `BslLsClient.set_workspace_configuration()` работает
- [ ] Reload конфигурации работает (тест: переключить с БП 3.0 на УТ 11)
- [ ] Без конфигурации bsl-LS работает с ограниченным набором правил
- [ ] `QueryToMissingMetadata` срабатывает на тестовом SDBL с несуществующим MDO когда конфа подключена
- [ ] Edge case: удалённая папка с XML — graceful degradation
- [ ] UI ConfigurationBadge корректно отражает все состояния

**Stop rule Phase C:** Сергей подключает БП 3.0 (`C:\BUFFER\SCHEME`), вставляет тестовый SDBL с заведомо несуществующим объектом, нажимает «Анализировать» — получает `QueryToMissingMetadata` diagnostic.

**Длительность:** 3-4 дня.

---

# PHASE D — Cloud AI orchestration

## Цель

Реализация cloud backend endpoint `/v1/ai/explain` для **structured AI analysis** поверх diagnostics.

В Sprint 6 это **minimal viable** endpoint. Полная инфраструктура (auth, caching, multi-model routing, soft caps) — это Phase 1 INFRA параллельно идущая в другой сессии.

## Структура

В новом проекте `server\` который уже создан для Phase 1:

```
server\
└── api\
    └── v1\
        └── ai\
            ├── __init__.py
            ├── routes.py        ← FastAPI routes
            ├── orchestrator.py  ← AI call logic
            ├── prompts.py       ← system + user prompt templates
            └── models.py        ← Pydantic schemas
```

## Endpoint `/v1/ai/explain`

`routes.py`:

```python
from fastapi import APIRouter
from .models import ExplainRequest, ExplainResponse
from .orchestrator import explain_query

router = APIRouter()

@router.post("/v1/ai/explain", response_model=ExplainResponse)
async def explain(req: ExplainRequest) -> ExplainResponse:
    return await explain_query(req)
```

## Schemas

`models.py`:

```python
from pydantic import BaseModel
from typing import Optional

class DiagnosticInput(BaseModel):
    code: str
    message: str
    severity: str
    range_start_line: int
    range_start_char: int
    range_end_line: int
    range_end_char: int
    snippet: str  # the SDBL substring at this range

class ConfigurationContext(BaseModel):
    mdo_types_used: list[str]
    tabular_sections_used: list[str]
    registers_used: list[str]

class ExplainRequest(BaseModel):
    query_sdbl: str
    diagnostics: list[DiagnosticInput]
    configuration_context: Optional[ConfigurationContext] = None
    related_tj_summary: Optional[str] = None  # not used in Sprint 6

class IssueExplanation(BaseModel):
    title: str
    severity: str
    what: str              # «Что произошло»
    why: str               # «Почему так получилось»
    what_to_do: str        # «Что делать»
    linked_diagnostic_codes: list[str]

class SuggestedRewrite(BaseModel):
    available: bool
    sdbl: Optional[str] = None
    reasoning: Optional[str] = None

class ExplainResponse(BaseModel):
    explanation_summary: str
    issues: list[IssueExplanation]
    suggested_rewrite: SuggestedRewrite
    model_used: str           # "claude-sonnet-4-5-..." for tracking
    duration_ms: int
```

## Orchestrator logic

`orchestrator.py`:

```python
import anthropic
import json
from .models import ExplainRequest, ExplainResponse
from .prompts import SYSTEM_PROMPT_EXPLAIN, USER_PROMPT_TEMPLATE

async def explain_query(req: ExplainRequest) -> ExplainResponse:
    client = anthropic.AsyncAnthropic()  # uses ANTHROPIC_API_KEY env
    user_msg = USER_PROMPT_TEMPLATE.format(
        sdbl=req.query_sdbl,
        diagnostics_json=json.dumps([d.model_dump() for d in req.diagnostics], ensure_ascii=False),
        config_context=req.configuration_context.model_dump() if req.configuration_context else None,
    )
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",  # Sonnet 4.5 — баланс цены и качества
        max_tokens=4000,
        system=SYSTEM_PROMPT_EXPLAIN,
        messages=[{"role": "user", "content": user_msg}],
    )
    # Parse Claude's response as JSON
    response_text = response.content[0].text
    parsed = json.loads(extract_json(response_text))
    return ExplainResponse(**parsed, model_used=response.model, duration_ms=...)
```

## Prompts

`prompts.py`:

```python
SYSTEM_PROMPT_EXPLAIN = """Ты — эксперт по производительности 1С:Предприятие и SDBL запросам. Твоя задача — объяснить разработчику 1С проблемы в его запросе понятным русским языком.

Правила:
1. Отвечай ТОЛЬКО на русском языке.
2. Будь конкретным: ссылайся на конкретные строки кода и значения, а не общими фразами.
3. Не давай советов вроде «оптимизируй запрос» — давай actionable шаги.
4. Группируй связанные проблемы вместе.
5. Если переписывание запроса даст значимый прирост — предложи suggested_rewrite.

Формат ответа: строго valid JSON по схеме:
{
  "explanation_summary": "Краткая суть проблем в одном предложении",
  "issues": [
    {
      "title": "Короткое название проблемы",
      "severity": "Blocker | Critical | Major | Minor | Info",
      "what": "Что именно происходит в коде, с цитатой",
      "why": "Почему это плохо технически (план запроса, оптимизатор, индексы)",
      "what_to_do": "Конкретные шаги исправления с примером",
      "linked_diagnostic_codes": ["RefOveruse", ...]
    }
  ],
  "suggested_rewrite": {
    "available": true | false,
    "sdbl": "переписанный SDBL запрос с пометкой что изменено",
    "reasoning": "что и почему изменено"
  }
}

Если ни одной проблемы — issues = [] и suggested_rewrite.available = false.
"""

USER_PROMPT_TEMPLATE = """Запрос SDBL:
```sql
{sdbl}
```

Диагностики от bsl-language-server:
```json
{diagnostics_json}
```

Контекст конфигурации (используемые объекты):
{config_context}

Объясни проблемы и предложи переписывание если оно даст эффект."""
```

## Что НЕ делается в Sprint 6 (для Phase 1 INFRA)

- Auth (JWT с user_id)
- Caching (один и тот же запрос — один и тот же ответ)
- Multi-model routing (Sonnet/Opus в зависимости от tier)
- Usage tracking (soft caps)
- Rate limiting

Это всё **прийдёт в Phase 1 INFRA** которая идёт параллельно в другой сессии. В Sprint 6 endpoint работает **без auth** на localhost — только для разработки.

## Tests Phase D

- Unit test для prompts (рендеринг шаблонов)
- Unit test для парсинга AI response (включая case когда Claude вернул невалидный JSON)
- Integration test с **real** Claude API (использует Сергея API key, гоняется только локально)

## Acceptance criteria Phase D

- [ ] Endpoint `/v1/ai/explain` работает на localhost
- [ ] Принимает структуру `ExplainRequest`, возвращает `ExplainResponse`
- [ ] Real Claude Sonnet 4.5 вызывается с правильным prompt
- [ ] Output Claude парсится в structured `ExplainResponse`
- [ ] Graceful handling если Claude вернул невалидный JSON (retry с уточнением)
- [ ] Latency < 5 секунд на простой запрос (Claude Sonnet типично 2-3 сек)

**Stop rule Phase D:** Сергей через curl/Postman вызывает endpoint с реальной структурой ExplainRequest (SDBL + diagnostics from Phase B) → получает осмысленный structured explanation на русском с issues и suggested_rewrite.

**Длительность:** 3-4 дня.

---

# PHASE E — UI restoration + extension

## Цель

Восстановить «Анализ запроса» в Sidebar Optimyzer, обновить с новым backend (bsl-LS + AI cloud) и improved UX.

## Что есть в коде (из hidden state)

- `frontend\src\components\screens\QueryAnalyzer.tsx` — основной компонент
- `frontend\src\components\query\FindingsList.tsx` — список findings
- `frontend\src\components\query\RewriteDiff.tsx` — diff между оригиналом и rewrite
- `frontend\src\components\query\ConfigurationBadge.tsx` — статус подключённой конфы
- Все эти компоненты **не удалены**, просто скрыты из Sidebar

## Что меняется

### Шаг 1. Восстановить пункт в Sidebar

`frontend\src\components\chrome\nav.ts`:

```ts
// Раскомментировать (это 1 строка):
{ id: "query-analyzer", label: "Анализ запроса", icon: "Code", group: "analyze", shortcut: "Ctrl+Q" },
```

`frontend\src\App.tsx` — раскомментировать Ctrl+Q shortcut.

### Шаг 2. Обновить backend RPC calls

Frontend сейчас вызывает старый endpoint. Заменить на новый который ходит в bsl-LS sidecar и в cloud AI:

```typescript
// frontend/src/api/queryAnalyzer.ts (новый файл)

export type AnalyzeRequest = {
  query_sdbl: string;
};

export type AnalyzeResponse = {
  diagnostics: Diagnostic[];           // from bsl-LS
  ai_explanation: ExplainResponse;     // from cloud AI
  analysis_duration_ms: number;
};

export async function analyzeQuery(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  // 1. Call local backend → which calls bsl-LS sidecar
  const diagnostics = await invoke("analyze_sdbl", { sdbl: req.query_sdbl });
  
  // 2. Get configuration context (which MDO types are used)
  const configContext = await invoke("extract_config_context", { sdbl: req.query_sdbl });
  
  // 3. Call cloud AI explain
  const aiExplanation = await fetch("https://api.optimyzer.pro/v1/ai/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query_sdbl: req.query_sdbl,
      diagnostics,
      configuration_context: configContext,
    }),
  }).then(r => r.json());
  
  return { diagnostics, ai_explanation: aiExplanation, analysis_duration_ms: ... };
}
```

В Sprint 6 endpoint AI работает на localhost (нет нормального backend). После Phase 1 INFRA — переключение на production.

### Шаг 3. Улучшение UI Findings

**Старый UI:** просто список диагностик с severity badge.

**Новый UI:** structured cards group:

```
┌──────────────────────────────────────────────────────────┐
│ AI Объяснение                                            │
├──────────────────────────────────────────────────────────┤
│ Запрос имеет 3 проблемы производительности и одну        │
│ архитектурную ошибку.                                    │
└──────────────────────────────────────────────────────────┘

┌─ [Critical] Lookup по несуществующему объекту ───────────┐
│ 🚫 Документ.ОбраткнаяРеализация не существует в конфе    │
│                                                          │
│ Что произошло: В строке 7 ссылка на MDO которого нет в  │
│ подключённой конфигурации БП 3.0.                       │
│                                                          │
│ Почему так: Возможно опечатка или вы анализируете       │
│ запрос из другой конфигурации (например, УТ 11).        │
│                                                          │
│ Что делать: Проверьте имя объекта. В БП 3.0 есть        │
│ Документ.ОбратнаяРеализация (без буквы 'к').            │
│                                                          │
│ Диагностики: QueryToMissingMetadata                      │
└──────────────────────────────────────────────────────────┘

┌─ [Major] Лишнее использование .Ссылка ───────────────────┐
│ ↩ Док.Ссылка.Контрагент.Ссылка.Наименование              │
│                                                          │
│ Что произошло: Двойное .Ссылка в цепочке полей.         │
│                                                          │
│ Почему так: Каждое .Ссылка генерирует JOIN в T-SQL...   │
│                                                          │
│ Что делать: Замените на Док.Ссылка.Контрагент.Наименование │
│                                                          │
│ Диагностики: RefOveruse, QueryNestedFieldsByDot          │
└──────────────────────────────────────────────────────────┘

┌─ Предложенное переписывание ─────────────────────────────┐
│ [Принять]  [Отклонить]                                   │
│                                                          │
│ ВЫБРАТЬ                                                  │
│   Док.Дата КАК Дата,                                     │
│ - Док.Ссылка.Контрагент.Ссылка.Наименование КАК Контр, │
│ + Док.Контрагент.Наименование КАК Контрагент,            │
│   Док.СуммаДокумента КАК Сумма                          │
│ ИЗ ...                                                   │
│                                                          │
│ Изменения: Убраны лишние .Ссылка для производительности  │
└──────────────────────────────────────────────────────────┘
```

### Шаг 4. CodeMirror highlighting

Используя existing CodeMirror integration — подсвечивать в editor строки с findings:

- Blocker/Critical — красный underline
- Major — янтарный underline
- Minor/Info — серый underline

При hover на underline — tooltip с message диагностики.

### Шаг 5. ConfigurationBadge update

Использует данные из `connected_configuration` SQLite (Phase C). Click на badge → открывается Settings → Конфигурация.

### Шаг 6. Empty states + loading states

- Изначально пусто → placeholder «Вставьте SDBL запрос для анализа»
- Анализирую → spinner + «Анализ запроса (3 сек, AI работает...)»
- Нет findings → положительный banner «Запрос выглядит хорошо! Не найдено проблем»
- Ошибка → понятный текст с кнопкой «Попробовать ещё раз»

## Acceptance criteria Phase E

- [ ] «Анализ запроса» появился в Sidebar (группа АНАЛИЗ)
- [ ] Ctrl+Q открывает экран
- [ ] Editor принимает SDBL, кнопка «Анализировать» работает
- [ ] Findings показываются в виде structured cards
- [ ] AI explanation summary сверху
- [ ] Suggested rewrite показывается если available
- [ ] CodeMirror подсвечивает строки с findings
- [ ] ConfigurationBadge показывает корректный статус
- [ ] Empty/loading/error states работают
- [ ] Дедупликация overlapping findings работает в UI

**Stop rule Phase E:** Сергей делает end-to-end demo: подключает БП 3.0, вставляет проблемный SDBL запрос, нажимает «Анализировать», получает findings + AI explanation + suggested rewrite за < 10 секунд.

**Длительность:** 5-7 дней.

---

# PHASE F — sqlglot integration

## Цель

Использовать sqlglot для **двух мест**:

1. **TopSQL screen** (Slow Queries — existing) — улучшить detection антипаттернов в T-SQL из DBMSSQL событий ТЖ
2. **QueryAnalyzer T-SQL view** — если есть связанный T-SQL exemplar из ТЖ, показать его с подсветкой + antipatterns

## Шаг 1. Install dependency

`backend\requirements.txt`:

```
sqlglot>=30.8.0,<31.0.0
```

## Шаг 2. T-SQL antipattern detector

`backend\optimyzer\sql\antipatterns.py`:

```python
import sqlglot
from sqlglot import exp

class TSqlAntipattern(BaseModel):
    name: str
    description: str
    severity: Severity
    location_in_ast: Optional[str]

def detect_antipatterns(tsql: str) -> list[TSqlAntipattern]:
    try:
        ast = sqlglot.parse_one(tsql, dialect="tsql")
    except sqlglot.errors.ParseError as e:
        return [TSqlAntipattern(name="ParseError", description=str(e), severity=Severity.MAJOR, location_in_ast=None)]
    
    patterns = []
    
    # NOT IN antipattern
    for not_op in ast.find_all(exp.Not):
        if isinstance(not_op.this, exp.In):
            patterns.append(TSqlAntipattern(
                name="NotInWithPossiblyNullable",
                description="NOT IN с подзапросом — медленно + могут быть нули в результате",
                severity=Severity.MAJOR,
            ))
    
    # LEFT JOIN with WHERE on right table (effectively INNER JOIN)
    # ... full implementation ...
    
    # OR в WHERE — оптимизатор плохо работает
    # ...
    
    # Function-wrapped predicates (non-SARGable)
    # ...
    
    # LIKE с leading wildcard
    # ...
    
    return patterns
```

Минимум 8-10 паттернов в Sprint 6. Расширим в follow-up sprints.

## Шаг 3. Использование в TopSQL screen

Сейчас `TopSQL` показывает агрегированные slow queries из ТЖ. Расширить колонкой «Антипаттерны» которая показывает count и при click — drill-down в детали.

`frontend\src\components\screens\TopSQL.tsx` — добавить колонку и tooltip.

## Шаг 4. T-SQL view в QueryAnalyzer

В QueryAnalyzer добавить tab «T-SQL» (если есть связанный T-SQL из ТЖ):

- Показать T-SQL текст с подсветкой sqlglot
- Показать antipatterns обнаруженные sqlglot
- (В Sprint 8 — план выполнения если есть `.sqlplan`)

## Acceptance criteria Phase F

- [ ] sqlglot установлен и работает в backend
- [ ] `detect_antipatterns(tsql)` возвращает list of patterns для тестовых T-SQL
- [ ] Минимум 8 antipatterns implemented
- [ ] TopSQL screen показывает колонку «Антипаттерны»
- [ ] QueryAnalyzer T-SQL view работает (если есть exemplar)
- [ ] Tests > 30 для antipatterns module

**Stop rule Phase F:** прогнать на 100 реальных T-SQL запросах из тестового архива Сергея. Проверить что antipatterns детектятся корректно (manual spot check 10-15).

**Длительность:** 3-4 дня.

---

# PHASE G — Tests + edge cases + performance

## Цель

Стабилизация Sprint 6, регрессионное тестирование, проверка edge cases.

## Test categories

### Регрессия

- Все existing backend tests (487 passed baseline Sprint 5) проходят
- Все existing frontend tests проходят
- Никаких поломанных функций

### Phase A-F tests

- Phase A: installer test (manual on clean VM)
- Phase B: bsl_ls unit tests > 80% coverage
- Phase C: configuration wiring tests
- Phase D: AI orchestration tests
- Phase E: UI E2E tests (Playwright)
- Phase F: antipatterns tests

### Edge cases

- **Большой архив ТЖ** + QueryAnalyzer open simultaneously — память не вылетает
- **Сломанная XML конфигурация** (битый файл) — graceful error
- **bsl-LS JVM crash** — auto-restart срабатывает
- **Cloud AI недоступен** — show error in UI с retry button
- **SDBL запрос > 10000 строк** — performance acceptable (< 30 сек)
- **Конфигурация очень большая** (ERP 2.5 ~5000 объектов) — bsl-LS работает (может медленно)
- **Кириллические имена объектов** — корректная обработка во всех слоях
- **Очень узкое окно** (mobile-size) — UI deg gracefully

### Performance benchmarks

Targets для production:
- bsl-LS sidecar cold start: < 30 сек (acceptable если lazy)
- Single SDBL analyze request: < 1 сек после warmup
- AI explanation request: < 5 сек (Claude Sonnet)
- Полный analyze cycle (UI click → result on screen): < 10 сек

Если что-то медленнее — investigate и улучшить.

## Acceptance criteria Phase G

- [ ] Все tests passing: backend > 530 (baseline 487 + 50 new)
- [ ] Frontend tests passing
- [ ] All 8 edge cases tested
- [ ] Performance targets met
- [ ] Memory leak check (long-running session — no leak)

**Stop rule Phase G:** Сергей делает 30-минутную интенсивную session с QueryAnalyzer — все работает стабильно, нет crashes, нет UI freezes.

**Длительность:** 3-5 дней.

---

# PHASE H — Documentation + Closure

## Цель

Закрытие Sprint 6 со всей документацией для архитектора и следующих спринтов.

## Documents to create/update

### 1. `docs/SPRINT_6_REPORT.md`

Closure report по аналогии со Sprint 5 reports. Структура:
- Что сделано
- Acceptance criteria status (32+ из 35)
- Технические решения
- Tech debt / known issues
- Performance metrics
- Testing instructions

### 2. `docs/OPUS_HANDOVER_SPRINT_6.md`

Handover для архитектора:
- Что готово, что в production-ready состоянии
- Что зафиксировано как tech debt для следующих спринтов
- Какие feature flags / configs нужно знать архитектору
- Открытые вопросы для решения архитектором

### 3. Обновить `docs/CCH_FEATURE_PARITY_REFERENCE.md`

Раздел про QueryAnalyzer — теперь у нас **production-grade** semantic validation. Покрытие методики 1С:Эксперт в этой области ~85%.

### 4. Обновить `docs/DECISIONS.md`

ADR-033 — выбор bsl-language-server как основы Query Analyzer.
ADR-034 — WebSocket sidecar architecture vs CLI per-request.
ADR-035 — Cloud AI orchestration через API endpoint.
ADR-036 — Bundled JRE 21 vs jlink vs GraalVM.

### 5. Удалить `docs/QUERY_ANALYZER_HIDDEN_2026_05.md`

Файл выполнил свою роль — QueryAnalyzer восстановлен. Move to `docs/archive/`.

### 6. README update

Optimyzer README — обновить feature list, добавить screenshot нового QueryAnalyzer.

## Final tag

```bash
git tag -a v0.6.0-internal -m "Sprint 6: Query Analyzer Restoration with bsl-language-server integration"
git push origin v0.6.0-internal
```

## Acceptance criteria Phase H

- [ ] All 6 documents created/updated
- [ ] Tag `v0.6.0-internal` создан и pushed
- [ ] Merge feat/sprint-6 → main fast-forward

**Длительность:** 1-2 дня.

---

# Технические инструкции для исполнителя

## Структура коммитов

Branch: `feat/sprint-6-query-analyzer`

Коммиты атомарные по логике, **не** по Phase. Примерные:

- `feat(deploy): bundle JRE 21 + bsl-language-server v0.29.0`
- `feat(server): bsl-LS WebSocket sidecar lifecycle management`
- `feat(server): bsl-LS protocol + JSON-RPC client`
- `feat(server): pydantic models for bsl-LS diagnostics`
- `feat(server): unit tests for bsl-LS adapter`
- `feat(config): wiring connected configuration with bsl-LS`
- `feat(cloud): /v1/ai/explain endpoint with Sonnet 4.5`
- `feat(cloud): system + user prompts for query explanation`
- `feat(ui): restore QueryAnalyzer in Sidebar`
- `feat(ui): structured findings cards with AI explanation`
- `feat(ui): CodeMirror highlighting of diagnostics`
- `feat(sql): sqlglot antipatterns detector`
- `feat(ui): T-SQL view in QueryAnalyzer`
- `test(*): integration tests for full analyze flow`
- `docs: SPRINT_6_REPORT + OPUS_HANDOVER + ADRs`

После merge в main — tag.

## Что НЕ делать в Sprint 6

- НЕ интегрировать PerformanceStudio (Sprint 8)
- НЕ интегрировать html-query-plan (Sprint 8)
- НЕ восстанавливать **наши** старые regex-based semantic rules — bsl-LS теперь главный источник правды
- НЕ форкать bsl-LS
- НЕ реализовывать auth/billing/caching/multi-model — это Phase 1 INFRA параллельно
- НЕ добавлять новые SDBL правила сверх 19 от bsl-LS (custom rules — Sprint 7+)
- НЕ менять existing ТЖ парсер / Operations / Anatomy views (вне scope)

## Stop rules — обязательны

Каждая Phase имеет stop rule. Без подтверждения Сергея — не двигаться в следующую Phase.

После завершения **каждой Phase** — отдельное сообщение Сергею с:
1. Что сделано
2. Acceptance criteria (галочки)
3. Демонстрация stop rule
4. Готов ли двигаться дальше

## Если что-то блокирует

Если технически невозможно сделать что-то — **остановиться и спросить архитектора**, не пытаться обойти.

Особенно если:
- bsl-LS неожиданно крашится на реальных конфигурациях 1С
- WebSocket mode имеет lag в performance
- Cloud AI возвращает невалидный JSON в > 10% случаев
- JRE bundling не работает на macOS / Linux (если Сергей планирует cross-platform)

---

# Итоговый Definition of Done для Sprint 6

Перед закрытием спринта проверить:

- [ ] Installer Optimyzer работает на чистой Windows 11 VM
- [ ] bsl-LS sidecar lazy-стартует при первом обращении к QueryAnalyzer
- [ ] WebSocket connection устанавливается, диагностики возвращаются
- [ ] Все 19 SDBL правил активны (configured by default rules)
- [ ] Configuration wiring работает: подключённая БП 3.0 даёт semantic validation
- [ ] Cloud AI endpoint `/v1/ai/explain` работает на localhost
- [ ] AI возвращает structured JSON, парсится корректно
- [ ] UI «Анализ запроса» восстановлен в Sidebar (Ctrl+Q)
- [ ] Findings группируются в structured cards
- [ ] CodeMirror highlighting работает
- [ ] sqlglot detect антипаттернов в TopSQL и QueryAnalyzer T-SQL view
- [ ] Backend tests > 530, frontend tests > 100, coverage > 80% new code
- [ ] Все 8 edge cases tested
- [ ] Documentation: SPRINT_6_REPORT, OPUS_HANDOVER, 4 ADRs
- [ ] Tag v0.6.0-internal, merged to main
- [ ] Сергей делает 30-минутную demo session — всё работает стабильно

---

# Roadmap context (для понимания того что дальше)

После Sprint 6 — **Sprint 7: AI Query Rewriter v2 + Multi-model routing**. Расширение AI capabilities:
- Opus 4.5 для Business tier (более сложные rewrites)
- Multi-pass reasoning для complex cases
- Caching и semantic deduplication

После Sprint 7 — **Sprint 8: Execution Plan Analyzer** (PerformanceStudio + html-query-plan).

После Sprint 8 — **Sprint 9: APDEX + Regression Tracking** (premium features оправдывающие 9 900 ₽).

После Sprint 9 — **Sprint 10: Deadlock Reconstruction + Team Workspace**.

После всех product sprints — закрытие Phase 1 INFRA (Yandex OAuth + YooKassa + soft caps + telemetry) → Phase 2 MARKETING → launch.

---

**Подготовил:** Claude Opus 4.7 (Architect)
**Для:** Claude Code (executor)
**Дата:** 2026-05-24
**Версия:** Sprint 6 promt v1 (после opensource research)
**Базовая работа:** OPENSOURCE_RESEARCH_REPORT.md
**Длительность:** 5-7 недель
**Tag goal:** v0.6.0-internal
**Следующий sprint:** Sprint 7 (AI Rewriter v2)
