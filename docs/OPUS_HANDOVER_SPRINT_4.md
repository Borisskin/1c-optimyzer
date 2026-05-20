# Opus handover after Sprint 4 closure

**Передача:** Claude Code (Sprint 4 implementation) → Claude Opus 4.7 (architect, Sprint 5+ planning).
**Дата:** 2026-05-20.
**Tag:** `v0.4.0-internal`.

---

## Sprint 4 был about

Query Analyzer — paste & analyze экран для SDBL-запросов 1С. Native rule engine (13 правил методики ЦУП 2.13.4) + AI rewriter через Claude Sonnet 4.6. **Pivot** на native-only вместо BSL Language Server — см. ADR-025 и [`docs/BSL_LS_GAP_ANALYSIS.md`](BSL_LS_GAP_ANALYSIS.md).

Полный отчёт: [`docs/SPRINT_4_REPORT.md`](SPRINT_4_REPORT.md).

## Что строго НЕ закрыто и принципиально требует Sprint 5+

### 1. **DoD #23 — hit-rate 70% на real DBMSSQL events**

**Проблема:** реальные DBMSSQL события в архиве содержат **T-SQL** (после трансляции платформой 1С), не SDBL. Наши native rules матчат русские ключевые слова — на T-SQL они не срабатывают.

**Решение Sprint 5+ кандидаты:**

- **A.** Извлекать оригинальный SDBL из 1С stack — событие DBMSSQL имеет `Context` который содержит модуль конфигурации. Через MCP BSL Atlas (Sprint 7) можно найти `Запрос.Текст = "..."` в коде и проанализировать его.
- **B.** Transliterate T-SQL → SDBL — сложно, ненадёжно, бесполезно для рекомендаций (имена таблиц T-SQL это `_AccumRgT5634`, не `РегистрНакопления.ТоварыНаСкладах`).
- **C.** Альтернативный source — пользователь руками копирует SQL из 1С Performance Console / SQL Profiler. Это уже работает в Sprint 4 (paste & analyze), нужно только UX-навигация: «увидел DBMSSQL событие в Errors Feed → кликни → SDBL подставляется в Query Analyzer».

**Рекомендация Opus:** Sprint 5 = вариант **C** (UX-навигация между screens) + scope под Sprint 7 = вариант **A** (MCP BSL Atlas).

### 2. **Scroll-to-finding** при клике в FindingsList

Сейчас селект карточки только подсвечивает её, в редакторе ничего не происходит. Нужно `view.dispatch({ effects: EditorView.scrollIntoView(...) })` или эквивалент. Минимальная работа.

### 3. **Custom SDBL highlighter** в CodeMirror

