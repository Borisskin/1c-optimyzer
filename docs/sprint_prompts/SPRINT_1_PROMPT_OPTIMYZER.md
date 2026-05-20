# Sprint 1 — Folder Ingestion (real-world calibrated) + ru-RU + OQL Engine + Editor

> **Контекст:** Sprint 0 закрыт + smoke test passed (окно открывается, UI 1:1 с дизайном). Discovery-инспекция реальной папки логов (11.94 GiB, 28 .log файлов, 6 типов процессов) выполнена — см. `docs/LOGS_INSPECTION.md`. Все архитектурные предположения откалиброваны на **реальных данных**, не на гипотезах.
>
> **Working directory:** `D:\1C-Optimyzer\1c-optimyzer\`
> **Branch:** `feat/sprint-1-ingest-and-oql` (от `feat/sprint-0-foundation`)

---

## 1. Контекст: что мы знаем после Sprint 0 + discovery

### Реальный формат данных (из LOGS_INSPECTION.md)

**Структура папок:** 17 подпапок, 6 типов префиксов процессов:
- `1cv8c_NNNN` (7 шт) — толстый клиент
- `1cv8s_NNNN` (4 шт) — server connection / session
- `1cv8_NNNN` (3 шт)
- `ragent_NNNN` (1 шт) — cluster agent
- `rmngr_NNNN` (1 шт) — cluster manager
- `rphost_NNNN` (1 шт) — worker process

**КРИТИЧНО:** регистр префиксов смешанный (`1CV8C_12044` и `1cv8c_23100` соседствуют). Все regex — **case-insensitive**.

**Имена файлов:** 100% соответствуют `^\d{8}\.log$` (YYMMDDHH.log). Год берётся из имени файла, минуты+секунды+микросекунды из event prefix.

**Распределение размеров (highly skewed):**
- min: 71 B
- median: 1.07 MiB
- max: 10.23 GiB (один rphost файл = 87% всего объёма)
- total: 11.94 GiB

**Encoding:** UTF-8 with BOM (utf-8-sig). Cp1251/cp866 — fallback для других инсталляций.

**Event format:**
```
47:02.139004-1,CALL,1,level=INFO,process=rmngr,OSThread=23464,t:clientID=1434,...
09:33.371005-1,HASP,3,level=INFO,process=1CV8C,OSThread=18076,Txt='
LOCALHASP_HASPSTATUS(,,ser=ORGL8,,,,)->size=4,type=10,port=102,ApiVer=25684'
```

Multi-line events существуют (HASP event имеет продолжение на следующей строке без prefix).

### Принятые архитектурные решения (на основе discovery)

1. **Zip убирается из UI** полностью. RPC `load_archive` остаётся как deprecated entry point для тестовых fixtures (не выбрасываем рабочий код Sprint 0).
2. **FolderSource — единственный primary способ** загрузки в UI Module 1.
3. **`process_role` — first-class column** в events table. Извлекается из имени родительской папки через regex `^(1cv8c|1cv8s|1cv8|ragent|rmngr|rphost)_(\d+)$` (re.IGNORECASE).
4. **Byte-weighted progress** обязателен. File-count progress на 28-файловом dataset с 87% объёма в одном файле даст ложное «27/28 = 96% done».
5. **DuckDB Appender API** обязателен. `executemany` не справится с 10 ГБ файлом.
6. **Streaming обязателен.** Buffered line iteration через `Path.open('rb', buffering=1024*1024)`.

### Решения по Q6-Q9 (приняты архитектором)

- **Q6 (locale):** A — hardcoded ru-RU в `frontend/src/i18n/ru.ts`, signature совместима с future i18n framework.
- **Q7 (real-data fixture):** A — локальный путь в `.env.test`, pytest auto-skip если недоступен. Плюс synthetic generator для unit tests.
- **Q8 (progress UX):** B+C combined — StatusBar inline progress + slide-in notification card. Без modal blocker, UI остаётся interactive.
- **Q9 (multi-archive sessions):** Sprint 1 — simplified replace (новая загрузка заменяет активный archive_id). Sprint 2 — full multi-session dropdown.

---

## 2. Новые ADR (фиксируются в Sprint 1)

### ADR-009: UI Language Policy

UI strings — на русском, hardcoded в `frontend/src/i18n/ru.ts`. Дизайн-файлы `design/opt/*.jsx` остаются английскими как visual reference. Backend RPC error messages — на русском.

### ADR-010: Folder as Primary (and Only) Ingestion Source in UI

Module 1 UI поддерживает только folder ingestion. ZIP остаётся как RPC entry point для backwards compatibility с тестами Sprint 0, но в UI недоступен. В будущем (Module 2+) может быть возвращён через Settings, если пользовательский запрос.

### ADR-011: DuckDB Appender API for Bulk Insert

Bulk insert через DuckDB Python Appender. Buffered append, indexes создаются ПОСЛЕ полного insertion.

### ADR-012: Streaming Parser with Byte-Weighted Progress

Парсер работает построчно через buffered file iteration. Progress reported в **байтах** (не файлах), throttled до 4 emit/sec. JSON-RPC notifications без id (fire-and-forget).

### ADR-013: Tauri 2 Native Drag-Drop API

Использовать `tauri://drag-drop` event, не DOM events. В `tauri.conf.json` установить `dragDropEnabled: true`.

### ADR-014: process_role as First-Class Column

В events table добавляется столбец `process_role` (VARCHAR), извлекается из имени родительской папки лог-файла. Допустимые значения: `'rphost' | 'rmngr' | 'ragent' | '1cv8c' | '1cv8s' | '1cv8' | 'unknown'`.

---

## 3. Структура изменений

### Backend

```
backend/src/optimyzer_backend/
├── ingest/                                  ПЕРЕИМЕНОВАНО из archive/
│   ├── __init__.py
│   ├── source.py                            абстрактный LogSource (NEW)
│   ├── folder_source.py                     primary FolderSource (NEW)
│   ├── zip_source.py                        переехал из archive/extractor.py (RENAMED)
│   ├── log_detector.py                      double-check имя+первая строка (NEW)
│   ├── encoding_detector.py                 UTF-8 → cp1251 → cp866 fallback (NEW)
│   ├── progress_reporter.py                 byte-weighted JSON-RPC notifications (NEW)
│   └── process_role_extractor.py            regex по имени папки (NEW)
├── oql/                                     ВСЕ NEW
│   ├── __init__.py
│   ├── grammar.lark
│   ├── parser.py
│   ├── ast.py
│   ├── compiler.py
│   ├── validator.py
│   ├── functions.py
│   └── templates.py
├── parsers/
│   └── tj_parser.py                         UPDATE: process_role, byte progress, BOM handling
├── storage/
│   ├── duckdb_store.py                      UPDATE: Appender API, schema +process_role
│   └── sqlite_store.py                      UPDATE: saved_queries table
├── rpc/
│   ├── archive_rpc.py                       UPDATE: +load_directory, deprecate load_archive
│   ├── oql_rpc.py                           NEW
│   └── ...
└── tests/
    ├── fixtures/
    │   └── synthetic/
    │       ├── __init__.py
    │       └── generate_tj_logs.py          synthetic generator (NEW)
    ├── test_folder_source.py                NEW
    ├── test_log_detector.py                 NEW
    ├── test_encoding_detector.py            NEW
    ├── test_process_role_extractor.py       NEW
    ├── test_progress_reporter.py            NEW
    ├── test_duckdb_appender.py              NEW
    ├── test_oql_parser.py                   NEW (~30 tests)
    ├── test_oql_compiler.py                 NEW (~20 tests)
    ├── test_oql_e2e.py                      NEW (~15 tests)
    └── test_sprint1_real_folder.py          acceptance gate (NEW)

.env.test.example                            template для real-data path (NEW)
```

### Frontend

```
frontend/src/
├── i18n/
│   └── ru.ts                                NEW: все UI strings
├── codemirror/                              NEW (CodeMirror 6 integration)
│   ├── oql-language.ts                      StreamLanguage
│   ├── oql-autocomplete.ts
│   ├── oql-linter.ts
│   └── oql-theme.ts
├── components/
│   ├── chrome/
│   │   ├── TopBar.tsx                       UPDATE: ru-RU + "Загрузить папку" (no dropdown)
│   │   ├── Sidebar.tsx                      UPDATE: ru-RU labels
│   │   ├── StatusBar.tsx                    UPDATE: ru-RU + inline progress
│   │   └── CommandPalette.tsx               UPDATE: ru-RU + commands
│   ├── overlays/
│   │   ├── DropZone.tsx                     FIX: Tauri 2 native API, only folders
│   │   └── ProgressCard.tsx                 NEW: slide-in notification
│   └── screens/
│       └── OQLConsole/
│           ├── OQLConsole.tsx               UPDATE: ru-RU + integrate Editor
│           ├── Editor.tsx                   NEW: CodeMirror wrapper
│           ├── ResultsPanel.tsx             UPDATE: real results from RPC
│           ├── TemplatesBar.tsx             NEW
│           ├── SavedQueriesMenu.tsx         NEW
│           └── DocsPanel.tsx                NEW (slide-in справа)
├── api/
│   └── backend.ts                           UPDATE: +load_directory, +execute_oql, progress events
└── store/
    └── appStore.ts                          UPDATE: progress state, OQL state
```

---

## 4. Phases

### Phase A — ru-RU локализация

**A1.** `frontend/src/i18n/ru.ts` — все UI strings как hierarchical const tree. Структура:

```ts
export const t = {
  app: { name: '1C-Optimyzer', edition: 'standalone' },
  topbar: {
    loadFolder: 'Загрузить папку с логами',
    recentSources: 'Недавние',
    searchPlaceholder: 'Поиск...',
    healthIdle: 'Готово',
    healthParsing: 'Обработка...',
    aiPro: 'AI Pro',
    aiTooltip: 'Доступно в платной подписке',
  },
  sidebar: {
    groups: { live: 'НАБЛЮДЕНИЕ', analyze: 'АНАЛИЗ', config: 'КОНФИГУРАЦИЯ', manage: 'УПРАВЛЕНИЕ' },
    items: {
      oql: 'OptimyzerQL',
      dashboard: 'Мониторинг',
      apdex: 'Apdex и SLA',
      workbench: 'Расследование',
      queries: 'Медленные запросы',
      locks: 'Блокировки',
      cluster: 'Здоровье кластера',
      indexes: 'Индексы и статистика',
      profiler: 'BSL-профайлер',
      health: 'Аудит конфигурации',
      compare: 'Сравнение',
      predictive: 'Прогнозы',
      resolution: 'Резолюции',
      multibase: 'Несколько баз',
      knowledge: 'База знаний',
      alerts: 'Алерты',
      reports: 'Отчёты',
      mobile: 'Мобильное',
    },
    tooltipModule: 'Доступно в модуле',
  },
  statusbar: {
    idle: 'готово',
    noArchive: 'логи не загружены',
    parsing: 'парсинг',
    indexing: 'построение индексов',
    duckdb: 'DuckDB',
    events: 'событий',
    activeArchive: 'активный архив',
    parsedIn: 'обработано за',
    devBuild: 'dev',
  },
  oql: {
    pageTitle: 'OptimyzerQL Console',
    breadcrumb: 'Управление',
    badgeFreeTier: 'free tier',
    sprintLabel: 'Sprint 1 · DSL parser',
    description: 'Декларативный язык запросов поверх технологического журнала',
    editor: {
      filenameDefault: 'untitled.oql',
      modified: 'не сохранено',
      saved: 'сохранено',
      cursor: 'стр',
      column: 'кол',
      rows: 'строк',
    },
    results: {
      tabs: { table: 'Таблица', chart: 'График', timeline: 'Хронология', raw: 'Сырой JSON' },
      empty: {
        noArchive: 'Загрузите логи ТЖ, чтобы начать запросы',
        hint: 'Перетащите папку с логами в окно или нажмите кнопку ниже',
        loadButton: 'Загрузить папку с логами',
      },
      placeholder: 'Напишите OQL-запрос или выберите шаблон ниже',
      rowsCounter: 'строк',
      executedIn: 'выполнено за',
      scannedEvents: 'просканировано событий',
      export: 'Экспорт CSV',
    },
    actions: {
      run: 'Выполнить',
      runShortcut: 'Ctrl+Enter',
      templates: 'Шаблоны',
      docs: 'Документация',
      share: 'Поделиться',
      save: 'Сохранить',
      saveAs: 'Сохранить как…',
    },
    presets: {
      label: 'ШАБЛОНЫ',
      // см. Phase H — templates.py для полного списка
    },
    saved: {
      label: 'СОХРАНЁННЫЕ',
      empty: 'Нет сохранённых запросов',
      newQuery: 'Новый запрос',
    },
    docsPanel: {
      title: 'Документация OptimyzerQL',
      sources: 'Источники данных',
      operators: 'Операторы',
      functions: 'Функции',
      examples: 'Примеры',
    },
  },
  progress: {
    discovering: 'Поиск логов в папке...',
    parsing: 'Парсинг логов',
    indexing: 'Построение индексов',
    of: 'из',
    files: 'файлов',
    currentFile: 'текущий файл',
    eventsInserted: 'событий загружено',
    minimize: 'Свернуть',
    cancel: 'Отменить',
    done: 'Готово',
    completedToast: 'Загружено {events} событий за {time}',
    cancelled: 'Загрузка отменена',
    errorToast: 'Ошибка загрузки: {message}',
  },
  cmdpalette: {
    placeholder: 'Команды...',
    groups: { navigation: 'НАВИГАЦИЯ', file: 'ФАЙЛ', recent: 'НЕДАВНИЕ', help: 'СПРАВКА' },
    commands: {
      loadFolder: 'Загрузить папку с логами',
      newQuery: 'Новый OQL-запрос',
      runQuery: 'Выполнить запрос',
      about: 'О программе',
      quit: 'Выйти',
      openSettings: 'Настройки',
    },
    noResults: 'Ничего не найдено',
  },
  toast: { success: 'Успешно', error: 'Ошибка', warning: 'Предупреждение', info: 'Информация' },
  errors: {
    folderNotFound: 'Папка не найдена',
    notADirectory: 'Это не папка',
    noLogsFound: 'Лог-файлы не найдены в указанной папке',
    invalidDropTarget: 'Перетащите папку с логами, не файл',
    parseError: 'Ошибка парсинга: {detail}',
    oqlSyntaxError: 'Синтаксическая ошибка: {detail}',
    oqlValidationError: 'Ошибка валидации: {detail}',
    networkError: 'Ошибка соединения с backend',
  },
};
```

**A2.** Замены в существующих компонентах — все hardcoded английские строки на `t.section.key`. Только text content меняется, DOM structure и styling сохраняются.

**A3.** В `design/README.md` добавить заметку (создать файл если нет):
```markdown
# Design Reference
Файлы в `opt/*.jsx` — визуальная спецификация на английском.
Production UI translates strings to ru-RU via `frontend/src/i18n/ru.ts`.
См. ADR-009.
```

### Phase B — Folder Ingestion

#### B1. Source abstraction

`backend/src/optimyzer_backend/ingest/source.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

ProcessRole = Literal['rphost', 'rmngr', 'ragent', '1cv8c', '1cv8s', '1cv8', 'unknown']
IngestPhase = Literal['discovering', 'parsing', 'indexing', 'done', 'error']

@dataclass
class LogFile:
    path: Path
    relative_path: str          # для display в progress
    size_bytes: int
    timestamp_from_name: str    # YYMMDDHH из имени, гарантировано не None
    process_role: ProcessRole   # из имени родительской папки
    process_pid: int | None     # из имени родительской папки (NNNN часть)

@dataclass
class IngestProgress:
    phase: IngestPhase
    files_done: int
    files_total: int
    bytes_done: int             # ОСНОВНОЙ счётчик для % progress
    bytes_total: int
    events_inserted: int
    current_file: str | None
    error_message: str | None = None

class LogSource(ABC):
    @abstractmethod
    def discover(self) -> list[LogFile]: ...
    
    @abstractmethod
    def open(self, log_file: LogFile, encoding: str) -> Iterator[str]: ...
```

#### B2. FolderSource

`backend/src/optimyzer_backend/ingest/folder_source.py`:

```python
import re
from pathlib import Path
from typing import Iterator
from .source import LogSource, LogFile
from .log_detector import is_tj_log_file
from .process_role_extractor import extract_process_role

LOG_NAME_RE = re.compile(r'^(\d{8})\.log$', re.IGNORECASE)

class FolderSource(LogSource):
    def __init__(self, root: Path):
        root = root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Папка не найдена: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Не папка: {root}")
        self.root = root
    
    def discover(self) -> list[LogFile]:
        results = []
        skipped_by_name = 0
        skipped_by_content = 0
        
        for entry in self.root.rglob('*'):
            if not entry.is_file():
                continue
            
            name_match = LOG_NAME_RE.match(entry.name)
            if not name_match:
                skipped_by_name += 1
                continue
            
            timestamp = name_match.group(1)
            
            # Content double-check — safety net на случай нестандартных файлов
            try:
                if not is_tj_log_file(entry):
                    skipped_by_content += 1
                    continue
            except OSError:
                skipped_by_content += 1
                continue
            
            try:
                size = entry.stat().st_size
            except OSError:
                continue
            
            # Extract process role и pid из имени родительской папки
            parent_name = entry.parent.name
            role, pid = extract_process_role(parent_name)
            
            results.append(LogFile(
                path=entry,
                relative_path=str(entry.relative_to(self.root)),
                size_bytes=size,
                timestamp_from_name=timestamp,
                process_role=role,
                process_pid=pid,
            ))
        
        # Сортировка: сначала маленькие файлы, потом большие — даёт fast feedback пользователю.
        # На discovery time это secondary, но для UX progress это важно: видишь как растёт count
        # на маленьких файлах, потом приходит большой rphost.
        results.sort(key=lambda lf: (lf.size_bytes, lf.relative_path))
        return results
    
    def open(self, log_file: LogFile, encoding: str = 'utf-8-sig') -> Iterator[str]:
        """Buffered streaming line iteration. encoding с BOM handling."""
        with log_file.path.open('r', encoding=encoding, errors='replace', buffering=1024*1024) as f:
            for line in f:
                yield line
```

#### B3. Log file content detector

`backend/src/optimyzer_backend/ingest/log_detector.py`:

```python
import re
from pathlib import Path

TJ_EVENT_PREFIX_RE = re.compile(rb'^\d{2}:\d{2}\.\d{6}-')

def is_tj_log_file(path: Path, max_check_bytes: int = 4096) -> bool:
    """True если первая непустая строка matches TJ event prefix."""
    try:
        with path.open('rb') as f:
            chunk = f.read(max_check_bytes)
    except OSError:
        return False
    
    if chunk.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
        chunk = chunk[3:]
    
    for line in chunk.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return bool(TJ_EVENT_PREFIX_RE.match(stripped))
    
    return False
```

#### B4. Process role extractor

`backend/src/optimyzer_backend/ingest/process_role_extractor.py`:

```python
import re

# Case-insensitive по результатам discovery (1CV8C_NNNN рядом с 1cv8c_NNNN в одной папке)
PROCESS_ROLE_RE = re.compile(
    r'^(1cv8c|1cv8s|1cv8|ragent|rmngr|rphost)_(\d+)$',
    re.IGNORECASE
)

def extract_process_role(folder_name: str) -> tuple[str, int | None]:
    """Возвращает (role_lowercase, pid) или ('unknown', None)."""
    match = PROCESS_ROLE_RE.match(folder_name)
    if not match:
        return ('unknown', None)
    return (match.group(1).lower(), int(match.group(2)))
```

#### B5. Encoding detector

`backend/src/optimyzer_backend/ingest/encoding_detector.py`:

```python
from pathlib import Path

# Порядок важен: utf-8-sig первый (наш случай из discovery), 
# затем plain utf-8 (без BOM), затем legacy кодировки.
ENCODINGS_TO_TRY = ['utf-8-sig', 'utf-8', 'cp1251', 'cp866']

def detect_encoding(path: Path, sample_size: int = 65536) -> str:
    """Try each encoding, return first that decodes без ошибок.
    Fallback на 'utf-8' с errors='replace' если все провалились.
    """
    try:
        with path.open('rb') as f:
            sample = f.read(sample_size)
    except OSError:
        return 'utf-8'
    
    for enc in ENCODINGS_TO_TRY:
        try:
            sample.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    
    return 'utf-8'  # fallback с errors='replace' в FolderSource.open()
```

#### B6. ZipSource — adapter, не выбрасываем

`backend/src/optimyzer_backend/ingest/zip_source.py`:

```python
# Переехало из archive/extractor.py с минимальным adapter к LogSource interface
# Используется ТОЛЬКО в тестовых fixtures, не в UI
# Suffix _deprecated не ставим — функция остаётся, просто не в primary path
```

#### B7. Тесты ingestion

`backend/tests/test_folder_source.py` — минимум 10 тестов:
- `test_folder_discovers_flat_logs` — папка без подпапок
- `test_folder_discovers_standard_structure` — `rphost_3460/26051815.log`
- `test_folder_discovers_mixed_case_prefixes` — `1CV8C_12044` и `1cv8c_23100` в одной папке
- `test_folder_discovers_all_six_role_types` — все 6 типов process
- `test_folder_filters_non_log_files` — `.txt`, `.md`, `.lck` исключены
- `test_folder_filters_bad_content_log` — файл с правильным именем `12345678.log` но содержимым `Hello world`
- `test_folder_handles_permission_denied` — graceful skip без exception
- `test_folder_handles_broken_symlink` — graceful skip
- `test_folder_sort_order` — sorted by size ascending
- `test_folder_process_role_extracted` — role + pid в LogFile

`backend/tests/test_log_detector.py` — минимум 6 тестов:
- `test_accepts_valid_tj_event` — пример из discovery
- `test_rejects_random_text` — `Hello world\nLine 2`
- `test_rejects_empty_file`
- `test_handles_utf8_bom` — файл с BOM в начале
- `test_handles_only_whitespace_then_event` — пустые строки в начале
- `test_handles_io_error` — non-existent path

`backend/tests/test_process_role_extractor.py` — минимум 8 тестов:
- `test_extracts_lowercase_rphost`
- `test_extracts_uppercase_RPHOST`
- `test_extracts_mixed_case_1CV8C`
- `test_extracts_all_six_roles` — параметризованный
- `test_returns_unknown_for_arbitrary_folder` — `logs`, `temp`, `backup`
- `test_returns_unknown_for_partial_match` — `rphost_abc` (pid не число)
- `test_extracts_pid` — большие числа
- `test_lowercase_role_in_result` — независимо от input case

`backend/tests/test_encoding_detector.py` — минимум 5 тестов:
- `test_detects_utf8_sig` — файл с BOM
- `test_detects_plain_utf8` — без BOM
- `test_detects_cp1251` — Windows кодировка
- `test_detects_cp866` — DOS кодировка
- `test_fallback_on_corrupt` — invalid byte sequence

### Phase C — Progress Reporting

#### C1. Backend: progress reporter

`backend/src/optimyzer_backend/ingest/progress_reporter.py`:

```python
import json
import sys
import time
from dataclasses import asdict
from .source import IngestProgress

class ProgressReporter:
    """JSON-RPC notifications fire-and-forget. Throttled до ~4 emit/sec."""
    
    def __init__(self, throttle_ms: int = 250):
        self.throttle_ms = throttle_ms
        self.last_emit = 0.0
    
    def emit(self, progress: IngestProgress, force: bool = False):
        now = time.monotonic() * 1000
        if not force and (now - self.last_emit) < self.throttle_ms:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": "progress",
            "params": asdict(progress),
        }
        sys.stdout.write(json.dumps(notification, ensure_ascii=False) + '\n')
        sys.stdout.flush()
        self.last_emit = now
```

#### C2. RPC: `load_directory`

`backend/src/optimyzer_backend/rpc/archive_rpc.py`:

```python
import threading
from pathlib import Path
from uuid import uuid4

@rpc.method('load_directory')
def load_directory(path: str) -> dict:
    """Запускает background ingestion. Возвращает archive_id сразу."""
    folder = Path(path)
    if not folder.exists():
        raise OptimyzerError(-32602, f"Папка не найдена: {path}")
    if not folder.is_dir():
        raise OptimyzerError(-32602, f"Не папка: {path}")
    
    archive_id = str(uuid4())
    
    thread = threading.Thread(
        target=_ingest_folder_async,
        args=(folder, archive_id),
        daemon=True,
    )
    thread.start()
    
    return {
        "archive_id": archive_id,
        "source_type": "folder",
        "path": str(folder),
        "status": "discovering",
    }

def _ingest_folder_async(folder: Path, archive_id: str):
    reporter = ProgressReporter()
    
    try:
        # === Phase 1: Discovery ===
        reporter.emit(IngestProgress(
            phase='discovering', files_done=0, files_total=0,
            bytes_done=0, bytes_total=0, events_inserted=0,
            current_file=None,
        ), force=True)
        
        source = FolderSource(folder)
        log_files = source.discover()
        total_bytes = sum(lf.size_bytes for lf in log_files)
        
        if not log_files:
            reporter.emit(IngestProgress(
                phase='error', files_done=0, files_total=0,
                bytes_done=0, bytes_total=0, events_inserted=0,
                current_file=None,
                error_message="Лог-файлы не найдены в указанной папке.",
            ), force=True)
            return
        
        # === Phase 2: Parsing + insertion ===
        bytes_done = 0
        events_inserted = 0
        store = DuckDBStore.for_archive(archive_id)
        store.init_schema()  # БЕЗ indexes — создадим в Phase 3
        
        with store.appender('events') as appender:
            for i, log_file in enumerate(log_files):
                encoding = detect_encoding(log_file.path)
                
                # Если detected encoding != 'utf-8-sig' (наш default из discovery) — warning event
                # (sprint 2 опционально — пока просто silently работаем)
                
                file_bytes_done = 0
                file_events = 0
                
                try:
                    for event in parse_log_file_streaming(source, log_file, encoding):
                        appender.append_row(event)
                        events_inserted += 1
                        file_events += 1
                    
                    file_bytes_done = log_file.size_bytes
                
                except Exception as e:
                    # Локальная ошибка в одном файле — logged, не fatal
                    # TODO в Sprint 2: эмитить как warning через notifications
                    pass
                
                bytes_done += file_bytes_done
                
                # Progress emit на каждом файле + intermediate emits через throttle
                reporter.emit(IngestProgress(
                    phase='parsing',
                    files_done=i + 1,
                    files_total=len(log_files),
                    bytes_done=bytes_done,
                    bytes_total=total_bytes,
                    events_inserted=events_inserted,
                    current_file=log_file.relative_path,
                ))
        
        # === Phase 3: Indexing ===
        reporter.emit(IngestProgress(
            phase='indexing', files_done=len(log_files), files_total=len(log_files),
            bytes_done=total_bytes, bytes_total=total_bytes,
            events_inserted=events_inserted, current_file=None,
        ), force=True)
        
        store.create_indexes()
        
        # Metadata
        SQLiteStore().add_recent_source(
            archive_id=archive_id,
            source_type='folder',
            path=str(folder),
            events_count=events_inserted,
            total_bytes=total_bytes,
        )
        
        # === Phase 4: Done ===
        reporter.emit(IngestProgress(
            phase='done', files_done=len(log_files), files_total=len(log_files),
            bytes_done=total_bytes, bytes_total=total_bytes,
            events_inserted=events_inserted, current_file=None,
        ), force=True)
        
    except Exception as e:
        reporter.emit(IngestProgress(
            phase='error', files_done=0, files_total=0,
            bytes_done=0, bytes_total=0, events_inserted=0,
            current_file=None, error_message=str(e),
        ), force=True)
        # Cleanup partial DuckDB
        try:
            DuckDBStore.delete_for_archive(archive_id)
        except Exception:
            pass
```

#### C3. Frontend: subscribe на notifications

`frontend/src-tauri/src/sidecar.rs` — Rust парсит stdout, detect notifications без `id`, emit как Tauri event:

```rust
// При парсинге строки stdout:
// - Если есть "id" поле → это response, send в oneshot channel
// - Если нет "id" но есть "method" → это notification, emit через app.emit("rpc-notification:{method}", params)
```

`frontend/src/api/backend.ts`:

```ts
import { listen } from '@tauri-apps/api/event';

export type ProgressEvent = {
  phase: 'discovering' | 'parsing' | 'indexing' | 'done' | 'error';
  files_done: number;
  files_total: number;
  bytes_done: number;
  bytes_total: number;
  events_inserted: number;
  current_file: string | null;
  error_message: string | null;
};

export function onProgress(cb: (e: ProgressEvent) => void): () => void {
  let unlisten: (() => void) | undefined;
  listen<ProgressEvent>('rpc-notification:progress', (event) => {
    cb(event.payload);
  }).then(fn => { unlisten = fn; });
  return () => unlisten?.();
}
```

#### C4. ProgressCard component

`frontend/src/components/overlays/ProgressCard.tsx`:

Slide-in card в правом верхнем углу. 360×~160px. Содержимое:

- **Title (phase-dependent):** «Поиск логов в папке...» / «Парсинг логов» / «Построение индексов»
- **Progress bar** — заполняется по `bytes_done / bytes_total` (byte-weighted!)
- **Counters line:** `4.2 ГБ / 11.9 ГБ · 38%`
- **File line:** `файл: rphost_28220/26051813.log` (truncated если длинный)
- **Events line:** `847 234 событий загружено`
- **Buttons:** [Свернуть] [Отменить]

При `phase='done'` — карточка transforms в success toast:
- Title: `Готово` (зелёный checkmark)
- Body: `Загружено 1 247 893 событий за 12 мин 34 сек`
- Auto-dismiss через 5 секунд

При `phase='error'` — error toast красный, не auto-dismiss.

Параллельно StatusBar показывает inline mini-progress:
```
● парсинг · rphost_28220/26051813.log · 4.2/11.9 ГБ · 38% · 847К событий
```
С пульсирующей точкой (animation `pulse` уже есть в design system).

#### C5. Cancel handling (опционально для Sprint 1, фиксированное API даже если не impl)

```ts
// RPC method: cancel_ingestion(archive_id) -> { ok: bool }
// В Sprint 1 — RPC только зарегистрирован, реальный cancel — Sprint 2
// (требует thread-safe cancellation token, что есть extra complexity)
// Button [Отменить] в UI — disabled с tooltip "Доступно в Sprint 2"
```

### Phase D — Drag-and-Drop Fix

#### D1. Tauri config

`frontend/src-tauri/tauri.conf.json`:

```json
{
  "app": {
    "windows": [{
      "dragDropEnabled": true,
      "title": "1C-Optimyzer",
      "width": 1440,
      "height": 900,
      "minWidth": 1280,
      "minHeight": 720,
      "resizable": true
    }]
  }
}
```

#### D2. DropZone — Tauri 2 native API

`frontend/src/components/overlays/DropZone.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import { rpc } from '@/api/backend';
import { useAppStore } from '@/store/appStore';
import { t } from '@/i18n/ru';
import styles from './DropZone.module.css';

type DragDropPayload = {
  type: 'enter' | 'over' | 'drop' | 'leave';
  paths?: string[];
  position?: { x: number; y: number };
};

export function DropZone() {
  const [dragActive, setDragActive] = useState(false);
  const showToast = useAppStore(s => s.showToast);
  
  useEffect(() => {
    const unlistens: Array<() => void> = [];
    
    listen<DragDropPayload>('tauri://drag-enter', () => {
      setDragActive(true);
    }).then(fn => unlistens.push(fn));
    
    listen<DragDropPayload>('tauri://drag-leave', () => {
      setDragActive(false);
    }).then(fn => unlistens.push(fn));
    
    listen<DragDropPayload>('tauri://drag-drop', async (event) => {
      setDragActive(false);
      const paths = event.payload.paths;
      if (!paths || paths.length === 0) return;
      
      const firstPath = paths[0];
      
      try {
        const classification = await invoke<{ kind: 'folder' | 'file' | 'missing' }>(
          'classify_path',
          { path: firstPath }
        );
        
        if (classification.kind === 'folder') {
          await rpc.loadDirectory(firstPath);
        } else {
          showToast({ kind: 'error', message: t.errors.invalidDropTarget });
        }
      } catch (e) {
        showToast({ kind: 'error', message: String(e) });
      }
    }).then(fn => unlistens.push(fn));
    
    return () => {
      unlistens.forEach(fn => fn());
    };
  }, [showToast]);
  
  if (!dragActive) return null;
  
  return (
    <div className={styles.overlay}>
      <div className={styles.message}>
        <Icon name="Folder" size={48} />
        <h3>{t.oql.results.empty.hint}</h3>
      </div>
    </div>
  );
}
```

#### D3. classify_path Tauri command

`frontend/src-tauri/src/main.rs`:

```rust
#[tauri::command]
fn classify_path(path: String) -> Result<serde_json::Value, String> {
    use std::path::Path;
    let p = Path::new(&path);
    
    if !p.exists() {
        return Ok(serde_json::json!({ "kind": "missing" }));
    }
    
    let kind = if p.is_dir() { "folder" } else { "file" };
    Ok(serde_json::json!({ "kind": kind }))
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            rpc_call,
            classify_path,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

#### D4. TopBar — кнопка одна, не dropdown

```tsx
// frontend/src/components/chrome/TopBar.tsx
<Button onClick={() => openFolderDialog()}>
  <Icon name="Folder" size={16} />
  {t.topbar.loadFolder}
</Button>

// При наличии recent sources — dropdown с историей справа
<RecentSourcesDropdown />
```

### Phase E — DuckDB Appender + Schema Update

#### E1. Schema с process_role

`backend/src/optimyzer_backend/storage/duckdb_store.py`:

```python
import duckdb
from contextlib import contextmanager
from pathlib import Path

class DuckDBStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(db_path))
    
    @classmethod
    def for_archive(cls, archive_id: str) -> 'DuckDBStore':
        base = Path.home() / 'AppData' / 'Roaming' / '1c-optimyzer' / 'duckdb'
        return cls(base / f'{archive_id}.duckdb')
    
    def init_schema(self):
        """Schema без indexes — индексы добавляются в create_indexes() после bulk insert."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id BIGINT,
                archive_id VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                duration_us BIGINT,
                event_type VARCHAR NOT NULL,
                session_id INT,
                user_name VARCHAR,
                context VARCHAR,
                
                -- NEW в Sprint 1
                process_role VARCHAR,
                process_pid INT,
                
                process VARCHAR,           -- из event поля 'process=...' (может отличаться от process_role)
                
                sql_text TEXT,
                sql_text_normalized TEXT,
                sql_text_hash VARCHAR(64),
                rows_read BIGINT,
                rows_modified BIGINT,
                extra JSON,
                source_file VARCHAR,
                source_line_start INT
            );
        """)
    
    @contextmanager
    def appender(self, table: str = 'events'):
        """DuckDB Appender API — bulk insert."""
        appender = self.conn.appender(table)
        try:
            yield appender
            appender.close()
        except Exception:
            try:
                appender.close()
            except Exception:
                pass
            raise
    
    def create_indexes(self):
        """Indexes ПОСЛЕ bulk insert (стандартная оптимизация bulk loads)."""
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_archive ON events(archive_id);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(archive_id, ts);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(archive_id, event_type);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_duration ON events(archive_id, duration_us DESC);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_sql_hash ON events(archive_id, sql_text_hash);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_role ON events(archive_id, process_role);")
    
    def execute(self, sql: str, params: list = None):
        return self.conn.execute(sql, params or [])
    
    @classmethod
    def delete_for_archive(cls, archive_id: str):
        base = Path.home() / 'AppData' / 'Roaming' / '1c-optimyzer' / 'duckdb'
        path = base / f'{archive_id}.duckdb'
        if path.exists():
            path.unlink()
```

#### E2. Parser update — set process_role

`backend/src/optimyzer_backend/parsers/tj_parser.py` — UPDATE: при создании event объекта добавлять `process_role` и `process_pid` из переданного `LogFile`.

#### E3. Performance baseline tests

`backend/tests/test_duckdb_appender.py`:

```python
def test_appender_inserts_100k_events_under_5s(tmp_path):
    store = DuckDBStore(tmp_path / 'test.duckdb')
    store.init_schema()
    
    start = time.monotonic()
    with store.appender('events') as ap:
        for i in range(100_000):
            ap.append_row(make_synthetic_event_row(i))
    elapsed = time.monotonic() - start
    
    assert elapsed < 5.0, f"100K insert took {elapsed:.2f}s (expected <5s)"
    
    count = store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 100_000
```

### Phase F — OQL Engine

#### F1. Grammar (Lark)

`backend/src/optimyzer_backend/oql/grammar.lark`:

```lark
?start: query

query: source pipe*

source: NAME

pipe: "|" pipe_op

?pipe_op: where_op
       | project_op
       | order_op
       | summarize_op
       | timerange_op
       | limit_op
       | take_op
       | render_op

where_op: "where" expr
project_op: "project" col_list
order_op: "order" "by" order_term ("," order_term)*
summarize_op: "summarize" agg_list ("by" col_list)?
timerange_op: "timerange" ("last" duration)
limit_op: "limit" INT
take_op: "take" INT
render_op: "render" RENDER_TYPE

order_term: NAME ORDER_DIR?
ORDER_DIR: "asc" | "desc"

col_list: NAME ("," NAME)*
agg_list: agg_expr ("," agg_expr)*
agg_expr: NAME "=" AGG_FUNC "(" agg_arg ")"
AGG_FUNC: "sum" | "avg" | "min" | "max" | "count" | "countd"
agg_arg: NAME | "*"

RENDER_TYPE: "table" | "bar" | "line" | "histogram" | "timeline" | "scatter"

?expr: or_expr
?or_expr: and_expr ("or" and_expr)*
?and_expr: not_expr ("and" not_expr)*
?not_expr: "not" comparison | comparison
?comparison: term CMP_OP term       -> binary_cmp
           | term "in" "(" value_list ")"  -> in_cmp
           | term

CMP_OP: "==" | "!=" | "<=" | ">=" | "<" | ">" 
      | "startswith" | "endswith" | "contains" | "matches"

?term: STRING -> string_lit
     | NUMBER DUR_UNIT -> duration_lit
     | NUMBER -> number_lit
     | NAME -> ident
     | "(" expr ")"

DUR_UNIT: "us" | "ms" | "s" | "m" | "h" | "d"

value_list: term ("," term)*

NAME: /[a-zA-Zа-яА-Я_][a-zA-Z0-9а-яА-Я_]*/
STRING: /"([^"\\]|\\.)*"/
NUMBER: /-?\d+(\.\d+)?/
INT: /\d+/

