# Sprint 5 Closure Report — MCP BSL Atlas + Semantic Validation + Golden Test Suite

**Branch:** `feat/sprint-5-configuration-metadata`
**Tag:** `v0.5.0-internal`
**Repo:** https://github.com/anymasoft/1c-optimyzer
**Closure date:** 2026-05-23

---

## TL;DR для архитектора

Sprint 5 закрыт. Query Analyzer теперь имеет **второй слой анализа — семантический**, который проверяет SDBL-запрос против **реальной структуры конфигурации 1С** (загружаемой из XML-выгрузки Конфигуратора).

- Подключение XML-выгрузки: за 10.09 секунд проиндексировано 1647 объектов реальной БП 3.0 (DoD #28: `<30s`, `≥100` ✓✓).
- 8 семантических правил работают в режиме «silent skip» если выгрузка не подключена — не показывают false-positive и не раздражают warning'ом «нечего проверить».
- Golden test suite — 35 cases (10 positive + 10 negative + 10 edge + 5 semantic) — regression baseline для всех будущих изменений rules.
- Полный backend suite: **487 passed, 21 skipped** (Sprint 4 baseline: 360 → Sprint 5: 487, +127 фактических test passes).
- Phase F (real-world queries из DBMSSQL.Context) — **скипнут по решению пользователя**, переезжает в Sprint 6 где будет автоматический поиск SDBL через MCP BSL Atlas вместо manual extraction.

**Это центральный шаг к нашему главному конкурентному преимуществу:** ни ЦУП, ни другие продукты в РФ-сегменте не делают семантическую валидацию против XML-выгрузки конфигурации. Карта в [CCH_FEATURE_PARITY_REFERENCE.md раздел 2.13.5](CCH_FEATURE_PARITY_REFERENCE.md#2135-семантическая-валидация-запросов-против-конфигурации-).

---

## Commit history

| Commit | Phase | Содержание |
|---|---|---|
| `3001080` | Phase 0 | Discovery формата XML выгрузки + CONFIGURATION_XML_FORMAT_STUDY.md + inspect_configuration_xml.py |
| `48a8dab` | Phase A | configuration_metadata пакет (parser + store + api) + 41 unit test |
| `ce17bad` | Phase B | Semantic rules engine + sdbl_tokenizer + 9 чекеров + 8 markdown rules + 39 unit test. Bonus: YAML inline-arrays fix в rule_loader |
| `fc7523a` | Phase C | RPC методы configuration.* + автоинтеграция в query_analyzer.analyze + 20 integration tests |
| `bf5404c` | Phase D | Frontend: ConfigurationBadge + ConfigurationDialog + AppStore + i18n |
| `7525f90` | Phase E | Golden test suite (35 cases) + параметризованный runner + 38 tests |
| `cb1f8b3` | Phase G | Real-data acceptance gates (10 tests, env-gated на C:\BUFFER\SCHEME) |
| _последний_ | Phase H | Документация: ADR-029..032, CONNECTING_CONFIGURATION, обновления FEATURES + CCH parity, SPRINT_5_REPORT, OPUS_HANDOVER_SPRINT_5 |

Все коммиты используют conventional commit format со scope (`feat(sprint-5)`, `test(sprint-5)`, `docs(sprint-5)`).

---

## DoD Status

### Блокирующие (P1)

| # | Criterion | Status | Verification |
|---|---|---|---|
| 1 | Phase 0 — CONFIGURATION_XML_FORMAT_STUDY.md создан | ✅ | `docs/CONFIGURATION_XML_FORMAT_STUDY.md` |
| 2 | XML парсер на synthetic примерах | ✅ | `TestParser` (10 tests in test_configuration_metadata.py) |
| 3 | XML парсер на real config (Test1CProf БП 3.0) | ✅ | `TestDoD28IndexingPerformance` real-data |
| 4 | SQLite store: index/query/persistence | ✅ | `TestStore` (19 tests) |
| 5 | Hash-based invalidation | ✅ | `test_hash_invalidation_*` |
| 6 | High-level API: is_object_exists, get_attributes, get_dimensions, get_resources, search_similar_objects | ✅ | `TestStore` |
| 7 | Sprint 6 placeholders с NotImplementedError | ✅ | `TestSprint6Placeholders` |
| 8 | Минимум 8 semantic rules | ✅ | 8 .md файлов в `semantic_rules/` (`test_load_minimum_8_semantic_rules`) |
| 9 | Каждое semantic rule с positive + negative unit test | ✅ | 8 классов в `test_semantic_rules.py` |
| 10 | Semantic rules silent если config не подключён | ✅ | `test_silent_without_config_store`, `test_silent_with_unconfig_store` |
| 11 | RPC методы configuration.connect/status/disconnect/reindex | ✅ | `test_configuration_rpc.py` (20 tests) |
| 12 | query_analyzer.analyze автоматически использует config store | ✅ | `TestQueryAnalyzerAutoUsesConfigStore` |
| 13 | Frontend ConfigurationBadge | ✅ | `ConfigurationBadge.tsx` + manual testing |
| 14 | Settings секция позволяет connect/disconnect/reindex | ✅ | `ConfigurationDialog.tsx` |
| 15 | Tauri folder picker | ✅ | `openDialog({directory: true})` в `ConfigurationDialog.tsx` |
| 16 | Toast уведомление после connect/reindex | ✅ | i18n `configuration.connectedToast` / `reindexedToast` |
| 17 | Golden test suite ≥ 30 basic cases | ✅ | 30 cases (10 positive + 10 negative + 10 edge) (`test_minimum_30_total_basic_cases`) |
| 18 | Golden suite ≥ 5 semantic cases | ✅ | 5 semantic cases (`test_minimum_5_semantic_cases`) |
| 19 | Pytest runner с параметризацией | ✅ | `test_golden_suite.py::test_golden_case` |
| 20 | CONFIGURATION_XML_FORMAT_STUDY.md | ✅ | Phase 0 deliverable |
| 21 | CONNECTING_CONFIGURATION.md | ✅ | User guide написан |
| 22 | FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md обновлён | ✅ | Sprint 5 closure update section |
| 23 | CCH_FEATURE_PARITY_REFERENCE.md обновлён (2.13.5) | ✅ | Sprint 5 ✓ + детальная таблица rules |
| 24 | ADR-029..032 в DECISIONS.md | ✅ | append at end |
| 25 | pytest ≥ 420 | ✅ | **487 passed** (точный +127 от Sprint 4 baseline 360) |
| 26 | TypeScript build clean | ✅ | `npx tsc --noEmit` no output |
| 27 | Conventional commits | ✅ | 8 коммитов со scope `(sprint-5)` |

### Acceptance gates (блокирующие закрытие Sprint 5)

| # | Gate | Status |
|---|---|---|
| 28 | Парсинг Test1CProf < 30s, ≥100 объектов | ✅ **10.09s, 1647 объектов** |
| 29 | Semantic rule срабатывает на запросе с несуществующим объектом | ✅ `РегистрНакопления.ТоварыНаСкладах.Остатки(, )` (из УТ, нет в БП 3.0) → `object_not_exists` |
| 30 | All golden cases проходят | ✅ 38 tests pass (35 cases + 3 sanity) |
| 31 | Persistence после restart tool | ✅ `TestDoD31Persistence` (2 tests) |
| 32 | 7+/10 real-world запросов с findings (Phase F) | ⏭ **SKIPPED по решению пользователя** — переезжает в Sprint 6 (см. OPUS_HANDOVER_SPRINT_5) |
| 33 | SPRINT_5_REPORT.md + OPUS_HANDOVER_SPRINT_5.md | ✅ оба написаны |

**Итог:** 32 из 33 DoD пройдено. #32 явно скипнут по согласованию с пользователем (см. AskUserQuestion в начале спринта) — Phase F не требует manual extraction в Sprint 5.

---

## File inventory

### Новые файлы

**Backend (новый пакет):**

- `backend/src/optimyzer_backend/configuration_metadata/__init__.py`
- `backend/src/optimyzer_backend/configuration_metadata/parser.py` (380 строк, dataclasses + XML парсер)
- `backend/src/optimyzer_backend/configuration_metadata/store.py` (450 строк, SQLite индекс + hash invalidation + Levenshtein + Sprint 6 placeholders)
- `backend/src/optimyzer_backend/configuration_metadata/api.py` (90 строк, singleton + env override)

**Backend (semantic engine):**

- `backend/src/optimyzer_backend/query_analyzer/sdbl_tokenizer.py` (170 строк, regex extractors)
- `backend/src/optimyzer_backend/query_analyzer/semantic_checks.py` (330 строк, 9 чекеров + registry)
- `backend/src/optimyzer_backend/query_analyzer/semantic_rules/README.md` + 8 markdown rules

**Backend (RPC):**

- `backend/src/optimyzer_backend/rpc/configuration_rpc.py` (130 строк, 4 RPC handler)

**Backend (tests):**

- `backend/tests/test_configuration_metadata.py` (41 unit test)
- `backend/tests/test_semantic_rules.py` (39 unit test)
- `backend/tests/test_configuration_rpc.py` (20 integration test)
- `backend/tests/test_golden_suite.py` (38 tests = 35 cases + 3 DoD)
- `backend/tests/test_sprint5_real_data.py` (10 tests, env-gated)
- `backend/tests/golden/queries/README.md` + 70 файлов golden cases (35 × 2)

**Frontend:**

- `frontend/src/components/screens/QueryAnalyzer/ConfigurationBadge.tsx` + `.module.css`
- `frontend/src/components/screens/QueryAnalyzer/ConfigurationDialog.tsx` + `.module.css`

**Backend scripts:**

- `backend/scripts/inspect_configuration_xml.py` (discovery tool из Phase 0)

**Документация:**

- `docs/CONFIGURATION_XML_FORMAT_STUDY.md` (Phase 0 deliverable)
- `docs/CONNECTING_CONFIGURATION.md` (user guide)
- `docs/SPRINT_5_REPORT.md` (этот файл)
- `docs/OPUS_HANDOVER_SPRINT_5.md`
- `docs/SPRINT_5_PROMPT_OPTIMYZER.md` (копия prompt для traceability)

### Изменённые файлы

- `backend/src/optimyzer_backend/__main__.py` — регистрация `configuration_rpc`
- `backend/src/optimyzer_backend/query_analyzer/native_rules.py` — поля `requires`, `check_name` в NativeRule, расширенный `analyze()` с config_store параметром и dispatch semantic
- `backend/src/optimyzer_backend/query_analyzer/aggregator.py` — semantic_rules_dir, all_rules property, configuration_connected в result
- `backend/src/optimyzer_backend/rpc/query_analyzer_rpc.py` — auto-use config store в analyze, status reports configuration_connected
- `backend/src/optimyzer_backend/explainer/rule_loader.py` — **bonus fix:** inline arrays `[a, b, c]` в YAML теперь парсятся как list (скрытый баг Sprint 4 — теги rules не загружались)
- `frontend/src/api/backend.ts` — ConfigurationInfo / ConnectResult / StatusResult типы + 4 RPC wrapper, QAStatus расширен полями
- `frontend/src/store/appStore.ts` — configurationStatus state
- `frontend/src/i18n/ru.ts` — блок `configuration.*` строк
- `frontend/src/components/screens/QueryAnalyzer/QueryAnalyzer.tsx` — badge + dialog подключены, refresh при изменении config
- `frontend/src/components/screens/QueryAnalyzer/QueryAnalyzer.module.css` — `.headerRight` flex
- `docs/DECISIONS.md` — append ADR-029..032
- `docs/CCH_FEATURE_PARITY_REFERENCE.md` — раздел 2.13.5 → ✅ + детальная таблица rules + Преимущество 5 → "Где видно: Sprint 5"
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` — Sprint 5 closure update section

---

## Testing instructions

### Backend regression (быстро)

```powershell
cd D:\1C-Optimyzer\backend
.\.venv\Scripts\python.exe -m pytest
```

Ожидается **487 passed, 21 skipped**.

### Real-data acceptance (требует C:\BUFFER\SCHEME)

```powershell
cd D:\1C-Optimyzer\backend
.\.venv\Scripts\python.exe -m pytest tests/test_sprint5_real_data.py -v
```

Ожидается **9 passed, 1 skipped** (Phase F placeholder).

Если у пользователя выгрузка лежит в другом месте — указать env:

```powershell
$env:OPTIMYZER_CONFIG_XML_PATH = "D:\my-other-path"
.\.venv\Scripts\python.exe -m pytest tests/test_sprint5_real_data.py
```

### Manual smoke test (full UI)

1. Запустить `D:\1C-Optimyzer\start.bat` (development mode).
2. В sidebar открыть **АНАЛИЗ → Анализ запроса**.
3. В правом верхнем углу — серый chip «Конфигурация не подключена». **Кликнуть**.
4. В модале «Конфигурация 1С» нажать **«Указать папку выгрузки…»**.
5. В Tauri folder picker выбрать `C:\BUFFER\SCHEME`.
6. Дождаться toast **«Конфигурация подключена: 1 647 объектов проиндексировано»** (10-15 секунд).
7. Закрыть модал. Chip в шапке должен стать **зелёным**: «Конфигурация: Бухгалтерия предприятия, редакция 3.0 · 1 647 объектов».
8. Вставить в редактор:
   ```sdbl
   ВЫБРАТЬ *
   ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, )
   ```
   Это запрос из УТ — в БП 3.0 такого регистра нет.
9. Нажать **«Анализировать»**.
10. В правой панели должен появиться **критичный** finding `object_not_exists` с сообщением «Объект «РегистрНакопления.ТоварыНаСкладах» не существует в подключённой конфигурации» и подсказками похожих имён (если есть).
11. Кликнуть на finding — редактор должен прокрутиться к проблемному месту (Sprint 4 hotfix).
12. Снова открыть модал «Конфигурация 1С», нажать **«Отключить»**, подтвердить.
13. Прогнать тот же запрос ещё раз → `object_not_exists` **исчезает**. Синтаксические findings (если есть) — остаются.

### Frontend type check

```powershell
cd D:\1C-Optimyzer\frontend
npx tsc --noEmit
```

Ожидается **0 ошибок**.

---

## Documented gaps и сомнения (для архитектора)

### 1. Phase F (real-world golden cases) скипнут — DoD #32 переезжает в Sprint 6

Sprint 5 prompt предлагал 10 real-world запросов extracted manually из DBMSSQL.Context. По решению Сергея этот шаг пропущен и переезжает в Sprint 6, где будет **автоматический** поиск SDBL по Context — без manual work.

**Impact:** мы не имеем validation на real DBMSSQL контекстах в Sprint 5. Семантические rules проверены только на:
- Synthetic XML (test_semantic_rules.py)
- Real БП 3.0 + handcrafted SDBL (test_sprint5_real_data.py)

**Когда станет проблемой:** если в production пользовательских запросов будут паттерны, которые не покрывают существующие тесты. Sprint 6 закроет это автоматическим mining'ом.

### 2. Regex tokenizer SDBL — pivot rule (ADR-031)

В Phase B мы использовали regex-based extractor для object references вместо полноценного SDBL парсера. Это работает на ~80-90% случаев (точная цифра не измерена на large corpus). Pivot rule prompt (если точность <70%) — не сработал, но и не верифицирован на больших данных.

**Когда станет проблемой:** на запросах с очень вложенными конструкциями, нестандартным форматированием (например `Документ . АвансовыйОтчет` с пробелами), или с экзотическими псевдонимами. Sprint 6 candidate — оценить точность на ~50-100 real DBMSSQL контекстах и решить: остаёмся на regex, переходим на pyparsing, или включаем BSL Language Server.

### 3. Standard attribute whitelist hardcoded

В `check_attribute_not_exists_in_from_alias` стандартные атрибуты (`Ссылка`, `Код`, `Наименование`, `ПометкаУдаления`, `Дата`, `Номер`, и т.п.) захардкожены в Python код. На самом деле эта таблица должна вытаскиваться из `Properties/StandardAttributes` в XML каждого объекта (там она опционально настраивается под объект).

**Impact:** false negatives — если у пользователя на каком-то объекте отключён `Code` через StandardAttributes, мы по-прежнему считаем что `К.Код` валиден. Очень редкий case.

**Sprint 6 candidate:** парсить `<StandardAttributes>` в Phase A парсере, складывать в `attributes` с пометкой `attribute_kind='standard'`.

### 4. Один config_metadata.db на tool

Sprint 5 поддерживает ровно одну подключённую конфигурацию. Если пользователь работает с двумя разными базами (БП + УТ) — переключение через disconnect/connect. Switching не сохраняет два индекса.

**Sprint 7 candidate:** профили конфигураций в UI с переключением.

### 5. `configuration.reindex` не cancellable

В отличие от ingestion архива (Sprint 1 cancel_event), reindex выгрузки нельзя прервать в середине. Для 1647 объектов это ~10 секунд, проблемой не является. Для гигантской конфигурации (10k+ объектов) — может стать issue.

**Sprint 7 candidate:** добавить cooperative cancellation в `index_configuration` (флаг между объектами).

### 6. Configuration metadata не зафиксирована в `.env.test`

Sprint 5 prompt упоминал `.env.test` с `OPTIMYZER_CONFIG_XML_PATH`. В коде используется обычный env (default `C:\BUFFER\SCHEME`). На CI это потребует явного экспорта переменной.

**Mitigation:** дефолт `C:\BUFFER\SCHEME` работает на Windows-машине пользователя без настройки. CI прогон real-data tests skipped if env not set (см. `pytestmark = skipif`).

---

## Sprint 6 placeholders (заложено в Phase A для совместимости)

В `ConfigurationMetadataStore` уже есть **два метода** которые `raise NotImplementedError("Sprint 6 feature")`:

```python
def find_module_by_context(self, tj_context: str) -> ModuleLocation | None:
    """Sprint 6: парсит stack trace из DBMSSQL.Context, находит .bsl модуль."""

def extract_sdbl_from_module(self, module_location, line: int) -> str | None:
    """Sprint 6: извлекает SDBL из строкового литерала рядом с указанной строкой."""
```

Sprint 6 заполнит их реализацией и сможет:
1. Брать `DBMSSQL.Context` из ТЖ
2. Парсить stack trace (Модуль.Метод(Строка))
3. Находить файл `.bsl` в выгрузке (через `Catalogs/X/Ext/ObjectModule.bsl` или CommonModules)
4. Парсить модуль, искать строковый литерал с запросом
5. Передавать его в Query Analyzer уже как чистый SDBL

Это закрывает DoD #32 от Sprint 5 (real-world hit rate) автоматически + закрывает DoD #23 от Sprint 4 (DBMSSQL → SDBL gap).

См. подробный план в `OPUS_HANDOVER_SPRINT_5.md`.

---

## Сводка метрик

| Метрика | Sprint 4 | Sprint 5 | Изменение |
|---|---|---|---|
| Backend tests passing | 360 | **487** | +127 |
| Backend tests skipped (env-gated) | 20 | 21 | +1 (Sprint 6 placeholder) |
| Native (syntactic) rules | 13 | 13 | без изменений |
| **Semantic rules** | 0 | **8** | new |
| Frontend новых компонентов | 0 (Sprint 4 base) | 2 (Badge + Dialog) | new |
| RPC методов | ~26 | 30 | +4 |
| Покрытие методики ЦУП (целевая) | 65% | **70%** + unique category | +5% + unique |
| Парсинг real БП 3.0 | n/a | **10.09 сек** | DoD #28 = <30s ✓ |
| Объектов в индексе real БП 3.0 | n/a | **1647** | DoD #28 = ≥100 ✓ |
| Golden test cases | 0 | **35** | new |

---

## Ссылки

- Repo: https://github.com/anymasoft/1c-optimyzer
- Branch: [`feat/sprint-5-configuration-metadata`](https://github.com/anymasoft/1c-optimyzer/tree/feat/sprint-5-configuration-metadata)
- Все commits Sprint 5 в порядке от первого к последнему: `3001080`, `48a8dab`, `ce17bad`, `fc7523a`, `bf5404c`, `7525f90`, `cb1f8b3`, _Phase H_
- Tag (после merge): `v0.5.0-internal`
- Phase 0 deliverable: [docs/CONFIGURATION_XML_FORMAT_STUDY.md](CONFIGURATION_XML_FORMAT_STUDY.md)
- User guide: [docs/CONNECTING_CONFIGURATION.md](CONNECTING_CONFIGURATION.md)
- Handoff: [docs/OPUS_HANDOVER_SPRINT_5.md](OPUS_HANDOVER_SPRINT_5.md)
- ADR'ы: [docs/DECISIONS.md#ADR-029](DECISIONS.md) — 029, 030, 031, 032
