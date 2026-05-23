# Opus Handover — Sprint 5 → Sprint 6

**Prepared by:** Claude Code (Sprint 5 implementation)
**For:** Claude Opus 4.7 (architect) перед написанием SPRINT_6_PROMPT
**Sprint 5 state:** Closed, tag `v0.5.0-internal` (после merge).

---

## State of the codebase

### Что работает после Sprint 5

1. **Query Analyzer (Sprint 4)** — синтаксическая проверка SDBL по 13 native rules, AI rewriter через Claude Sonnet, frontend с CodeMirror и подсветкой findings.
2. **Configuration Metadata (Sprint 5)** — подключение XML-выгрузки конфигурации 1С (через Конфигуратор), SQLite индекс с hash-based invalidation, парсинг 1647 объектов БП 3.0 за ~10 секунд.
3. **Semantic rules (Sprint 5)** — 8 семантических правил, которые проверяют запрос против реальной структуры конфигурации (object_not_exists, attribute_not_exists, virtual_table_not_supported, и т.д.). Silent skip без подключённой конфигурации.
4. **Frontend ConfigurationBadge + Dialog (Sprint 5)** — UI для подключения/отключения/переиндексации, Tauri folder picker, тосты.
5. **Golden test suite (Sprint 5)** — 35 эталонных запросов в `backend/tests/golden/queries/`, параметризованный pytest runner. Regression baseline.

### Что НЕ работает (но запланировано)