COMMENT: "//" /[^\n]*/
%ignore COMMENT
%ignore /[ \t\r\n]+/
```

#### F2. AST classes + Parser + Compiler + Validator

Подробная implementation — следуй стандартному Lark pattern:
- `ast.py` — dataclasses для всех node types
- `parser.py` — Lark parser + Transformer (parse tree → AST)
- `compiler.py` — AST → DuckDB SQL string + parameters list
- `validator.py` — type/source checking перед compilation

**Ключевые особенности compiler:**

1. **Whitelist columns** — `_safe_ident()` принимает только known columns:
   ```python
   ALLOWED = {
       'ts', 'event_type', 'session_id', 'user_name', 'context',
       'process', 'process_role', 'process_pid',
       'duration_us', 'sql_text', 'sql_text_normalized', 'sql_text_hash',
       'rows_read', 'rows_modified', 'source_file',
       # Aliases для удобства пользователя:
       'duration_ms', 'duration', 'sid', 'sql', 'sql_normalized',
       'role', 'pid',
   }
   
   ALIASES = {
       'duration_ms': 'duration_us',
       'duration': 'duration_us',
       'sid': 'session_id',
       'sql': 'sql_text',
       'sql_normalized': 'sql_text_normalized',
       'role': 'process_role',
       'pid': 'process_pid',
   }
   ```

2. **Duration coercion** — `where Duration > 1000ms` → SQL: `duration_us > 1000000`:
   ```python
   DURATION_UNITS_TO_US = {
       'us': 1, 'ms': 1_000, 's': 1_000_000,
       'm': 60_000_000, 'h': 3_600_000_000, 'd': 86_400_000_000,
   }
   ```

3. **Source restriction for Module 1** — только `events`. Любой другой source → readable error:
   ```python
   if query.source.name != 'events':
       raise OQLCompileError(
           f"Источник '{query.source.name}' недоступен в Module 1. "
           f"Доступен только 'events'. Источники 'metrics', 'deadlocks', "
           f"'code_graph', 'configurations' появятся в следующих модулях."
       )
   ```

4. **Parameterized SQL** — все literal values как параметры, не string concatenation. Защита от injection даже если пользователь — owner.

5. **Friendly error messages** — `Lark UnexpectedToken` парсится и transforms в человекочитаемое:
   ```python
   "Неожиданный токен 'filter' в позиции 47. Возможно, имелось в виду 'where'?"
   ```

#### F3. RPC

`backend/src/optimyzer_backend/rpc/oql_rpc.py`:

```python
@rpc.method('execute_oql_query')
def execute_oql_query(archive_id: str, query: str) -> dict:
    """Parse → validate → compile → execute. Возвращает rows + metadata."""
    
    try:
        ast = parse_oql(query)
    except OQLParseError as e:
        return {"ok": False, "error": str(e), "phase": "parse"}
    
    errors = validate(ast, active_archive_id=archive_id)
    if errors:
        return {"ok": False, "error": "; ".join(errors), "phase": "validate"}
    
    try:
        compiler = SQLCompiler(active_archive_id=archive_id)
        sql, params = compiler.compile(ast)
    except OQLCompileError as e:
        return {"ok": False, "error": str(e), "phase": "compile"}
    
    start = time.monotonic()
    store = DuckDBStore.for_archive(archive_id)
    
    try:
        result = store.execute(sql, params).fetchall()
        columns = [(d[0], str(d[1])) for d in store.conn.description]
    except Exception as e:
        return {"ok": False, "error": f"Ошибка выполнения: {e}", "phase": "execute"}
    
    elapsed_ms = (time.monotonic() - start) * 1000
    
    return {
        "ok": True,
        "columns": [{"name": n, "type": t} for n, t in columns],
        "rows": [list(r) for r in result],
        "row_count": len(result),
        "executed_ms": round(elapsed_ms, 1),
        "render": _extract_render_hint(ast),  # 'table' | 'bar' | 'line' | ...
        "sql_compiled": sql,  # для debug panel
    }

