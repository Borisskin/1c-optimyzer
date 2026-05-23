# Sprint 5 — MCP BSL Atlas + Semantic Validation + Golden Test Suite

> **Контекст:** Sprint 4 закрыт (tag `v0.4.0-internal`, merge на main). Query Analyzer работает в режиме «paste & analyze» с 13 native rules + AI rewriter через Claude. Native rules матчат **русские ключевые слова SDBL**. Sprint 4 review выявил критический архитектурный insight: в архиве ТЖ поле `DBMSSQL.Sql` содержит **трансформированный T-SQL** (язык СУБД), а **не оригинальный SDBL**. Оригинальный SDBL живёт в коде модулей конфигурации. Это означает что **DBMSSQL → Query Analyzer integration физически требует выгрузку конфигурации** — что переворачивает порядок roadmap.
>
> **Sprint 5 — это центральный шаг к нашему главному конкурентному преимуществу.** Sprint 5 даёт пользователю возможность подключить XML выгрузку своей конфигурации 1С и проверять запросы против **реальной структуры** базы — фича, которой нет ни у ЦУПа, ни у других конкурентов в РФ-сегменте. Это **уникальная позиция** на рынке.
>
> **Дополнительная цель Sprint 5:** собрать `tests/golden/queries/` — regression baseline из 30-50 эталонных SDBL запросов с разметкой ожидаемых findings. Это страховка от того что будущие изменения rules не сломают существующие проверки.
>
> **Working directory:** `D:\1C-Optimyzer\1c-optimyzer\` **Branch от main:** `feat/sprint-5-configuration-metadata`

---

## /goal

### GOAL

Дать Query Analyzer **второй слой анализа — семантический** — против **реальной структуры конкретной конфигурации 1С**. Конкретно:

1. **Подключение XML выгрузки конфигурации.** Пользователь указывает путь к папке с XML выгрузкой 1С (как `C:\BUFFER\SCHEME\` у Сергея). Backend парсит выгрузку, строит индекс метаданных в SQLite: справочники / документы / регистры / реквизиты / измерения / типы. Подключение опциональное — Query Analyzer продолжает работать без выгрузки в текущем синтаксическом режиме.

2. **Семантические rules — новая категория `category: semantic`.** Минимум 8 семантических правил которые проверяют запрос против индекса метаданных: существование объектов, существование реквизитов, корректность типов в `ВЫРАЗИТЬ`, существование измерений виртуальных таблиц, и т.д.

3. **UI индикация состояния конфигурации.** Badge в Sidebar / в верхней части QueryAnalyzer screen — «Конфигурация: подключена ✓ (БП 3.0, 1247 объектов)» или «Конфигурация не подключена — доступны только синтаксические проверки».

4. **Golden test suite — `tests/golden/queries/`.** 30-50 эталонных SDBL запросов с разметкой ожидаемых findings. Pytest-suite который автоматически проходит по всему набору и сверяет результат. Это regression baseline для всех будущих изменений rules.

5. **Архитектурная подготовка под Sprint 6** (DBMSSQL → Query Analyzer integration). Sprint 5 закладывает Configuration Metadata API так, чтобы Sprint 6 мог использовать его для **поиска оригинального SDBL в модулях** по Context из события `DBMSSQL`.

**Measurable outcome:**

- Middle-программист 1С подключает свою XML выгрузку → Query Analyzer показывает finding «Регистр накопления `ТоварыНаСкладах` не существует в этой конфигурации — возможно вы скопировали запрос из УТ, а у вас БП. Аналогичные данные в БП лежат в регистре бухгалтерии `Хозрасчетный`».
- Время подключения выгрузки: парсинг 1247 объектов БП 3.0 за < 30 секунд.
- Семантические проверки одного запроса: < 1 секунды после первичного парсинга выгрузки.
- Golden test suite: 30-50 запросов, прогон полного набора < 60 секунд, все ожидаемые findings матчатся.

### CONTEXT

**Состояние после Sprint 4 (baseline для Sprint 5):**

- Tag `v0.4.0-internal` на main
- 360 backend tests passing
- 13 native rules в `backend/src/optimyzer_backend/query_analyzer/native_rules/rules/`
- AI rewriter через Claude Sonnet работает (backend-only)
- Frontend QueryAnalyzer screen с CodeMirror подсветкой findings + RewriteDiff modal
- ТЖ-симулятор в `tools/tj-simulator/` (наследие Sprint 3.5) — пригодится для генерации тестовых ситуаций
- 60+ PowerShell-скиллов в `.claude/skills/` для работы с 1С конфигурациями
- ADR-025 (pivot на native-only вместо BSL Language Server) принят как окончательное решение

**Окружение пользователя:**

- База: серверная, `Srvr="localhost:2541";Ref="Test1CProf"` (учебная база из курса 1С:Эксперт; это **БП 3.0** или близкая конфигурация — Phase 0 уточнит)
- XML выгрузка конфигурации: `C:\BUFFER\SCHEME\` — **уже готова**, Сергей выгрузил из Конфигуратора
- Платформа 1С: 8.3.27.1859
- Java установлена (наследие подготовки к BSL LS которая не понадобилась)

**Стратегические решения принятые ДО Sprint 5 (обязательны):**

- **Решение 1:** Configuration metadata индексируется в **SQLite** в `data/config_metadata.db`. Не DuckDB (там события ТЖ), не in-memory (нужна persistence между запусками tool).
- **Решение 2:** Подключение конфигурации — **опциональное**. Query Analyzer работает без неё в синтаксическом режиме. Если конфигурация подключена — добавляются семантические rules. **Никаких mandatory dependencies.**
- **Решение 3:** Парсинг XML выгрузки — **через стандартную библиотеку Python (`xml.etree.ElementTree`)**, без внешних зависимостей. Структура XML выгрузки 1С хорошо документирована и стабильна между версиями платформы.
- **Решение 4:** Семантические rules — **отдельный класс** в native_rules engine. Они имеют поле `requires: configuration_metadata`. Если конфигурация не подключена — эти rules **молчат** (не false positive, не warning «не могу проверить»), просто пропускаются.
- **Решение 5:** Golden test suite — **plain `.sdbl` файлы + `.expected.json`** рядом. Никаких pickle, никаких бинарных форматов. Чтобы любой человек мог открыть файл, прочитать запрос, понять что ожидается.
- **Решение 6:** Sprint 5 НЕ интегрируется с архивом ТЖ. Query Analyzer остаётся в режиме «paste & analyze» с дополнительным семантическим слоем. Интеграция с DBMSSQL событиями — Sprint 6 scope.
- **Решение 7:** Sprint 5 НЕ работает напрямую с базой 1С (не запускает 1cv8c.exe, не использует mcp-1c). Только XML выгрузка как статический источник. Это сознательное упрощение для скорости.

**Архитектурная подготовка под Sprint 6 (DBMSSQL integration):**

Configuration Metadata API в Sprint 5 закладывает методы которые Sprint 6 будет использовать для извлечения оригинального SDBL из модулей:

```python
# Sprint 5 API
class ConfigurationMetadataStore:
    def is_object_exists(self, full_name: str) -> bool: ...
    def get_attributes(self, object_full_name: str) -> list[Attribute]: ...
    def get_register_dimensions(self, register_full_name: str) -> list[Dimension]: ...