Сейчас используется generic `@codemirror/lang-sql` — русские ключевые слова не подсвечиваются как keywords. Не блокирует функциональность, но качество UX страдает. Reference: [@codemirror/lang-sql custom dialect API](https://codemirror.net/docs/ref/#lang-sql).

### 4. **Ctrl+Q keyboard shortcut**

Sprint 4 promt просил Ctrl+Q. Не реализовано потому что Ctrl+1..9 уже заняты. Можно добавить как Ctrl+Shift+Q или через CommandPalette.

---

## Архитектурные решения Sprint 4 которые **зарезервированы** под Sprint 5+

### `BSLLanguageServerClient` stub

Файл `backend/src/optimyzer_backend/query_analyzer/bsl_ls_client.py` — thin stub. API контракт зарезервирован. Если Sprint 5+ решит интегрировать BSL LS (например, для анализа полных `.bsl` модулей конфигурации с embedded запросами через MCP) — нужно:

1. Установить Java 11+ на user-side, скачать `.jar`
2. В `bsl_ls_client.py.__init__` снять hard-disable, реализовать subprocess invocation
3. Парсить JSON output → `BSLDiagnostic`
4. `Aggregator._merge_and_dedupe` уже умеет приоритизировать native над BSL LS — менять не надо
5. `frontend/i18n/ru.ts.queryAnalyzer.bslLsBanner` поменять / убрать

### `SolutionGenerator` placeholder

Файл `backend/src/optimyzer_backend/query_analyzer/solution_generator.py` — всегда 501. Sprint 8 включит при готовности MCP BSL Atlas:

1. Снять `enabled = False`
2. Реализовать `generate_solution(finding_id, base_context)` через Claude API + MCP context
3. Frontend `FindingsList.tsx` добавить кнопку «Сгенерировать решение» условно (если status.solution_gen_enabled)

`Finding.solution_template_id: str | None` — placeholder поле в dataclass, не используется в Sprint 4.

### `query_rewrite_cache` table

В `data/explainer_cache.db` добавлена отдельная таблица (idempotent CREATE IF NOT EXISTS). Не пересекается с Sprint 3 `explainer_cache`.

---

## Что я сделал из изменений общего кода (не только новый код)

### `claude_client.py._load_dotenv_once` — override empty values

**Изменение:**
```python
# Было:
if key and key not in os.environ:
    os.environ[key] = value
# Стало:
if key and not os.environ.get(key):  # not present or empty
    os.environ[key] = value
```

**Зачем:** Windows / Claude Code env иногда устанавливает `ANTHROPIC_API_KEY=""` (пустая строка). Старая логика не загружала .env потому что считала что переменная "уже есть". Новая логика грузит .env если значение пустое.

**Побочный эффект:** Sprint 3 `test_claude_client_live_generation` теперь запускается чаще (раньше скипался когда env=""). Тест иногда таймаутится (15 сек таймаут на Claude API call). Это **flaky** — не блокирует Sprint 4, но **рекомендация: поднять `DEFAULT_TIMEOUT_S` в `claude_client.py` с 15 → 30 сек.**

### `frontend/src/api/backend.ts` — +types & RPC wrappers для Sprint 4

Добавлены: `QAFinding`, `QAAnalyzeResult`, `QARewriteChange`, `QARewriteResult`, `QAStatus` + 4 RPC методы.

### `frontend/src/i18n/ru.ts.queryAnalyzer.*` block

Полный набор UI strings для нового screen. Совместимый с существующим pattern.

### `frontend/src/components/chrome/nav.ts`, `App.tsx`, `store/appStore.ts`

Минимальные изменения для регистрации нового screen `"query-analyzer"`.

---

## Покрытие методики курса 1С:Эксперт после Sprint 4

| Раздел курса | Sprint 3 | Sprint 4 | Δ |
|---|---|---|---|
| Раздел 10 (Запросы которые работают быстро) | 0% | **85%** | +85pp |
| Раздел 7 (Индексы) | 0% | **60%** | +60pp |
| Раздел 8 (Анализ плана запроса) | 0% | **40%** | +40pp |
| Общее | ~30% | **~40%** | +10pp |

Цель Module 1 — 40-45%. Sprint 5+ должен добить остаток через:
- Раздел 8 — EXPLAIN integration (Sprint 7 кандидат через MCP-1c)
- Раздел 7 — Index recommendation engine (Sprint 5-6)
- Раздел 11 — Реструктуризация конфигурации (Sprint 7-8)
- Раздел 13 — Параллельность работы (уже на 75% — Sprint 5 может добить)

---

## Roadmap для Sprint 5 (рекомендация Opus)

**Tentative title:** Sprint 5 — Query Analyzer integration with archive + Index recommendations

**P1:**

1. **Errors Feed → Query Analyzer navigation** — кликаешь на DBMSSQL событие → SDBL подставляется в Query Analyzer. Минимальная работа: extract SDBL from `Context` если оно содержит `Запрос.Текст = "..."`, иначе показывать T-SQL и предупреждать что rules не сработают.
2. **Index recommendation engine** — простой эвристический анализ: какие колонки фигурируют в `ГДЕ` / `СОЕДИНЕНИЕ` / `УПОРЯДОЧИТЬ ПО` для топ-10 самых медленных DBMSSQL событий. Output: список рекомендаций «добавить индекс на `Документ.X.Период,Контрагент`».
3. **Lock Wait Anatomy** — view по аналогии с Deadlock Anatomy, но для TLOCK событий. ЦУП раздел 2.13.2. (Перенесено из Sprint 3 OPUS_HANDOVER.)
4. **Scroll-to-finding** + Custom SDBL highlighter — UX polish.

**P2:**

5. **Native rules расширение** до 18-20 правил — добавить `select_into_table_value` (выгрузка в `ТаблицаЗначений` без явного типа), `аналитика в подзапросе` (cross-апplication функций), и т.д.
6. **AI rewriter improvements** — few-shot examples в prompt для типичных 1С patterns.

**P3:**

7. **Saved queries** для Query Analyzer (можно сохранить запрос с findings).

**STOP RULES для Sprint 5:**

- Не делать MCP BSL Atlas integration — это Sprint 7 scope.
- Не делать EXPLAIN execution в живой базе — Sprint 7 через mcp-1c.
- Не возвращаться к BSL Language Server без явного pivot решения через ADR.

---

## Список открытых вопросов и сомнений

1. **DoD #23** — обозначено как documented gap. Sprint 5 кандидат на закрытие через UX-навигацию.
2. **Flaky Sprint 3 AI live test** — поднять таймаут до 30 сек.
3. **Stale paths в pytest output** — `..\1c-optimyzer\backend\tests\...` — pytest cache artifacts. Не блокирует.
4. **Cargo.toml line endings** — git auto-normalize, не моё изменение, можно ignore или закоммитить вместе с Sprint 4 changeset.

---

## Что трогать в Sprint 5 опасно

- `backend/src/optimyzer_backend/explainer/` — Sprint 3 explainer engine. Если меняем — отдельный sprint phase.
- `backend/src/optimyzer_backend/sql/anatomy.py`, `deadlock_anatomy.py` — Sprint 3 anatomy.
- `backend/src/optimyzer_backend/sql/views.py` — Sprint 3.5 ErrorsFeed добавил server-side event_types filter. Не ломать.
- Зомби папка `D:\1C-Optimyzer\1c-optimyzer\frontend\` — это остаток от Sprint 3.5 hoist. Pытаться удалить — Windows handle не отпускает. Игнорируем.

---

**Prepared by:** Claude Code (Sprint 4 implementation session). **For:** Opus 4.7 architectural review + Sprint 5 planning.