@rpc.method('validate_oql_query')
def validate_oql_query(query: str, archive_id: str | None = None) -> dict:
    """Static check для debounced typing в editor."""
    try:
        ast = parse_oql(query)
    except OQLParseError as e:
        return {"ok": False, "errors": [{"message": str(e), "phase": "parse"}]}
    
    errors = validate(ast, active_archive_id=archive_id)
    if errors:
        return {"ok": False, "errors": [{"message": m, "phase": "validate"} for m in errors]}
    
    return {"ok": True}
```

#### F4. Тесты OQL

`backend/tests/test_oql_parser.py` (~30 tests):
- Basic queries: `events | take 10`
- Multiple wheres: chained
- All pipe operators
- Comments
- Duration units (all 6: us/ms/s/m/h/d)
- Timerange last
- Render types (all 6)
- Russian identifiers: `where context == "РасчётыСервер"`
- Error cases: empty query, unknown operator (с suggestion `'filter' → 'where'?`), missing source, mismatched parens, unterminated string

`backend/tests/test_oql_compiler.py` (~20 tests):
- Every pipe op → correct SQL
- Duration coercion: `1000ms → 1000000`
- All column aliases resolved correctly
- Group by composition (subquery wrapping)
- Unknown column → readable error
- Parameterized values (test injection безопасность)
- process_role filter: `where role == "rphost"`
- Whitelist enforcement

`backend/tests/test_oql_e2e.py` (~15 tests):
- Synthetic events → OQL → DuckDB → results
- All preset queries работают
- Performance: `take 1000` over 100K events < 200ms

### Phase G — CodeMirror Editor

#### G1. CodeMirror 6 setup

```bash
cd frontend
npm install codemirror @codemirror/state @codemirror/view @codemirror/language
npm install @codemirror/autocomplete @codemirror/lint @codemirror/commands @codemirror/search
```

#### G2. OQL StreamLanguage

`frontend/src/codemirror/oql-language.ts` — StreamParser с правильным token typing для каждого элемента OQL grammar. См. цвета в дизайне `optimyzerql.jsx` — точно реплицировать:
- Comments: `#737373`
- Sources (`events`, etc): `#0F766E` bold
- Keywords (`where`, `order by`, etc): `#0F766E` bold
- Strings: `#16A34A`
- Numbers + units: `#D97706`
- Function calls: `#2563EB`
- Pipes `|`: `#A3A3A3`