# Sprint 6 расширение
class ConfigurationMetadataStore:
    # ... methods from Sprint 5
    def find_module_by_context(self, tj_context: str) -> ModuleLocation | None:
        """Sprint 6: парсит stack trace из DBMSSQL.Context, находит модуль."""
    def extract_sdbl_from_module(self, module_location: ModuleLocation, line: int) -> str | None:
        """Sprint 6: извлекает текст запроса из строкового литерала рядом с указанной строкой."""
```

Sprint 5 **не реализует** последние два метода (placeholders) но **закладывает интерфейс**.

**Ключевые файлы которые трогаем:**

- `backend/src/optimyzer_backend/configuration_metadata/` — **новый пакет**
- `backend/src/optimyzer_backend/configuration_metadata/parser.py` — парсер XML выгрузки
- `backend/src/optimyzer_backend/configuration_metadata/store.py` — SQLite indexed store
- `backend/src/optimyzer_backend/configuration_metadata/api.py` — high-level API для query analyzer
- `backend/src/optimyzer_backend/query_analyzer/semantic_rules/` — **новая папка** с semantic markdown rules
- `backend/src/optimyzer_backend/query_analyzer/engine.py` — расширение для category=semantic + requires=configuration_metadata
- `backend/src/optimyzer_backend/rpc/configuration_rpc.py` — новые RPC методы (`connect_configuration`, `get_configuration_status`, `disconnect_configuration`)
- `backend/tests/test_configuration_metadata.py` — unit tests парсера и store
- `backend/tests/test_semantic_rules.py` — unit tests semantic rules
- `backend/tests/golden/queries/` — **новая папка** с golden test suite
- `backend/tests/golden/queries/positive/` — 10+ запросов с явными проблемами
- `backend/tests/golden/queries/negative/` — 10+ «чистых» запросов
- `backend/tests/golden/queries/edge_cases/` — 10+ edge cases
- `backend/tests/golden/queries/real_world/` — 10+ запросов из реальных DBMSSQL контекстов
- `backend/tests/test_golden_suite.py` — runner для golden test suite
- `frontend/src/components/screens/QueryAnalyzer/ConfigurationBadge.tsx` — **новый компонент** статуса конфигурации
- `frontend/src/components/settings/ConfigurationSection.tsx` — **новый компонент** в Settings для подключения папки выгрузки
- `frontend/src/i18n/ru.ts` — новые strings
- `docs/CONFIGURATION_XML_FORMAT_STUDY.md` — Phase 0 deliverable
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` — обновить статусы
- `docs/CCH_FEATURE_PARITY_REFERENCE.md` — обновить статус Раздела 2.13.5
- `docs/DECISIONS.md` — ADR-029..032
- `docs/SPRINT_5_REPORT.md`, `docs/OPUS_HANDOVER_SPRINT_5.md`

### CONSTRAINTS

**Глобальные (обязательны):**

- CSS Modules, no inline styles
- ru-RU локализация в `i18n/ru.ts`
- Conventional commits (feat/fix/refactor/test/docs/chore) с scope
- No time estimates anywhere
- Light theme only — dark theme FORBIDDEN
- Не модифицировать `design/opt/*.jsx`
- ADR-001..028 в силе (не пересматривать)

**Sprint 5 специфичные:**

- Парсинг XML выгрузки — **только стандартная Python библиотека**, без `lxml` / `xmltodict` / других внешних зависимостей. `xml.etree.ElementTree` достаточен.
- SQLite indexed store **локально** в `data/config_metadata.db`. Если файл существует от прошлой сессии — пересоздавать только если хеш папки выгрузки изменился.
- Семантические rules — **silent on missing metadata**. Если конфигурация не подключена — rule просто не запускается. **Не показываем баннер «не могу проверить, подключите конфигурацию»** на каждый запрос — это раздражает. Только глобальный badge статуса в UI.
- Golden test suite — формат строгий: каждая папка содержит `query.sdbl` + `expected.json`. Pytest runner итерирует по папкам.
- Configuration metadata persistence: если выгрузка уже распарсена и индекс есть — не парсить заново при перезапуске tool. Использовать хеш папки (modification time + размер) для invalidation.