- **DBMSSQL → Query Analyzer integration.** Sprint 4 known gap (DoD #23): в архиве ТЖ поле `DBMSSQL.Sql` содержит T-SQL после трансляции платформой, не оригинальный SDBL. Пользователь не может прямо проанализировать SQL из лога — нужно вручную найти исходник в коде модуля. **Sprint 6 закрывает этот gap.**
- **Real-world golden cases (Phase F).** В Sprint 5 скипнуто по решению пользователя — переезжает в Sprint 6 (автоматический extraction).
- **Lock Wait Anatomy** — отдельный view (Sprint 7+ candidate).
- **Continuous monitoring** — раздел 7 roadmap, не Sprint 6.

---

## MANDATORY Sprint 6 requirement: видимость T-SQL ↔ 1С-запрос

**Источник:** прямой запрос пользователя (Сергей, 2026-05-23 после Sprint 5 testing):
> «Надо, чтобы юзер видел SQL, и понимал, с каким 1С запросом он связан. Один юзер собирает одни события в ТЖ, другой — другие; если есть возможность получить нужные данные — получаем, если нет — обходимся без них.»

Это **обязательное** требование Sprint 6, не «было бы хорошо».

### Бизнес-проблема

Сейчас в Top SQL / Slow Queries / Anatomy юзер видит только нормализованный T-SQL вида `SELECT _IDRRef FROM dbo._Reference42 WHERE _Description LIKE ?`. Технически правильно, но **не actionable** — невозможно сопоставить с реальным запросом в коде 1С (`ВЫБРАТЬ Ссылка ИЗ Справочник.Контрагенты ГДЕ Наименование ПОДОБНО &Имя`). Юзер не знает где в коде искать, а имена таблиц (`_Reference42`) ничего не говорят.

### Технический контекст: два пути в ТЖ

В платформе 1С связь T-SQL ↔ исходный 1С-запрос восстановима **двумя способами**:

**Путь 1 — SDBL event (полный, точный).** Если в `logcfg.xml` включён `<event>SDBL</event>`, платформа на каждый 1С-запрос пишет отдельное событие, идущее **прямо перед** DBMSSQL (миллисекунды разница). Содержит исходный SDBL текст. Корреляция по `(SessionID, OSThread, t:clientID, dbpid)` + time-window даёт **100% точное** сопоставление.

Цена для пользователя: ТЖ растёт ~1.5–2× по объёму. Многие админы SDBL не включают именно поэтому.

**Путь 2 — DBMSSQL.Context + поиск в модуле (эвристика).** В DBMSSQL событии всегда есть поле `Context` — путь вызова в 1С-коде, например:
```
ВнешняяОбработка.StandardDocumentsPosting.Форма.MainForm.Модуль.DoPortionPostAtServer(247)
```
Из этого можно найти `.bsl` файл, распарсить метод, извлечь все литералы `Запрос.Текст = "..."`. Точность не 100% — в одном методе бывает 3-10 запросов, и без AST/runtime сложно сказать какой именно соответствует данному T-SQL. Можно показать candidates с ranking по similarity (имена таблиц/полей).

**Путь 3 (reverse-translation T-SQL → SDBL) — НЕ ДЕЛАЕМ.** По решению пользователя глубокий reverse engineering вне scope (месяцы работы, теряется информация при некоторых трансляциях).

### Policy: graceful degradation

Sprint 6 реализует **оба пути** с приоритетом:
1. Если в архиве есть SDBL events → парсим, склеиваем с DBMSSQL → показываем **точный SDBL** (badge «exact, from SDBL event»).
2. Если SDBL events нет → используем Context + парсинг модуля → показываем **candidates** из метода (badge «approximate, from module»), с предупреждением и кнопкой «уточнить» (открыть модуль в редакторе).
3. Если ничего не получилось (нет Context, или модуль не найден в подключённой конфигурации, или метод вообще без литералов запросов) → показываем только T-SQL с пометкой «не удалось связать с 1С-кодом — для точной связки включите SDBL events в logcfg.xml».

В UI пользователь видит **один и тот же expand-блок** в Top SQL / Slow Queries / Anatomy.Top SQL:
```
T-SQL: SELECT _IDRRef FROM dbo._Reference42 ...
─────────────────────────────────────────────────
1С-запрос [exact / approximate / unavailable]:
  ВЫБРАТЬ Ссылка ИЗ Справочник.Контрагенты ...

Источник: ВнешняяОбработка.StandardDocumentsPosting.Форма.MainForm.Модуль:247
[ Открыть в Анализе запроса ]   [ Что включить в logcfg для точной связки ]
```

### Что нужно сделать в Sprint 6

1. **SDBL event parsing.** Расширить `tj_parser.py` — interpret `SDBL` события (сейчас они проходят как generic event без specialized fields). Сохранить `sdbl_text`, `sdbl_hash` в `events` table (или отдельную `sdbl_events` если архитектор решит).
2. **Correlation engine.** Новый модуль (например `backend/src/optimyzer_backend/sql/sdbl_correlation.py`) — для каждого DBMSSQL события ищет ближайший SDBL event по `(SessionID, OSThread, dbpid)` + time-window (например ±50 ms). Сохраняет связь в `dbmssql_sdbl_links` или в дополнительную колонку DBMSSQL.
3. **Context-based fallback** (тот самый Phase F из Sprint 5 + `find_module_by_context` + `extract_sdbl_from_module` placeholders — наполнить реализацией).
4. **RPC + frontend.** Метод `query.get_source_query(archive_id, dbmssql_event_id)` возвращает `{kind: "exact"|"approximate"|"unavailable", sdbl: str|null, candidates: list, source: ModuleLocation|null}`. В Top SQL / Slow Queries / Anatomy в expand-row показывать блок «1С-запрос».
5. **Onboarding hint.** Если в архиве нет ни одного SDBL event — в Top SQL / Slow Queries показать ненавязчивый banner «для точной связки T-SQL с 1С-кодом включите SDBL events в logcfg.xml», с примером XML-секции и кнопкой «не показывать».

### Acceptance gate

- Архив с включёнными SDBL events: ≥ 95% top-100 DBMSSQL событий получают exact SDBL.
- Архив без SDBL events (только Context): ≥ 60% top-100 DBMSSQL получают хотя бы 1 candidate (approximate). 40% «unavailable» — приемлемо как known limitation.
- Banner про logcfg показывается **только** когда в архиве нет ни одного SDBL event, и dismissible.

### Что Sprint 6 НЕ делает

- Не пишет reverse-translator T-SQL → SDBL.
- Не модифицирует logcfg.xml у пользователя автоматически.
- Не пытается матчить кандидатов через AST 1С-кода (только regex на `"..."` литералы в методе) — точность улучшается в Sprint 7+.
- Не запускает `1cv8c.exe` для трассировки SDBL.

---

## Sprint 6 кандидат — DBMSSQL → Query Analyzer integration

Это **главная нерешённая задача после Sprint 5** и **прямое продолжение** ADR-025 (pivot на native-only) + Sprint 4 DoD #23 + Sprint 5 DoD #32.

### Бизнес-цель

Пользователь открывает архив ТЖ → видит топ-N медленных DBMSSQL событий → **кликает на событие** → Optimyzer находит соответствующий SDBL в коде модуля → передаёт в Query Analyzer → пользователь видит findings и AI rewrite.

Сейчас этот flow обрывается на шаге «найти SDBL по DBMSSQL.Context». Sprint 6 закрывает это через два ключевых метода в `ConfigurationMetadataStore`:

```python
# Sprint 6 — заполнить placeholders которые УЖЕ ЕСТЬ в API
def find_module_by_context(self, tj_context: str) -> ModuleLocation | None:
    """Парсит stack trace из DBMSSQL.Context (типичный формат):
       'Документ.АвансовыйОтчет.Модуль(15)' или
       'ОбщийМодуль.РасчетСебестоимости.ВыполнитьРасчет(247)'
       Возвращает ссылку на .bsl файл и номер строки."""

def extract_sdbl_from_module(self, module_location, line: int) -> str | None:
    """Открывает .bsl файл по module_location, ищет строковый литерал
       вокруг указанной строки, извлекает текст SDBL запроса."""
```

### Архитектурная подготовка УЖЕ есть

В Sprint 5 в `ConfigurationMetadataStore` (`backend/src/optimyzer_backend/configuration_metadata/store.py`) эти два метода raise NotImplementedError с пометкой «Sprint 6 feature». **API контракт зафиксирован** — Sprint 6 не пересматривает интерфейс, только заполняет реализацию.

### Что нужно решить архитектору

1. **Где лежат .bsl файлы?** В выгрузке конфигурации:
   - `Catalogs/X/Ext/ObjectModule.bsl` — модуль объекта справочника
   - `Catalogs/X/Ext/ManagerModule.bsl` — модуль менеджера
   - `Catalogs/X/Forms/Y/Ext/Form/Module.bsl` — модуль формы
   - `CommonModules/X/Ext/Module.bsl` — общий модуль
   - И т.д.

   Sprint 6 должен составить mapping `Тип.ИмяОбъекта.МодульИмя` → файл `.bsl`.

2. **Парсинг stack trace.** Типичный `DBMSSQL.Context` от 1С:
   ```
   Документ.АвансовыйОтчет.МодульОбъекта.ПриЗаписи(15)
   ОбщийМодуль.РасчетСебестоимости.ВыполнитьРасчет(247)
   Форма.Документ.АвансовыйОтчет.ФормаДокумента.Команда1.Обработчик(82)
   ```
   Нужен парсер для всех типичных форматов.

3. **Извлечение SDBL литерала.** В коде 1С запросы обычно:
   ```bsl
   Запрос.Текст =
   "ВЫБРАТЬ
   |   *
   |ИЗ Справочник.Контрагенты";
   ```
   То есть многострочные literals с `|`-конкатенацией. Парсер должен собрать всё и убрать `|` (pipe = новая строка в SDBL).

   Альтернативные форматы: `"" + строка1 + "" строка2`, использование `СтрШаблон`, и т.д. Sprint 6 может start со standard `"..."` literals и расширяться по мере накопления test cases.

4. **70% точность hit-rate** — DoD #32 от Sprint 5 переезжает: 7+/10 real DBMSSQL событий должны находить SDBL и получать findings.

### Что Phase F (manual extraction) перестаёт быть нужной

В Sprint 5 prompt Phase F требовала: «Сергей вручную находит оригинальный SDBL в Конфигураторе для 10 событий и сохраняет как golden cases». Это много ручной работы и скучно.

Sprint 6 заменяет это **automatic mining**: backend сам ходит по топ-N DBMSSQL событий, извлекает SDBL через `find_module_by_context` + `extract_sdbl_from_module`, складывает в `tests/golden/queries/real_world/`. Сергей **review** findings (правильно ли извлечён SDBL? правильные ли findings?), accept/reject. Это в 10 раз быстрее.

---

## Sprint 6 backlog (другие кандидаты, не обязательны вместе с DBMSSQL integration)

### Кандидат B — расширить semantic rules

Текущие 8 rules — это minimum для Sprint 5. Можно добавить:

- `cross_database_object` — обращение к объекту через `ВнешнийИсточникДанных.X` (Sprint 5 не покрывает)
- `parameter_type_mismatch` — `&Параметр` указан как Число, а используется в `Ссылка = &Параметр` — нужно ВЫРАЗИТЬ
- `joinkey_type_mismatch` — `ВНУТРЕННЕЕ СОЕДИНЕНИЕ ... ПО А.Поле = Б.Поле` где Поле разных типов
- `tabular_section_attribute_missing` — `Документ.Х.ТабчастьN.НесуществующийРеквизит` (сейчас не покрывается)
- `composite_type_member_missing` — для определяемых типов

Каждое — отдельный markdown rule + чекер. Не требует архитектурных изменений.

### Кандидат C — standard attribute parser

Сейчас стандартные атрибуты захардкожены в `semantic_checks.py`. Sprint 6 может парсить `<Properties/StandardAttributes>` секцию из XML каждого объекта и складывать в БД как `attribute_kind='standard'`. Это устраняет false negatives когда стандартный атрибут отключён в конфигурации.

### Кандидат D — profile конфигураций

Если пользователь работает с двумя базами (БП + УТ), сейчас приходится переключаться через disconnect/connect. Sprint 6 может ввести список профилей в UI: «БП 3.0 v3.0.39.57» и «УТ 11.5» — оба сохраняются как разные `config_metadata_*.db`, переключение через dropdown.

### Кандидат E — symptoms landing screen

См. CCH_FEATURE_PARITY_REFERENCE.md раздел 2.11.2 — у ЦУПа есть landing с 5 симптомами производительности. У нас сейчас нет — пользователь сразу попадает в SQL Console / Анатомию. Это psychological UX gap. Sprint 7 candidate, но если SPRINT_6_PROMPT окажется лёгким — можно подтянуть.

---

## Известные технические долги (после Sprint 5)

| Долг | Impact | Priority |
|---|---|---|
| Standard attributes hardcoded в Python | False negatives на edited StandardAttributes | Low (редкий case) |
| `configuration.reindex` не cancellable | UX issue на огромных конфигурациях | Low (10-секундный re-index на БП 3.0) |
| Один config_metadata.db на tool | Switching между базами требует disconnect/connect | Low (mvp use case) |
| Regex tokenizer SDBL не точен на 100% | False negatives на нестандартных запросах | Medium — нужна оценка на real corpus |
| `OPTIMYZER_CONFIG_XML_PATH` в env, не в `.env.test` | CI setup чуть-чуть messy | Low |
| Sprint 4 hotfix scroll-to-finding — flash decoration через setTimeout (не cancellable если view destroyed) | Minor memory leak на edge case | Low (cleanup есть в `useEffect` return) |
| ~~`normalize_sql` оставлял `N?` от Unicode-литералов и не нормализовал hex (`0x01`)~~ | ~~Визуальный мусор в Top SQL / Slow Queries~~ | ~~Closed в commit d9b6530~~ (расширены regex `[Nn]?'...'` и `0[xX][0-9a-fA-F]+`) |
| `normalize_sql` не покрыт unit-tests | Регрессия может проскочить незаметно | Medium — добавить test suite в Sprint 6 |

---

## Состояние внешних зависимостей

- **Anthropic API** — работает, ключ в `.env` ANTHROPIC_API_KEY (грузинский биллинг). Sprint 4 hotfix поднял timeout с 15s до 30s.
- **DuckDB** — Sprint 0-3 storage. Не трогали в Sprint 5.
- **SQLite** — Sprint 3 cache + Sprint 4 query rewriter cache (`data/explainer_cache.db`) + **Sprint 5 config metadata (`data/config_metadata.db`)** — три отдельных файла, не путаются.
- **Tauri 2** — frontend, plugin-dialog для folder picker. Без изменений в Sprint 5.
- **BSL Language Server** — НЕ используется (ADR-025), stub остаётся в `bsl_ls_client.py` для будущего optional integration.
- **lxml / xmltodict** — НЕ используется (ADR-030), только `xml.etree.ElementTree`.

---

## Сводка для SPRINT_6_PROMPT_OPTIMYZER.md

Если архитектор будет писать prompt для Sprint 6, рекомендую структуру:

### Главная цель Sprint 6

**Closure DoD #23 от Sprint 4 + DoD #32 от Sprint 5 = DBMSSQL → Query Analyzer integration.**

### Phase plan (proposal)

Порядок отражает graceful-degradation policy из MANDATORY раздела выше:
сначала строим **точный** путь (SDBL events), потом **fallback** (Context →
модуль), потом UI/acceptance.

1. **Phase 0** — Discovery: формат `SDBL` events в ТЖ (поля Sdbl, Context, correlation keys) + формат `DBMSSQL.Context` (stack trace patterns) + структура `.bsl` в выгрузке.
2. **Phase A** — SDBL events parsing: `tj_parser.py` interpret `SDBL` event → `sdbl_text` / `sdbl_hash` в `events` (или отдельной таблице).
3. **Phase B** — Correlation engine: `sdbl_correlation.py` — для каждого DBMSSQL ищет ближайший SDBL по `(SessionID, OSThread, dbpid)` + time-window ±50 ms. Сохраняет linkage.
4. **Phase C** — Context-based fallback: `ConfigurationMetadataStore.find_module_by_context()` + parser stack trace + mapping `Тип.Объект.Модуль` → `.bsl` файл (placeholder из Sprint 5 уже есть).
5. **Phase D** — `extract_sdbl_from_module()` — извлечение строкового литерала. Поддержать минимум `"...|...|..."` многострочный формат. Возвращает list candidates с ranking по similarity к T-SQL.
6. **Phase E** — Integration RPC: `query.get_source_query(archive_id, event_id)` → `{kind: "exact"|"approximate"|"unavailable", sdbl, candidates, source}`. Используется в Top SQL / Slow Queries / Anatomy.
7. **Phase F** — Frontend: блок «1С-запрос» в expand-row Top SQL / Slow Queries / Anatomy.Top SQL. Banner «включите SDBL events» когда в архиве 0 SDBL events. Кнопка «Анализировать запрос» открывает QueryAnalyzer.
8. **Phase G** — Automatic golden mining: backend ходит по топ-N DBMSSQL событий и складывает в `tests/golden/queries/real_world/` (заменяет manual Phase F из Sprint 5).
9. **Phase H** — Acceptance gate: оба пути (см. MANDATORY раздел).
10. **Phase I** — Документация + ADR-033..037.

### Что НЕ нужно в Sprint 6

- Не парсить ВСЕ форматы строковых литералов (только typical `"..."`-style многострочные + конкатенация через `+`).
- Не работать с runtime 1С (только static XML выгрузка + текст модулей + ТЖ архив).
- Не запускать `1cv8c.exe` или Конфигуратор.
- Не модифицировать существующие 8 semantic rules.
- Не писать reverse-translator T-SQL → SDBL (explicitly out of scope per user decision).
- Не модифицировать logcfg.xml у пользователя автоматически — только показать hint.

### Stop rules

- Если формат `DBMSSQL.Context` сильно нестандартный — пометить как known limitation, не блокировать.
- Если в `.bsl` файле SDBL извлечь не получилось (динамическая конкатенация / СтрШаблон / сложная подстановка) — skip event, помечать как `kind: "unavailable"`, не падать.
- Если SDBL events есть, но correlation не находит match (time-window не сработал на ровно этом DBMSSQL) — fallback на Context-путь.

---

## Контакты и материалы

- **Sprint 5 report:** [`docs/SPRINT_5_REPORT.md`](SPRINT_5_REPORT.md)
- **Discovery doc Sprint 5:** [`docs/CONFIGURATION_XML_FORMAT_STUDY.md`](CONFIGURATION_XML_FORMAT_STUDY.md)
- **User guide:** [`docs/CONNECTING_CONFIGURATION.md`](CONNECTING_CONFIGURATION.md)
- **ADR-029..032:** [`docs/DECISIONS.md`](DECISIONS.md) (в конце файла)
- **Repo:** https://github.com/anymasoft/1c-optimyzer
- **Branch Sprint 5:** `feat/sprint-5-configuration-metadata` (merged в main как `v0.5.0-internal`)

---

**Prepared with care for the next architect cycle.**