#### G3. Theme

`frontend/src/codemirror/oql-theme.ts` — EditorView.theme с правильными font (JetBrains Mono), line-height, padding, gutter styling. Background `#FBFBFA`, активная строка с subtle tint, line numbers `#A3A3A3`.

#### G4. Autocomplete

`frontend/src/codemirror/oql-autocomplete.ts` — static completions:
- Sources (5 шт, с tooltip «Module N» для недоступных)
- Keywords (~15)
- Render types (6)
- Column names (whitelist из compiler)
- Aggregation functions (6)

При контекст-aware (after `|`) — приоритет keywords. После `where` — приоритет column names. После `order by` — column names.

#### G5. Linter — real-time validation

`frontend/src/codemirror/oql-linter.ts` — calls `rpc.validateOqlQuery` debounced 500ms. Inline error markers.

#### G6. Editor component

`frontend/src/components/screens/OQLConsole/Editor.tsx`:

```tsx
import { useEffect, useRef } from 'react';
import { EditorView, basicSetup } from 'codemirror';
import { keymap } from '@codemirror/view';
import { Prec } from '@codemirror/state';
import { autocompletion } from '@codemirror/autocomplete';
import { oqlLanguage, oqlHighlightStyle, oqlEditorTheme, oqlCompletions, oqlLinter } from '@/codemirror';

type Props = {
  value: string;
  onChange: (value: string) => void;
  onRun: () => void;
};

export function Editor({ value, onChange, onRun }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    const view = new EditorView({
      doc: value,
      parent: containerRef.current,
      extensions: [
        basicSetup,
        oqlLanguage,
        oqlEditorTheme,
        oqlHighlightStyle,
        autocompletion({ override: [oqlCompletions] }),
        oqlLinter,
        Prec.highest(keymap.of([
          {
            key: 'Ctrl-Enter',
            mac: 'Cmd-Enter',
            run: () => { onRun(); return true; },
          },
        ])),
        EditorView.updateListener.of(update => {
          if (update.docChanged) onChange(update.state.doc.toString());
        }),
      ],
    });
    
    viewRef.current = view;
    return () => view.destroy();
  }, []);
  
  // Sync external changes (templates loading) обратно в editor
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== value) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      });
    }
  }, [value]);
  
  return <div ref={containerRef} className="oql-editor" />;
}
```