**Запрещено в Sprint 5:**

- НЕ интегрироваться с архивом ТЖ (Sprint 6 scope)
- НЕ запускать `1cv8c.exe` или работать с базой через ВК (это другая категория интеграции, Sprint 7+ возможно)
- НЕ парсить модули `.bsl` файлы для извлечения SDBL литералов (это Sprint 6 scope — поиск запросов по Context)
- НЕ делать UI для просмотра структуры конфигурации (это отдельная фича — Sprint 8+ возможно как Configuration Browser)
- НЕ модифицировать существующие Sprint 4 native rules (категория `performance` / `correctness` / `style`). Семантические rules — **дополнение**, не замена.

### PRIORITY

- **P1 (блокирующее закрытие Sprint 5):**
  - Phase 0 — Discovery формата XML выгрузки 1С (структура папок, корневые элементы)
  - Phase A — Backend парсер XML + SQLite store + tests
  - Phase B — Semantic rules engine + минимум 8 markdown rules
  - Phase C — RPC методы для подключения / статуса / disconnect
  - Phase D — Frontend ConfigurationBadge + Settings секция
  - Phase E — Golden test suite (минимум 30 запросов: 10 positive + 10 negative + 10 edge cases)
  - Phase G — Real-data acceptance на выгрузке Test1CProf пользователя
- **P2 (важно но не блокирующее):**
  - Phase F — 10 real-world запросов в golden suite (extracted manually из DBMSSQL событий)
  - Phase H — Документация + ADR'ы
- **P3 (nice-to-have):**
  - Подсветка семантических findings отдельным цветом в CodeMirror (например purple вместо red/amber/blue)
  - Подсказка в hover-tooltip «Этот объект существует в вашей конфигурации» (positive feedback)

### PLAN

**Phase 0 — Discovery: формат XML выгрузки 1С**

Цель: получить fact-based input о структуре выгрузки до написания парсера.

Создать `backend/scripts/inspect_configuration_xml.py` который:

1. Принимает путь к выгрузке (default из `.env.test` — `C:\BUFFER\SCHEME\` для Сергея)
2. Идёт по корневой структуре, считает количество объектов каждого типа
3. Для типовых объектов (Документ, Справочник, РегистрНакопления, РегистрСведений, РегистрБухгалтерии, ПланВидовХарактеристик) — выгребает schema XML:
   - Корневой элемент
   - Структура атрибутов (имя, тип)
   - Структура измерений / ресурсов / реквизитов
   - Структура табличных частей
4. Для **виртуальных таблиц регистров** (Остатки, Обороты, ОстаткиИОбороты, СрезПоследних) — какие XML-теги их описывают
5. Записывает результат в `docs/CONFIGURATION_XML_FORMAT_STUDY.md`

Output формат:

```markdown
# Configuration XML Format Study — выгрузка БП 3.0

## Общая статистика

Папка: C:\BUFFER\SCHEME
Корневой файл: Configuration.xml
Объектов: 1247
  - Справочников: 312
  - Документов: 168
  - РегистровНакопления: 47
  - РегистровСведений: 89
  - РегистровБухгалтерии: 3
  - ПлановВидовХарактеристик: 14
  - ПлановСчетов: 1
  - Перчислений: 234
  - ОбщихМодулей: 187

## Структура одного объекта (Справочник.Контрагенты)

Папка: Catalogs/Контрагенты/
Файлы:
  - Контрагенты.xml — основные свойства
  - Forms/ — формы
  - Templates/ — шаблоны печати
  - Ext/ — модули
  - ...

## Schema корневого XML файла справочника

[пример XML с разметкой что есть что]

## ... (аналогично для других типов объектов)

## Виртуальные таблицы регистров

Регистр.Остатки — описано в XML файле регистра, тег <Resources/>
Регистр.Обороты — описано там же
...
```

Это документ — **критический input** для Phase A (парсер). Без него мы гадаем о структуре.

**STOP RULE:** если выяснится что XML выгрузка имеет **сильно разную структуру** между типами объектов (например, План Видов Характеристик кардинально отличается от Справочника) или версиями платформы — **остановиться и спросить архитектора через ranked options**: (a) парсить только основные типы (Документ/Справочник/Регистры) в Sprint 5, остальное — Sprint 6+, (b) сделать generic парсер с base class + специализациями.

**Phase A — Backend парсер XML + SQLite store**

`backend/src/optimyzer_backend/configuration_metadata/parser.py`:

```python
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
from pathlib import Path

class ObjectKind(str, Enum):
    CATALOG = "Справочник"
    DOCUMENT = "Документ"
    ACCUMULATION_REGISTER = "РегистрНакопления"
    INFORMATION_REGISTER = "РегистрСведений"
    ACCOUNTING_REGISTER = "РегистрБухгалтерии"
    CHART_OF_CHARACTERISTIC_TYPES = "ПланВидовХарактеристик"
    CHART_OF_ACCOUNTS = "ПланСчетов"
    ENUM = "Перечисление"
    COMMON_MODULE = "ОбщийМодуль"
    # ...

@dataclass
class Attribute:
    name: str
    type_kind: str          # "Строка" | "Число" | "СправочникСсылка" | "ДокументСсылка" | etc
    type_ref: str | None    # "Справочник.Контрагенты" если type_kind ссылочный
    length: int | None      # для строки
    precision: int | None   # для числа

@dataclass
class Dimension:
    name: str
    type_kind: str
    type_ref: str | None

@dataclass
class Resource:
    name: str
    type_kind: str

@dataclass
class ConfigurationObject:
    kind: ObjectKind
    name: str              # "Контрагенты"
    full_name: str         # "Справочник.Контрагенты"
    synonym: str | None    # человеческое имя для UI
    attributes: list[Attribute]
    dimensions: list[Dimension]   # только для регистров
    resources: list[Resource]     # только для регистров
    tabular_sections: list[str]   # имена табличных частей

class ConfigurationParser:
    def __init__(self, configuration_xml_path: Path):
        self.root_path = configuration_xml_path
        
    def parse(self) -> list[ConfigurationObject]:
        """Парсит всю выгрузку, возвращает список объектов."""
        # 1. Читать Configuration.xml в корне
        # 2. Для каждого упомянутого объекта — идти в подпапку, парсить специфический XML
        # 3. Применять правильный парсер для типа объекта
        # 4. Возвращать список ConfigurationObject
```

`backend/src/optimyzer_backend/configuration_metadata/store.py`:

```python
import sqlite3
import hashlib
from pathlib import Path

class ConfigurationMetadataStore:
    """SQLite-индекс метаданных конфигурации.
    
    Schema:
        objects (full_name TEXT PRIMARY KEY, kind TEXT, name TEXT, synonym TEXT)
        attributes (object_full_name TEXT, name TEXT, type_kind TEXT, type_ref TEXT, ...)
        dimensions (register_full_name TEXT, name TEXT, type_kind TEXT, type_ref TEXT)
        resources (register_full_name TEXT, name TEXT, type_kind TEXT)
        tabular_sections (object_full_name TEXT, name TEXT)
        meta (key TEXT PRIMARY KEY, value TEXT)  -- хеш выгрузки, дата индексации, версия
    """
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path("data/config_metadata.db")
        self.db_path = db_path
        self._connect_or_create()
    
    def index_configuration(self, configuration_xml_path: Path) -> dict:
        """Парсит выгрузку и заполняет таблицы. Возвращает статистику."""
        new_hash = self._compute_hash(configuration_xml_path)
        existing_hash = self._get_meta("source_hash")
        
        if existing_hash == new_hash:
            return {
                "status": "already_indexed",
                "object_count": self._count_objects(),
            }
        
        # Очистить старое
        self._truncate_all()
        
        # Парсить новое
        parser = ConfigurationParser(configuration_xml_path)
        objects = parser.parse()
        
        # Сохранить в БД
        for obj in objects:
            self._save_object(obj)
        
        self._set_meta("source_hash", new_hash)
        self._set_meta("source_path", str(configuration_xml_path))
        self._set_meta("indexed_at", datetime.now().isoformat())
        
        return {
            "status": "indexed",
            "object_count": len(objects),
            "by_kind": self._stats_by_kind(),
        }
    
    # High-level API для query analyzer
    def is_object_exists(self, full_name: str) -> bool: ...
    def get_attributes(self, object_full_name: str) -> list[Attribute]: ...
    def get_dimensions(self, register_full_name: str) -> list[Dimension]: ...
    def get_resources(self, register_full_name: str) -> list[Resource]: ...
    def get_object_kind(self, full_name: str) -> ObjectKind | None: ...
    def search_similar_objects(self, full_name: str, max_distance: int = 3) -> list[str]:
        """Levenshtein distance для подсказок 'возможно вы имели в виду...'."""
    
    # Placeholders для Sprint 6 (не реализуются в Sprint 5)
    def find_module_by_context(self, tj_context: str) -> 'ModuleLocation | None':
        raise NotImplementedError("Sprint 6 feature")
    
    def extract_sdbl_from_module(self, module_location, line: int) -> str | None:
        raise NotImplementedError("Sprint 6 feature")
```

Тесты `backend/tests/test_configuration_metadata.py`:
- `test_parse_synthetic_xml_minimal` — на минимальном synthetic XML
- `test_parse_catalog_with_attributes` — справочник с реквизитами
- `test_parse_register_with_dimensions_and_resources` — регистр накопления
- `test_parse_register_virtual_tables` — виртуальные таблицы (Остатки/Обороты)
- `test_hash_invalidation` — если хеш папки меняется — пересохранение
- `test_hash_stable` — если папка не менялась — не пересохранение
- `test_search_similar_objects_levenshtein` — поиск похожих имён

**Phase B — Semantic rules engine**

Расширить `backend/src/optimyzer_backend/query_analyzer/engine.py`:

```python
@dataclass
class Rule:
    id: str
    severity: str
    category: str          # "performance" | "correctness" | "style" | "semantic"  ← NEW
    requires: list[str]    # ["configuration_metadata"] для semantic rules  ← NEW
    # ...

def analyze(query_text: str, rules: list[Rule], 
            config_store: ConfigurationMetadataStore | None = None) -> list[Finding]:
    findings = []
    for rule in rules:
        # Skip semantic rules if no config
        if "configuration_metadata" in rule.requires and config_store is None:
            continue
        
        if rule.category == "semantic":
            findings.extend(_analyze_semantic(query_text, rule, config_store))
        else:
            findings.extend(_analyze_syntactic(query_text, rule))
    
    return findings
```

Семантические rules в `backend/src/optimyzer_backend/query_analyzer/semantic_rules/rules/`:

```
semantic_rules/
├── README.md
├── object_not_exists.md
├── attribute_not_exists.md
├── register_dimension_not_exists.md
├── register_resource_not_exists.md
├── vyrazit_type_not_exists.md
├── virtual_table_not_supported.md
├── tabular_section_not_exists.md
└── enum_value_not_exists.md
```

Пример semantic rule `object_not_exists.md`:

```markdown
---
id: object_not_exists
applies_to: sdbl_query
severity: critical
category: semantic
requires: [configuration_metadata]
match:
  type: semantic_check
  check: extract_objects_from_query_then_verify_existence
tags: [semantic-check, configuration-validation]
---

# Объект не существует в подключённой конфигурации

## Что не так

Запрос ссылается на объект `{{object_full_name}}`, которого нет в подключённой
конфигурации.

## Почему это плохо

Запрос либо использует объект из другой конфигурации (например, скопирован из
УТ а используется в БП), либо ссылается на объект который был удалён или
переименован. В обоих случаях запрос **не выполнится** в вашей базе.

## Похожие имена в вашей конфигурации

{{similar_objects}}

## Как исправить

1. Проверьте имя объекта — возможно есть опечатка
2. Если объект из другой конфигурации — найдите аналог в вашей. Например, в БП 3.0
   данные о товарах на складах лежат в регистре бухгалтерии `Хозрасчетный`, а не в
   регистре накопления `ТоварыНаСкладах` как в УТ
3. Проверьте что XML выгрузка актуальна — возможно объект добавлен в конфигурацию
   после выгрузки
```

Для семантических rules **простой regex** недостаточен — нужен **извлекатель токенов из SDBL**. Не полный парсер, а regex-based extractor:

```python
# backend/src/optimyzer_backend/query_analyzer/sdbl_tokenizer.py

def extract_object_references(query_text: str) -> list[ObjectReference]:
    """Извлекает упоминания объектов вида 'Документ.X', 'Справочник.Y',
    'РегистрНакопления.Z' из текста запроса."""
    
    pattern = r'\b(Документ|Справочник|РегистрНакопления|РегистрСведений|РегистрБухгалтерии|ПланВидовХарактеристик|ПланСчетов|Перечисление)\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\b'
    # ... возвращает list[ObjectReference(kind, name, line, col_start, col_end)]
```

Этот tokenizer **не парсер SDBL** — он не понимает структуру запроса, только находит references. Для семантических проверок этого достаточно. Полноценный SDBL парсер — отдельная задача (Sprint 6+).

Минимум 8 semantic rules с positive + negative unit tests каждое.

**Phase C — RPC методы**

`backend/src/optimyzer_backend/rpc/configuration_rpc.py`:

```python
@rpc.method("configuration.connect")
def connect_configuration_rpc(path: str) -> dict:
    """Подключает XML выгрузку конфигурации."""
    path = Path(path)
    if not path.exists():
        return {"ok": False, "error": "Path does not exist"}
    
    store = ConfigurationMetadataStore()
    try:
        result = store.index_configuration(path)
        return {
            "ok": True,
            "status": result["status"],  # "indexed" | "already_indexed"
            "object_count": result["object_count"],
            "by_kind": result.get("by_kind"),
            "indexed_at": store.get_meta("indexed_at"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@rpc.method("configuration.status")
def get_configuration_status_rpc() -> dict:
    """Возвращает текущий статус подключённой конфигурации."""
    store = ConfigurationMetadataStore()
    if not store.is_indexed():
        return {"connected": False}
    return {
        "connected": True,
        "source_path": store.get_meta("source_path"),
        "indexed_at": store.get_meta("indexed_at"),
        "object_count": store.count_objects(),
        "by_kind": store.stats_by_kind(),
    }

@rpc.method("configuration.disconnect")
def disconnect_configuration_rpc() -> dict:
    """Отключает конфигурацию (удаляет SQLite файл)."""
    store = ConfigurationMetadataStore()
    store.clear()
    return {"ok": True}
```

Также обновить `query_analyzer.analyze` чтобы он автоматически использовал config store если он подключён:

```python
@rpc.method("query_analyzer.analyze")
def analyze_query_rpc(query_text: str) -> dict:
    config_store = get_configuration_store_if_connected()  # None если не подключено
    findings = analyze_query(query_text, config_store=config_store)
    return {
        "query_text": query_text,
        "findings": [_finding_to_dict(f) for f in findings],
        "configuration_connected": config_store is not None,
        "summary": _compute_summary(findings),
    }
```

**Phase D — Frontend ConfigurationBadge + Settings секция**

Файлы:
- `frontend/src/components/screens/QueryAnalyzer/ConfigurationBadge.tsx` — badge в шапке QueryAnalyzer
- `frontend/src/components/settings/ConfigurationSection.tsx` — секция в Settings
- `frontend/src/state/configurationStore.ts` — Zustand store для состояния

**ConfigurationBadge** в QueryAnalyzer screen (в шапке рядом с заголовком):

```
Состояние «не подключено»:
┌─────────────────────────────────────────────────────────────┐
│ Анализ запроса                  [Конфигурация не подключена]│
│ Вставьте текст 1С-запроса (SDBL)...                          │
└─────────────────────────────────────────────────────────────┘

Состояние «подключено»:
┌─────────────────────────────────────────────────────────────┐
│ Анализ запроса                  [Конфигурация: БП 3.0 ✓]    │
│                                  1247 объектов               │
└─────────────────────────────────────────────────────────────┘
```

Hover на badge — tooltip с деталями (имя из synonym или из путей, дата индексации, путь). Click — переход в Settings.

**Settings секция** «Конфигурация 1С»:

```
┌─────────────────────────────────────────────────────────────┐
│ Конфигурация 1С                                              │
│                                                              │
│ ☐ Конфигурация не подключена                                │
│                                                              │
│ Подключите XML выгрузку конфигурации чтобы Query Analyzer    │
│ мог проверять запросы против реальной структуры вашей базы. │
│                                                              │
│ [Указать папку выгрузки...]    [Подробнее →]                │
└─────────────────────────────────────────────────────────────┘

После подключения:
┌─────────────────────────────────────────────────────────────┐
│ Конфигурация 1С                                              │
│                                                              │
│ ✓ Подключена                                                │
│                                                              │
│ Путь:    C:\BUFFER\SCHEME                                   │
│ Имя:     Бухгалтерия предприятия, редакция 3.0              │
│ Объектов: 1247 (312 справочников, 168 документов, ...)      │
│ Индекс:  обновлён 20.05.2026 21:34                          │
│                                                              │
│ [Переиндексировать]  [Отключить]                            │
└─────────────────────────────────────────────────────────────┘
```

Через input type="file" в Tauri нативный folder picker (Tauri 2 API: `dialog.open({directory: true})`).

После успешного подключения — toast «Конфигурация подключена: 1247 объектов проиндексировано за 18 секунд».

**Phase E — Golden test suite**

Структура:

```
backend/tests/golden/queries/
├── README.md
├── positive/                          # запросы с явными проблемами
│   ├── 01_subquery_in_join/
│   │   ├── query.sdbl
│   │   └── expected.json              # {"findings": ["subquery_in_join"]}
│   ├── 02_virtual_table_in_join/
│   ├── 03_or_in_where/
│   ├── ... (10 запросов)
├── negative/                          # «чистые» запросы — 0 critical/warning findings
│   ├── 01_simple_select/
│   ├── 02_proper_join_with_temp_table/
│   ├── ... (10 запросов)
├── edge_cases/                        # граничные случаи
│   ├── 01_empty_query/
│   ├── 02_only_comments/
│   ├── 03_5_level_nested_subquery/
│   ├── 04_query_with_10_temp_tables/
│   ├── ... (10 запросов)
├── real_world/                        # реальные запросы из DBMSSQL контекстов (Phase F)
│   ├── 01_from_invoice_posting/
│   ├── ... (10 запросов из Test1CProf)
└── semantic/                          # запросы для semantic rules (require config_metadata)
    ├── 01_unknown_register/
    │   ├── query.sdbl                  # ВЫБРАТЬ ИЗ РегистрНакопления.НеСуществующий
    │   ├── expected.json               # {"findings": ["object_not_exists"], "requires_configuration": true}
    │   └── configuration.expected      # "Test1CProf"  - в какой конфигурации ожидается
    ├── ... (5+ запросов)
```

Формат `expected.json`:

```json
{
    "findings": [
        {
            "rule_id": "or_in_where",
            "severity": "warning",
            "line_range": [8, 8]
        },
        {
            "rule_id": "vyrazit_in_where",
            "severity": "warning",
            "line_range": [9, 9]
        }
    ],
    "requires_configuration": false,
    "notes": "Classic anti-pattern: OR + VYRAZIT in WHERE clause"
}
```

Pytest runner `backend/tests/test_golden_suite.py`:

```python
import json
from pathlib import Path
import pytest

GOLDEN_ROOT = Path(__file__).parent / "golden" / "queries"

def collect_golden_cases():
    """Собирает все папки с query.sdbl + expected.json."""
    cases = []
    for category in ["positive", "negative", "edge_cases", "real_world", "semantic"]:
        category_path = GOLDEN_ROOT / category
        if not category_path.exists():
            continue
        for case_dir in sorted(category_path.iterdir()):
            if not case_dir.is_dir():
                continue
            query_file = case_dir / "query.sdbl"
            expected_file = case_dir / "expected.json"
            if query_file.exists() and expected_file.exists():
                cases.append((category, case_dir.name, query_file, expected_file))
    return cases

@pytest.mark.parametrize("category, name, query_file, expected_file", collect_golden_cases())
def test_golden_query(category, name, query_file, expected_file):
    """Каждый golden case прогоняется через query analyzer."""
    query_text = query_file.read_text(encoding="utf-8")
    expected = json.loads(expected_file.read_text(encoding="utf-8"))
    
    config_store = None
    if expected.get("requires_configuration"):
        config_store = _get_test_configuration_store()  # use Test1CProf fixture
    
    findings = analyze_query(query_text, config_store=config_store)
    
    # Verify expected rules are matched
    expected_rule_ids = {f["rule_id"] for f in expected["findings"]}
    actual_rule_ids = {f.rule_id for f in findings}
    
    missing = expected_rule_ids - actual_rule_ids
    if missing:
        pytest.fail(f"Missing expected findings: {missing}")
    
    # For negative cases — verify NO critical/warning findings
    if category == "negative":
        critical_warning = [f for f in findings if f.severity in ("critical", "warning")]
        if critical_warning:
            pytest.fail(f"Negative case got unexpected findings: {[f.rule_id for f in critical_warning]}")
```

Это даёт **30+ автотестов** одним runner'ом. Любое будущее изменение rules — если ломает baseline — сразу видно.

**Phase F — Real-world запросы из DBMSSQL**

Manual extraction: открыть архив ТЖ Сергея в нашем tool'е, найти топ-20 DBMSSQL событий, посмотреть `Context` (stack trace до места вызова), **попросить Сергея найти оригинальный SDBL в модуле БП 3.0** (вручную через Конфигуратор), сохранить как golden case.

Это **manual work** — но он даёт **самые ценные test cases**. 10 запросов = 10 golden tests на realистике.

Сергей делает это сам или Claude Code просит данные через AskUserQuestion если нужно.

**Phase G — Real-data acceptance gate**

`backend/tests/test_sprint5_real_data.py`:

```python
@pytest.mark.skipif(not OPTIMYZER_REAL_FOLDER_PATH, reason="...")
class TestSprint5Acceptance:
    
    def test_configuration_xml_format_study_documented(self):
        """Phase 0 deliverable exists."""
    
    def test_index_test1cprof_configuration(self):
        """Парсинг C:\\BUFFER\\SCHEME полностью завершается за < 30 секунд.
        Минимум 100 объектов проиндексировано."""
    
    def test_semantic_rules_minimum_8(self):
        """Phase B: минимум 8 semantic rules."""
    
    def test_semantic_rule_object_not_exists_on_real_config(self):
        """На запросе с несуществующим в БП объектом (например 'РегистрНакопления.ТоварыНаСкладах'
        который характерен для УТ а не БП) — semantic rule срабатывает."""
    
    def test_semantic_rules_silent_without_config(self):
        """Без подключённой конфигурации semantic rules не запускаются (не выдают
        false positive, не выдают warning о пропуске)."""
    
    def test_golden_suite_minimum_30_cases(self):
        """В golden test suite минимум 30 запросов суммарно."""
    
    def test_golden_suite_all_pass(self):
        """Все golden cases успешно проходят (один run)."""
    
    def test_configuration_metadata_persistence(self):
        """После перезапуска tool конфигурация остаётся подключённой
        (читается из data/config_metadata.db без переиндексации)."""
    
    def test_real_world_queries_get_findings(self):
        """Минимум 7 из 10 real-world запросов получают ≥1 finding."""
```

**Phase H — Документация + ADR'ы**

`docs/CONFIGURATION_XML_FORMAT_STUDY.md` (Phase 0 deliverable).

`docs/CONNECTING_CONFIGURATION.md` — инструкция для пользователя:
1. Откройте Конфигуратор 1С
2. Меню «Конфигурация» → «Выгрузить конфигурацию в файлы XML...»
3. Выберите папку (рекомендуется отдельная папка, например `C:\BUFFER\SCHEME\`)
4. Дождитесь окончания (1-5 минут для типичной конфигурации)
5. В 1C-Optimyzer откройте Settings → Конфигурация 1С → «Указать папку выгрузки»
6. Укажите ту же папку
7. Дождитесь индексации (10-30 секунд)

`docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` — обновить статус Раздела 7 (Индексы) с уточнениями (теперь можем проверять что индекс существует для упомянутых полей? — Sprint 6 candidate).

`docs/CCH_FEATURE_PARITY_REFERENCE.md` — обновить статус Раздела 2.13.5 «Семантическая валидация» с 0% на 80%.

ADR'ы:
- **ADR-029** — Configuration metadata persistence в SQLite
- **ADR-030** — Парсинг XML выгрузки через стандартную Python библиотеку (без lxml)
- **ADR-031** — Semantic rules как extension существующего engine, не replacement
- **ADR-032** — Golden test suite формат (plain files + JSON)

`docs/SPRINT_5_REPORT.md` — closure report.
`docs/OPUS_HANDOVER_SPRINT_5.md` — handoff для Sprint 6 (включая placeholders `find_module_by_context` / `extract_sdbl_from_module` которые Sprint 6 будет реализовывать).

### DONE WHEN

| # | Criterion | Verification |
|---|---|---|
| 1 | Phase 0 — `docs/CONFIGURATION_XML_FORMAT_STUDY.md` создан | file exists |
| 2 | XML парсер работает на синтетических примерах | unit tests |
| 3 | XML парсер работает на real config (Test1CProf) | acceptance test |
| 4 | SQLite store работает: index/query/persistence | unit tests |
| 5 | Hash-based invalidation: переиндексация только при изменении папки | unit test |
| 6 | High-level API: `is_object_exists`, `get_attributes`, `get_dimensions`, `get_resources`, `search_similar_objects` | unit tests |
| 7 | Placeholders `find_module_by_context` / `extract_sdbl_from_module` есть в API (raise NotImplementedError) | code review |
| 8 | Минимум 8 semantic rules в `semantic_rules/rules/` | file count |
| 9 | Каждое semantic rule имеет positive + negative unit test | pytest |
| 10 | Semantic rules **silent** если config не подключён (не запускаются, не выдают false positive) | unit test |
| 11 | RPC методы `configuration.connect/status/disconnect` работают | integration tests |
| 12 | `query_analyzer.analyze` автоматически использует config store если подключён | integration test |
| 13 | Frontend ConfigurationBadge показывает статус в QueryAnalyzer | manual |
| 14 | Settings секция «Конфигурация 1С» позволяет подключить/отключить/переиндексировать | manual |
| 15 | Tauri folder picker работает (выбор папки) | manual |
| 16 | После переиндексации — toast уведомление | manual |
| 17 | Golden test suite: минимум 30 cases (10 positive + 10 negative + 10 edge cases) | file count |
| 18 | Golden test suite: 5+ semantic cases | file count |
| 19 | Pytest runner для golden suite работает (один collect, параметризованные tests) | pytest |
| 20 | `docs/CONFIGURATION_XML_FORMAT_STUDY.md` написан | file |
| 21 | `docs/CONNECTING_CONFIGURATION.md` написан | file |
| 22 | `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновлён | file diff |
| 23 | `docs/CCH_FEATURE_PARITY_REFERENCE.md` обновлён (Раздел 2.13.5) | file diff |
| 24 | ADR-029..032 written в DECISIONS.md | file |
| 25 | pytest суммарно ≥ 420 (Sprint 4 had 360, +60+ для config + semantic + golden) | CI |
| 26 | TypeScript build clean (0 errors) | CI |
| 27 | Conventional commits | git log |
| 28 | **ACCEPTANCE GATE:** Парсинг Test1CProf конфигурации < 30 секунд, ≥100 объектов | env-gated pytest |
| 29 | **ACCEPTANCE GATE:** Semantic rule срабатывает на запросе с несуществующим объектом | env-gated pytest |
| 30 | **ACCEPTANCE GATE:** Все golden cases проходят (30+ tests) | env-gated pytest |
| 31 | **ACCEPTANCE GATE:** Persistence работает (после restart tool — конфигурация остаётся подключённой) | env-gated pytest |
| 32 | **ACCEPTANCE GATE:** 7+ из 10 real-world запросов получают findings (Phase F) | env-gated pytest |
| 33 | SPRINT_5_REPORT.md + OPUS_HANDOVER_SPRINT_5.md written | files |

Пункты 28-32 — обязательные blocking gates. Sprint 5 не закрыт без них.

### VERIFY

- **pytest backend** — 420+ tests зелёные (включая Sprint 0-4 baseline + Sprint 5 add)
- **TypeScript build** — 0 errors
- **Manual smoke (`.\start.bat`):**
  - Открыть Settings → Конфигурация 1С → «Указать папку выгрузки» → выбрать `C:\BUFFER\SCHEME`
  - Дождаться toast «Конфигурация подключена»
  - Открыть QueryAnalyzer → в шапке badge «Конфигурация: БП 3.0 ✓»
  - Вставить запрос с `РегистрНакопления.ТоварыНаСкладах` (которого нет в БП)
  - Нажать «Анализировать»
  - Увидеть **semantic finding** «Регистр накопления `ТоварыНаСкладах` не существует в подключённой конфигурации» с предложением похожих объектов
  - В Settings нажать «Отключить» → badge меняется на «не подключена»
  - Прогнать тот же запрос → semantic finding **исчезает** (но performance findings остаются)
- **Регрессия Sprint 0-4** не сломана: все anatomy views работают, Query Analyzer работает с performance/correctness/style rules, AI rewriter работает

**Rollback plan:**

Если Sprint 5 ломает что-то в Sprint 4:
- `git revert <sprint5_merge_commit>` возвращает на `v0.4.0-internal`
- `data/config_metadata.db` можно удалить — пересоздаётся
- XML выгрузка пользователя не трогается (read-only)
- Frontend ConfigurationBadge изолирован — удаление не ломает QueryAnalyzer

### OUTPUT

После закрытия Sprint 5:

- Tag `v0.5.0-internal` на merge commit
- `docs/SPRINT_5_REPORT.md` с измеренными метриками (время индексации, количество semantic rules, golden suite size, real-world hit rate)
- `docs/CONFIGURATION_XML_FORMAT_STUDY.md` (Phase 0 deliverable)
- `docs/CONNECTING_CONFIGURATION.md` (user guide)
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновлён
- `docs/CCH_FEATURE_PARITY_REFERENCE.md` обновлён (раздел 2.13.5 → 80%)
- ADR-029..032
- `docs/OPUS_HANDOVER_SPRINT_5.md` для следующей сессии (Sprint 6 — DBMSSQL → Query Analyzer integration через Configuration Metadata)
- Sprint 5 commit history + merge tag

### STOP RULES

- **Phase 0 — критичный.** Если выяснится что XML выгрузка существенно отличается между типами объектов или версиями платформы — **остановиться и спросить через ranked options**: (a) парсить только основные типы (Документ/Справочник/Регистры) в Sprint 5, остальное — Sprint 6, (b) сделать generic парсер с base class + специализациями для каждого типа, (c) использовать внешнюю библиотеку.
- Если Phase A показывает что Test1CProf конфигурация содержит **сильно нестандартные кастомизации** (custom branches в стандартных типах) — фиксировать как known limitation, не блокировать Sprint 5.
- Если semantic rules выдают **слишком много false positives** на real запросах — итеративно tighten regex extractor; **не** отключать rules целиком.
- Останавливаться при неоднозначности high impact. Не выдумывать формат XML — читать реальные файлы из `C:\BUFFER\SCHEME`.
- Показывать ranked options (2-4 варианта), не задавать open-ended вопросы.
- Не расширять scope. Смежные задачи (DBMSSQL → Query Analyzer / Lock Wait Anatomy / continuous monitoring) → `OPUS_HANDOVER_SPRINT_5.md` как Sprint 6/7 кандидаты.
- No time estimates anywhere в reports/commits/docs.
- Light theme only (dark theme FORBIDDEN).
- Не модифицировать `design/opt/*.jsx`.
- Не модифицировать ADR-001..028 без явного указания архитектора.
- Destructive ops (новый `data/config_metadata.db`) → явно `CREATE TABLE IF NOT EXISTS`. Если formats меняется — bump version в meta таблице.
- Conventional commits обязательны.
- Real-data acceptance gates (DoD #28-32) — блокирующие условия закрытия Sprint 5.
- Anthropic API key — НИКОГДА в commits.
- Persistence: `data/config_metadata.db` — отдельный SQLite, не путать с `data/explainer_cache.db` (там query rewriter cache от Sprint 4).
- Semantic rules — **silent on missing metadata**. Не паниковать пользователя сообщениями «не могу проверить, подключите конфигурацию». Только глобальный badge статуса.
- Golden test suite — **plain files**. Никаких pickle/binary форматов. Любой человек должен мочь открыть и понять.
- Если в Phase F (real-world queries) Сергей не может найти оригинальный SDBL для какого-то DBMSSQL события — пропустить этот case, не блокировать сбор golden suite на нём.
- **Pivot rule:** если в Phase B оказывается что regex-based extractor SDBL объектов даёт <70% точность на real запросах — **остановиться и спросить архитектора через ranked options**: (a) написать простой SDBL tokenizer на pyparsing, (b) использовать 1c-syntax/bsl-parser (Java sidecar — возврат к идее Sprint 4 которую мы отвергли), (c) принимать 70% точность как baseline и улучшать в Sprint 6.

---

**Prepared by:** Claude Opus 4.7 (architect) **For:** Claude Code (Sprint 5 implementation)