### Phase H — Templates Library

#### H1. Templates definition

`backend/src/optimyzer_backend/oql/templates.py`:

```python
TEMPLATES = [
    {
        "id": "first_100",
        "label": "Первые 100 событий",
        "description": "Самые ранние события в архиве",
        "category": "basic",
        "query": "events\n| order by ts asc\n| take 100",
    },
    {
        "id": "longest_100",
        "label": "Самые долгие 100 событий",
        "description": "События с максимальным duration_us",
        "category": "basic",
        "query": "events\n| where duration_us is not null\n| order by duration_us desc\n| take 100",
    },
    {
        "id": "deadlocks_recent",
        "label": "Недавние дедлоки",
        "description": "TDEADLOCK события за последние 24 часа",
        "category": "issues",
        "query": "events\n| where event_type == \"TDEADLOCK\"\n| timerange last 24h\n| order by ts desc",
    },
    {
        "id": "slow_sql",
        "label": "Медленные SQL запросы",
        "description": "DBMSSQL события длительностью больше 1 сек",
        "category": "queries",
        "query": "events\n| where event_type == \"DBMSSQL\" and duration_ms > 1000\n| project ts, duration_ms, sql_text_normalized, rows_read\n| order by duration_ms desc\n| take 100",
    },
    {
        "id": "events_by_type",
        "label": "Распределение по типам событий",
        "description": "Сколько событий каждого типа",
        "category": "stats",
        "query": "events\n| summarize cnt = count(*) by event_type\n| order by cnt desc",
    },
    {
        "id": "events_by_role",
        "label": "Распределение по ролям процессов",
        "description": "rphost / rmngr / ragent / 1cv8c / 1cv8s",
        "category": "stats",
        "query": "events\n| summarize cnt = count(*) by process_role\n| order by cnt desc\n| render bar",
    },
    {
        "id": "memory_alerts",
        "label": "События с памятью > 100 МБ",
        "description": "EXCP, MEM, или CALL events с высоким memory",
        "category": "issues",
        "query": "events\n| where event_type in (\"EXCP\", \"MEM\")\n| order by ts desc\n| take 100",
    },
    {
        "id": "lock_conflicts",
        "label": "Конфликты блокировок",
        "description": "TLOCK события",
        "category": "issues",
        "query": "events\n| where event_type == \"TLOCK\"\n| order by duration_ms desc\n| take 100",
    },
]
```

#### H2. RPC

```python
@rpc.method('list_templates')
def list_templates() -> list[dict]:
    return TEMPLATES
```

#### H3. UI — Templates bar

`frontend/src/components/screens/OQLConsole/TemplatesBar.tsx`:

Bottom bar в OQL Console показывает первые 4-5 templates как кликабельные buttons. Click → query загружается в editor. Кнопка «Шаблоны» открывает full grid modal со всеми templates, поиском, категориями.

### Phase I — Saved Queries

#### I1. SQLite schema

```python
# backend/src/optimyzer_backend/storage/sqlite_store.py — добавить таблицу:

CREATE TABLE IF NOT EXISTS saved_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    query TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP,
    run_count INTEGER DEFAULT 0
);
```

#### I2. RPC

```python
@rpc.method('list_saved_queries')
@rpc.method('save_query')           # name, description, query → id
@rpc.method('delete_saved_query')   # id
@rpc.method('rename_saved_query')   # id, new_name
@rpc.method('mark_query_run')       # id (увеличивает run_count, set last_run_at)
```

#### I3. UI

`SavedQueriesMenu.tsx` — dropdown в editor header. Список saved queries, click → загружает в editor. Кнопка «Сохранить» в actions bar editor показывает dialog «Имя запроса» и сохраняет current content.

### Phase J — Real-data Acceptance Gate

**Главное условие закрытия Sprint 1.**

`backend/tests/test_sprint1_real_folder.py`:

```python
import os
from pathlib import Path
import pytest

REAL_FOLDER_PATH = os.environ.get('OPTIMYZER_REAL_FOLDER_PATH')

@pytest.mark.skipif(
    not REAL_FOLDER_PATH or not Path(REAL_FOLDER_PATH).exists(),
    reason="OPTIMYZER_REAL_FOLDER_PATH not set or folder missing. "
           "Set in .env.test or environment to enable acceptance gate."
)
class TestSprint1RealFolder:
    """Acceptance gate Sprint 1.
    
    Acceptance criteria:
    - Папка ~12 ГБ обрабатывается без exceptions
    - >=95% событий парсятся (сравнение с counted lines)
    - Streaming parser не превышает 500 МБ RAM на peak
    - 10 различных OQL queries работают на parsed data
    """
    
    def test_loads_real_folder_without_exceptions(self, tmp_path):
        folder = Path(REAL_FOLDER_PATH)
        # ... full ingestion run
        # Assertions: status == 'done', events_inserted > 0
    
    def test_parsed_events_coverage_above_95_percent(self, tmp_path):
        # ... count raw event prefixes vs parsed events count
    
    def test_memory_usage_under_500mb(self, tmp_path):
        # ... через resource module — peak RSS during ingestion
    
    def test_oql_queries_on_real_data(self, tmp_path):
        # Прогнать 10 разных OQL queries из templates + custom
        # Assertion: каждый возвращает результат без exception
        pass
```

`.env.test.example`:
```
# Local-only path к реальной папке логов для acceptance tests
# Copy to .env.test (gitignored) и установить актуальный путь
OPTIMYZER_REAL_FOLDER_PATH=D:\1C-Optimyzer\1c-optimyzer\logs
```

`.env.test` → добавить в `.gitignore` (уже там по common patterns, проверь).

### Phase K — Synthetic Data Generator

`backend/tests/fixtures/synthetic/generate_tj_logs.py`:

```python
"""Synthetic TJ log generator для unit tests без real-data dependency.

Usage: python -m backend.tests.fixtures.synthetic.generate_tj_logs --output /tmp/synthetic-logs --size 100MB
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

ROLES = ['rphost', 'rmngr', 'ragent', '1cv8c', '1cv8s']
EVENT_TYPES = ['CALL', 'SCALL', 'DBMSSQL', 'EXCP', 'TLOCK', 'TDEADLOCK', 'MEM']

def generate_event(ts: datetime) -> str:
    """Synthetic event с реалистичной структурой."""
    event_type = random.choice(EVENT_TYPES)
    duration = random.randint(1, 50000)  # microseconds
    process = random.choice(['rphost', 'rmngr', '1cv8c'])
    pid = random.randint(1000, 99999)
    
    base = f"{ts.minute:02d}:{ts.second:02d}.{ts.microsecond:06d}-{duration},{event_type},{random.randint(1,5)},"
    base += f"process={process},OSThread={random.randint(1000, 30000)}"
    
    if event_type == 'DBMSSQL':
        sql = "SELECT * FROM _AccumRgT5634 WHERE _Period >= ? LIMIT 100"
        base += f",Sql='{sql}',Rows={random.randint(0, 10000)}"
    elif event_type == 'CALL':
        base += f",Context='Документ.Реализация.Модуль.ОбработкаПроведения'"
    
    return base + "\n"

def generate_folder(output: Path, total_size_bytes: int):
    output.mkdir(parents=True, exist_ok=True)
    
    # Создать несколько подпапок разных process roles
    subfolder_count = 5
    subfolders = []
    for i in range(subfolder_count):
        role = random.choice(ROLES)
        pid = random.randint(10000, 99999)
        sub = output / f'{role}_{pid}'
        sub.mkdir(exist_ok=True)
        subfolders.append(sub)
    
    bytes_written = 0
    base_ts = datetime.now()
    
    while bytes_written < total_size_bytes:
        sub = random.choice(subfolders)
        ts = base_ts + timedelta(hours=random.randint(0, 23))
        filename = ts.strftime('%y%m%d%H') + '.log'
        filepath = sub / filename
        
        # Write batch of events to this file
        with filepath.open('a', encoding='utf-8-sig') as f:
            for _ in range(random.randint(100, 10000)):
                event_ts = ts + timedelta(microseconds=random.randint(0, 3_600_000_000))
                event = generate_event(event_ts)
                f.write(event)
                bytes_written += len(event.encode('utf-8'))
                
                if bytes_written >= total_size_bytes:
                    break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--size', default='100MB', help='Total size, e.g. 100MB, 1GB')
    args = parser.parse_args()
    
    # Parse size
    size_map = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
    size_str = args.size.upper()
    for suffix, mult in size_map.items():
        if size_str.endswith(suffix):
            total = int(size_str[:-len(suffix)]) * mult
            break
    else:
        total = int(size_str)
    
    generate_folder(args.output, total)
    print(f"Generated {total:,} bytes in {args.output}")
```

Используется в smoke tests и для quick local dev iteration без 12 ГБ dependency.

---

## 5. Definition of Done — Sprint 1

| # | Criterion | Verification |
|---|---|---|
| 1 | `frontend/src/i18n/ru.ts` создан, все UI strings на русском | Manual UI walkthrough |
| 2 | TopBar показывает «Загрузить папку с логами» (одна кнопка, не dropdown) | Visual |
| 3 | Все 18 sidebar items на русском | Visual |
| 4 | StatusBar / Command Palette / Toasts на русском | Visual |
| 5 | FolderSource рекурсивно находит все .log файлы в реальной структуре | pytest |
| 6 | log_detector корректно фильтрует non-TJ файлы | pytest |
| 7 | process_role extractor поддерживает все 6 типов в mixed case | pytest |
| 8 | encoding_detector корректно определяет utf-8-sig (default) | pytest |
| 9 | DuckDB Appender API работает, schema включает process_role | pytest |
| 10 | RPC `load_directory` запускает background ingestion + emits progress | manual + integration |
| 11 | Drag-and-drop **папки** работает (Tauri 2 native API) | manual |
| 12 | Drag-and-drop файла отклоняется с toast «Перетащите папку, не файл» | manual |
| 13 | StatusBar показывает byte-weighted inline progress | manual |
| 14 | ProgressCard slide-in в правом верхнем работает | manual |
| 15 | По завершении — success toast «Загружено N событий за T» | manual |
| 16 | OQL grammar парсит все базовые формы (~30 tests) | pytest |
| 17 | OQL compiler генерирует корректный SQL для всех операторов (~20 tests) | pytest |
| 18 | RPC `execute_oql_query` работает end-to-end | integration |
| 19 | RPC `validate_oql_query` работает для debounced typing | integration |
| 20 | CodeMirror editor с OQL syntax highlighting (точно по дизайн-цветам) | visual |
| 21 | Autocomplete показывает sources/keywords/columns | manual |
| 22 | Inline error markers при невалидном OQL | manual |
| 23 | Ctrl+Enter запускает query | manual |
| 24 | Templates bar показывает 5+ templates, click загружает в editor | manual |
| 25 | Saved queries: save/load/delete работают | manual |
| 26 | pytest суммарно ≥ 100 passing (Sprint 0 had 29, +70+ minimum) | pytest |
| 27 | Conventional commits соблюдены | git log |
| 28 | SPRINT_1_REPORT.md, ADR-009 до ADR-014 обновлены | files exist |
| 29 | **ACCEPTANCE GATE:** Real folder ~12 ГБ обрабатывается без exceptions, ≥95% events parsed | env-gated pytest |
| 30 | **ACCEPTANCE GATE:** 10 различных OQL queries работают на real data, возвращают корректные результаты | env-gated pytest |
| 31 | OPUS_HANDOVER_SPRINT_1.md подготовлен | file exists |

**Пункты 29 и 30** — обязательные blocking gates. Sprint 1 не закрыт пока real-data tests не зелёные.

---

## 6. Что НЕ в Sprint 1 (явно отложено)

- **Cancel ingestion** — кнопка [Отменить] в UI disabled, RPC registered но не functional. Sprint 2.
- **Multi-archive sessions dropdown** — Sprint 1 = simplified replace. Sprint 2 — full multi-session с cleanup.
- **Chart / Timeline / Raw views полностью функциональные** — Sprint 2.
- **Export CSV / JSON / XLSX** — Sprint 2.
- **AI Helper (natural language → OQL)** — Sprint 2 minimum, или Module 2 (LLM integration).
- **Performance tuning** — Sprint 2 (если ingestion > 10 минут на 12 ГБ — нормально для Sprint 1, оптимизация в Sprint 2).
- **Production .msi installer** — Sprint 3.
- **Onboarding / Welcome screen** — Sprint 3.

---

## 7. Дисциплина

- **Conventional commits** обязательны: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `test(scope):`, `docs:`, `chore:`.
- **Один коммит = одна логическая единица.** Никаких mega-commits «всё сделано».
- **Один phase = одна или несколько коммитов**, никаких pull request'ов в середине phase без рабочего unit.
- **Тесты обязательны** для каждого нового модуля. Никакого «потом покрою тестами».
- **Реальная проверка acceptance gate перед закрытием.** Если real-data test упал — это **блокер**, фиксим до закрытия Sprint 1.
- **Документация в момент изменений**, не «потом задокументирую».

---

## 8. Замечания для Claude Code

- **Берегите architectural соответствие** дизайну. Все цвета, шрифты, layout, animations — точно из `design/opt/*.jsx`.
- **Real-data testing — primary acceptance.** Synthetic tests хорошо для CI, но gate Sprint 1 = real 12 ГБ.
- **Byte-weighted progress — критично.** File-count progress даст плохой UX на этих данных.
- **process_role — first-class column.** Это даёт большую ценность OQL запросов (`where role == "rphost"`).
- **Не оптимизируйте парсер преждевременно.** Sprint 1 — correctness first. Если ingestion на 12 ГБ занимает 15 минут — это ок, оптимизация в Sprint 2.
- **Друзьям не давайте `unwrap()`** в Rust. Все error handling — graceful.
- **CSS Modules**, без inline styles. Правило сохраняется.

---

## 9. Готов к работе

Прочти полностью. Запросов на уточнение не должно быть — все архитектурные решения приняты на основе discovery. Если что-то непонятно — задавай в QUESTIONS.md как Q10+.

Стартуй: branch `feat/sprint-1-ingest-and-oql`, Phase A → K последовательно. Удачи. Sprint 1 — это **главный технический спринт** Module 1, после него у нас полностью работающий OptimyzerQL standalone tool, который можно тестировать на реальных кейсах 1С-экспертов.
