# Sprint 4 — Query Analyzer (paste & analyze + BSL Language Server sidecar + AI rewriter)

> **Контекст:** Sprint 3 закрыт (tag `v0.3.0-internal`, merge `f2b8249`). Sprint 3.5 (UI hotfix + ТЖ-симулятор + 60+ PowerShell-скиллов для 1С) закрыт (merge `127604b`). Real-data validation Phase D из Sprint 3 разблокирована — симулятор накопил 81 TDEADLOCK + достаточно TLOCK / DBMSSQL / EXCP в архиве.
>
> **Sprint 4 — это центральный sprint для позиционирования продукта.** Раздел 10 курса 1С:Эксперт («Запросы которые работают быстро») сейчас покрыт на 0%. Sprint 4 поднимает его до ~85% и одновременно закрывает Раздел 7 (Индексы) на ~60% и часть Раздела 8 (Анализ плана запроса) на ~80%. После Sprint 4 общее покрытие методики курса достигает ~40% — это та metric, которая идёт в маркетинг и статьи на Инфостарте.
>
> **Working directory:** `D:\1C-Optimyzer\1c-optimyzer\` **Branch от main:** `feat/sprint-4-query-analyzer`

---

## /goal

### GOAL

Дать пользователю возможность **вставить SDBL-запрос 1С** (язык запросов 1С) в отдельный экран Query Analyzer и получить:

1. **Подсветку конкретных проблемных мест** в исходном тексте запроса (line + column ranges с цветовым выделением). Не «общие советы», а **точные строки** с подсказкой что не так.
2. **Список findings** с описанием каждой проблемы по методике ЦУП раздела 2.13.4 + Раздел 10 курса 1С:Эксперт. Каждый finding имеет severity (critical / warning / info), категорию (performance / correctness / style) и линк на пункт методики.
3. **AI-переписанный вариант запроса** через Claude Sonnet с side-by-side сравнением и объяснением каждого изменения. AI работает поверх результата rule-based анализа (как в Sprint 3 explainer engine).
4. **Архитектурная подготовка** под Sprint 5 (анализ DBMSSQL событий из загруженного архива → подача SQL в Query Analyzer) и Sprint 7 (MCP BSL Atlas — поиск откуда этот запрос в коде конфигурации).

**Measurable outcome:** Middle-программист 1С вставляет реальный запрос из своего проекта → видит проблемные места с подсветкой → понимает что и почему переписать → копирует AI-вариант. Без чтения курса 1С:Эксперт. Время от вставки до вывода — менее 5 секунд для rule-based, менее 15 секунд для AI-варианта.

### CONTEXT

**Состояние после Sprint 3 + Sprint 3.5 (baseline):**

- Tag `v0.3.0-internal` на main
- 272 backend tests passing (Sprint 3.5 add 3 view tests + Sprint 3 base 268)
- 3 anatomy views работают (Top Business Operations / Operation Anatomy / Deadlock Anatomy)
- Rule engine с 8 markdown rules + AI Claude explainer работают на real data
- ТЖ-симулятор готов в `tools/tj-simulator/` (внешняя обработка + расширение конфигурации)
- 60+ PowerShell-скиллов в `.claude/skills/` — позволяют Claude Code автономно работать с конфигурациями 1С (создавать .epf, .cfe, выгружать/загружать XML, патчить методы)
- Покрытие методики 1С:Эксперт: Раздел 4 — 90%, Раздел 13 — 75%, Раздел 6 — 75%, общее ~30% (после Sprint 3)

**Стратегические решения принятые ДО Sprint 4 (обязательны к соблюдению):**

- **Развилка A1:** BSL Language Server подключается **как Java sidecar** (subprocess из Python backend). Запускаем `java -jar bsl-language-server.jar --analyze -s <input.bsl> -r json`, парсим JSON output. **Не** линкуем код, не модифицируем upstream — общение только через CLI invocation.
- **Развилка B1:** Если у пользователя **не установлена Java** — Query Analyzer работает в **degraded mode**: только native rules (без BSL Language Server). Показываем баннер «Установите Java для расширенного анализа» с кнопкой «Узнать как». Tool **не блокируется**, не падает.
- **Развилка C1:** GPL-3.0 у `bsl-language-server` — безопасно через subprocess invocation. Наш код не линкуется с GPL-кодом. **НЕ bundle** `.jar` файл в наш installer — пользователь сам качает с GitHub release. Инструкция установки в `docs/INSTALL_BSL_LS.md`.
- **Развилка D1:** MCP интеграция (BSL Atlas для поиска запроса в конфигурации, mcp-1c для validation запроса в живой базе) **отложена в Sprint 5+**. Sprint 4 — это **standalone «paste & analyze»** режим без зависимости от конфигурации.
- **Архитектурная подготовка под Sprint 8-9 (AI-генератор решений):** Sprint 4 backend закладывает интерфейс `solution_generator` который пока возвращает `501 Not Implemented`. Это резервирует место в API контракте чтобы Sprint 8 не переделывал архитектуру.

**Ключевые внешние артефакты которые используем:**

- **`1c-syntax/bsl-language-server` v0.25.0+** — GitHub release `.jar`, запускаем через subprocess. Документация: `https://1c-syntax.github.io/bsl-language-server/`. Особо важный режим — `--analyze -s <file> -r json`, выдаёт JSON с диагностиками формата `{range: {start: {line, character}, end: {line, character}}, severity, code, message, source}`.
- **`1c-syntax/bsl-parser` v0.26.0** — НЕ используем напрямую (это движок BSL LS, мы общаемся с LS высокоуровнево).
- **Claude API через Anthropic SDK** — backend-only (как Sprint 3), модель `claude-sonnet-4-5` по умолчанию.

**Целевая аудитория и use cases Sprint 4:**

- **Use case A (главный):** программист 1С нашёл медленный запрос в своём коде, скопировал текст запроса, вставил в наш Query Analyzer → получил список проблем → переписал и протестировал.
- **Use case B (от Sprint 5):** программист 1С в нашем tool открыл DBMSSQL событие из архива → кликнул «Проанализировать» → запрос автоматически попадает в Query Analyzer (через тот же интерфейс).
- **Use case C (от Sprint 7):** программист 1С указал XML-выгрузку своей конфигурации → tool находит каждый «плохой» запрос в коде по `context` события → подсвечивает прямо строку модуля.

Sprint 4 закрывает Use case A полностью и закладывает архитектурную базу для B и C.

**Ключевые файлы которые трогаем:**

- `backend/src/optimyzer_backend/query_analyzer/` — **новый пакет** (rule engine + BSL LS sidecar + AI rewriter)
- `backend/src/optimyzer_backend/query_analyzer/native_rules/` — native rules по методике ЦУП (не покрытые BSL LS)
- `backend/src/optimyzer_backend/rpc/query_analyzer_rpc.py` — новые RPC methods
- `backend/tests/test_query_analyzer.py` — unit tests
- `frontend/src/components/screens/QueryAnalyzer/` — новый screen (`QueryAnalyzer.tsx`, `FindingsList.tsx`, `RewriteDiff.tsx`)
- `frontend/src/components/editor/QueryEditor.tsx` — обёртка над CodeMirror 6 с подсветкой findings
- `frontend/src/components/chrome/Sidebar.tsx` — enable новый screen
- `frontend/src/i18n/ru.ts` — новые strings
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` — обновить статусы Разделов 7/8/10
- `docs/DECISIONS.md` — ADR-025..028
- `docs/INSTALL_BSL_LS.md` — инструкция установки Java + BSL LS для пользователя
- `docs/SPRINT_4_REPORT.md`, `docs/OPUS_HANDOVER_SPRINT_4.md`

### CONSTRAINTS

**Глобальные (обязательны):**

- CSS Modules, no inline styles
- ru-RU локализация в `i18n/ru.ts`
- Conventional commits (feat/fix/refactor/test/docs/chore) с scope
- No time estimates anywhere
- Light theme only — dark theme FORBIDDEN
- Не модифицировать `design/opt/*.jsx`
- ADR-001..024 в силе (не пересматривать)

**Sprint 4 специфичные:**

- BSL Language Server `.jar` **не bundle**. Инструкция установки + опциональный path configuration в settings.
- Claude API calls **только backend** (no frontend access to API key). Использовать existing `claude_client.py` из `explainer/` как pattern.
- AI rewriter timeout — 30 секунд (длиннее чем у Sprint 3 explainer потому что задача более сложная — generate code, не free text). Если timeout — показываем rule-based findings + кнопка «Попробовать ещё раз».
- AI cache — расширить existing `explainer_cache` table или сделать новый `query_rewrite_cache` (на выбор по структурной чистоте). Ключ кеша: `hash(нормализованный_текст_запроса + список_findings)`.
- Native rules engine — markdown файлы в `backend/src/optimyzer_backend/query_analyzer/native_rules/`, format похожий на Sprint 3 explainers (YAML frontmatter + body), но с дополнительными полями: `pattern_regex` или `ast_pattern` для матчинга против исходного текста.
- BSL LS sidecar invocation — через `subprocess.run()` с таймаутом 30 секунд. Если `.jar` не найден или Java отсутствует — silent fallback на native rules + установка флага `bsl_ls_available=False` в RPC response.

**Запрещено в Sprint 4:**

- НЕ делать integration с архивом ТЖ (Sprint 5 scope)
- НЕ делать MCP BSL Atlas integration (Sprint 7 scope)
- НЕ делать execution запроса в живой базе через mcp-1c (Sprint 7 scope)
- НЕ делать full IDE-like editor (только paste & analyze + подсветка)
- НЕ модифицировать существующие Sprint 3 anatomy views
- НЕ переписывать explainer engine — это **другой engine** для другой задачи. Можно переиспользовать code patterns, но не код.

### PRIORITY

- **P1 (блокирующее закрытие Sprint 4):**
  - Phase 0 — Gap analysis диагностик BSL Language Server vs наш список native rules
  - Phase A — BSL Language Server sidecar integration
  - Phase B — Native rule engine + минимум 8 native rules по методике ЦУП 2.13.4
  - Phase C — Findings aggregation + ranges normalization (BSL LS + native rules в один список)
  - Phase D — Frontend QueryAnalyzer screen + CodeMirror подсветка
  - Phase E — AI rewriter через Claude
  - Phase G — Real-data acceptance (на запросах из DBMSSQL событий тестового архива)
- **P2 (важно но не блокирующее):**
  - Phase F — Расширение кеша + persistence findings
  - Phase H — Документация обновлена, ADR'ы написаны
- **P3 (nice-to-have):**
  - Sidebar keyboard shortcut Ctrl+Q для Query Analyzer
  - Экспорт findings как Markdown отчёт

### PLAN

**Phase 0 — Discovery: gap analysis BSL Language Server vs наш target rule set**

Цель: понять **что уже умеет BSL Language Server из коробки**, чтобы не дублировать native rules, и **где у нас гэп** — те правила методики ЦУП, которых в BSL LS нет.

Создать `backend/scripts/bsl_ls_diagnostics_inventory.py` который:

1. Запускает BSL LS в режиме `--analyze` на **синтетическом наборе** запросов (10-15 файлов с известными антипаттернами по ЦУП 2.13.4: соединение с подзапросом, виртуальная таблица в JOIN, ИЛИ в условии WHERE, IN с подзапросом, ВЫРАЗИТЬ внутри WHERE, ОБЪЕДИНИТЬ ВСЕ vs ОБЪЕДИНИТЬ, и т.д.).
2. Парсит JSON output, собирает все коды диагностик которые BSL LS вернул.
3. Сопоставляет с нашим **target list** из 12-15 правил методики ЦУП.
4. Создаёт `docs/BSL_LS_GAP_ANALYSIS.md` со следующей таблицей:

| Антипаттерн ЦУП 2.13.4 | Покрывает BSL LS? | Код диагностики | Нужен native rule? |
|---|---|---|---|
| Соединение с подзапросом | ✅ | `JoinWithSubQuery` | Нет |
| Виртуальная таблица в JOIN | ❓ | — | **Да** |
| ... | | | |

Это документ — **критический input** для Phase B (наши native rules). Без него мы дублируем работу BSL LS или пропускаем то что они не покрывают.

**Target list 12-15 native rules** (на проверку через gap analysis):

Из методики ЦУП 2.13.4 «Анализ длинных запросов» и Раздела 10 курса:

1. `subquery_in_join` — соединение с подзапросом (антипаттерн)
2. `virtual_table_in_join` — виртуальная таблица регистра в JOIN
3. `or_in_where` — OR в условии WHERE (часто не использует индекс)
4. `in_with_subquery` — IN с подзапросом (заменить на JOIN)
5. `vyrazit_in_where` — ВЫРАЗИТЬ в условии WHERE (антипаттерн преобразования типа)
6. `not_in_with_subquery` — NOT IN с подзапросом (антипаттерн)
7. `select_distinct_unnecessary` — DISTINCT когда не нужен
8. `group_by_without_having` — GROUP BY с фильтрацией после, вместо HAVING
9. `union_instead_of_union_all` — ОБЪЕДИНИТЬ вместо ОБЪЕДИНИТЬ ВСЕ
10. `temp_table_without_index` — временная таблица без индекса для JOIN
11. `cross_join_implicit` — неявное декартово произведение через WHERE
12. `query_in_loop` — индикатор: SDBL syntax не покрывает, но AI может определить из контекста
13. `aggregation_without_index` — агрегация по полю без подходящего индекса
14. `force_brackets_loaded_table` — подзапрос-выборка вместо временной таблицы
15. `where_after_or_in_one_column` — WHERE с OR на одной колонке (легко переписать в IN)

Phase 0 уточнит какие из них уже в BSL LS, какие нужны нам как native.

**Phase A — BSL Language Server sidecar integration**

Backend `backend/src/optimyzer_backend/query_analyzer/bsl_ls_client.py`:

```python
import subprocess
import json
import shutil
from pathlib import Path
from dataclasses import dataclass

@dataclass
class BSLDiagnostic:
    line_start: int       # 1-based
    line_end: int
    col_start: int        # 1-based
    col_end: int
    severity: str         # "error" | "warning" | "info"
    code: str             # BSL LS rule code
    message: str
    source: str           # "bsl-language-server"

class BSLLanguageServerClient:
    def __init__(self, jar_path: str | None = None):
        """jar_path — путь к bsl-language-server.jar. Если None — пробуем
        стандартные локации (~/.bsl-ls/, $BSL_LS_HOME, рядом с исполняемым).
        Если ничего не нашли — self.available = False, и tool работает
        без BSL LS.
        """
        ...

    @property
    def available(self) -> bool:
        return self._jar_path is not None and self._java_available

    def analyze_query(self, query_text: str, timeout: float = 30.0) -> list[BSLDiagnostic]:
        """Запускает BSL LS на тексте запроса, возвращает список диагностик.
        Если self.available == False — возвращает [] и не вызывает subprocess.
        """
        if not self.available:
            return []
        # 1. Записать query_text во временный файл с расширением .bsl
        # 2. Запустить: java -jar <jar> --analyze -s <tmpfile> -r json
        # 3. Парсить JSON output → list[BSLDiagnostic]
        # 4. Если timeout / не-zero exit code — log warning, вернуть []
```

Здесь критично: **BSL LS работает с файлами `.bsl`, не с фрагментами текста**. Поэтому пишем временный файл и удаляем после анализа.

Тесты:
- `test_bsl_ls_available_check` — корректно определяет availability
- `test_bsl_ls_analyze_returns_diagnostics` — на синтетическом плохом запросе возвращает ≥1 диагностику
- `test_bsl_ls_handles_timeout` — при искусственном таймауте возвращает []
- `test_bsl_ls_handles_missing_jar` — при отсутствии jar возвращает []

**Phase B — Native rule engine + minimum 8 native rules**

Backend `backend/src/optimyzer_backend/query_analyzer/native_rules/`:

```
native_rules/
├── README.md                          # формат native rules
├── rule_loader.py                     # читает *.md
├── engine.py                          # match against SDBL text
├── rules/
│   ├── virtual_table_in_join.md
│   ├── or_in_where.md
│   ├── in_with_subquery.md
│   ├── vyrazit_in_where.md
│   ├── temp_table_without_index.md
│   ├── select_distinct_unnecessary.md
│   ├── group_by_without_having.md
│   └── union_instead_of_union_all.md
```

Формат native rule (`*.md`):

```markdown
---
id: virtual_table_in_join
applies_to: sdbl_query
severity: warning
category: performance
match:
  type: regex_lines
  patterns:
    - '(?i)ВНУТРЕННЕЕ\s+СОЕДИНЕНИЕ\s+\w+\.\.\w+\s*\.\s*Остатки'
    - '(?i)JOIN\s+\w+\.\.\w+\s*\.\s*Balance'
tags: [tsup-2.13.4, expert-10]
---

# Виртуальная таблица регистра в соединении

## Что не так

Виртуальные таблицы 1С (Остатки, Обороты, ОстаткиИОбороты) **не материализованы** — это набор запросов, которые платформа разворачивает в момент исполнения. Использование виртуальной таблицы в JOIN заставляет СУБД повторно вычислять её при каждом сравнении строк.

## Почему это плохо

Виртуальная таблица может содержать сложные подзапросы с группировками по периодам. JOIN заставит выполнить этот сложный подзапрос O(N×M) раз вместо одного раза.

## Как переписать

Вынести виртуальную таблицу в **отдельный запрос** через временную таблицу или индексированный временный набор:

```sdbl
ВЫБРАТЬ
    Остатки.Номенклатура,
    Остатки.Склад,
    Остатки.КоличествоОстаток
ПОМЕСТИТЬ ВТ_Остатки
ИЗ
    РегистрНакопления.ТоварыНаСкладах.Остатки(&Дата) КАК Остатки
ИНДЕКСИРОВАТЬ ПО Номенклатура, Склад
;

ВЫБРАТЬ ...
ИЗ
    Документ.РеализацияТоваровУслуг.Товары КАК Реализация
    ВНУТРЕННЕЕ СОЕДИНЕНИЕ ВТ_Остатки КАК Остатки
        ПО Реализация.Номенклатура = Остатки.Номенклатура
```

## Связано в курсе 1С:Эксперт

Раздел 10 — «Запросы которые работают быстро. Типичные причины неоптимальной работы. Приёмы оптимизации».
Методика ЦУП раздела 2.13.4 — «Виртуальные таблицы и временные таблицы».
```

Engine `engine.py`:

```python
def analyze(query_text: str, rules: list[Rule]) -> list[Finding]:
    """Прогоняет query_text через каждое правило, возвращает findings."""
    findings = []
    for rule in rules:
        if rule.match_type == 'regex_lines':
            for pattern in rule.patterns:
                for match in re.finditer(pattern, query_text):
                    line_start, col_start = _offset_to_line_col(query_text, match.start())
                    line_end, col_end = _offset_to_line_col(query_text, match.end())
                    findings.append(Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.category,
                        line_start=line_start, col_start=col_start,
                        line_end=line_end, col_end=col_end,
                        message=rule.title,
                        explanation_md=rule.body,
                        tags=rule.tags,
                    ))
    return findings
```

Тесты: для каждого rule — positive test (queries которые должны matchить) + negative test (queries которые **не** должны matchить).

**Phase C — Findings aggregation + ranges normalization**

Backend `backend/src/optimyzer_backend/query_analyzer/aggregator.py`:

Объединяет findings из BSL LS и native rules в один отсортированный список. Ranges нормализуются:

```python
@dataclass
class Finding:
    source: str              # "bsl-language-server" | "native"
    rule_id: str             # "virtual_table_in_join" or "BSL-LS-JoinWithSubQuery"
    severity: str            # "critical" | "warning" | "info"
    category: str            # "performance" | "correctness" | "style"
    line_start: int          # 1-based, inclusive
    line_end: int            # 1-based, inclusive
    col_start: int           # 1-based, inclusive
    col_end: int             # 1-based, exclusive
    message: str
    explanation_md: str
    tags: list[str]          # ["tsup-2.13.4", "expert-10"]

def analyze_query(query_text: str) -> dict:
    """Главный entry point — синхронный анализ запроса."""
    bsl_findings = bsl_ls_client.analyze_query(query_text)
    native_findings = native_engine.analyze(query_text, rules)
    all_findings = _merge_and_sort(bsl_findings + native_findings)
    return {
        "query_text": query_text,
        "findings": [_finding_to_dict(f) for f in all_findings],
        "bsl_ls_available": bsl_ls_client.available,
        "summary": {
            "critical": sum(1 for f in all_findings if f.severity == "critical"),
            "warning": sum(1 for f in all_findings if f.severity == "warning"),
            "info": sum(1 for f in all_findings if f.severity == "info"),
        }
    }
```

Дедупликация: если BSL LS и native rule матчат **одинаковый range** с одинаковой темой — оставляем один (priority: native rule, потому что у него русское объяснение по методике ЦУП).

RPC method:

```python
@rpc.method("query_analyzer.analyze")
def analyze_query_rpc(query_text: str) -> dict:
    """Synchronous, ≤5 sec для rule-based pass."""
    return analyze_query(query_text)
```

Тесты:
- На пустом запросе возвращает `findings = []`
- На синтетическом «плохом» запросе возвращает ≥3 findings
- `summary` counts корректны
- Если BSL LS unavailable — `bsl_ls_available=False`, native findings всё равно есть

**Phase D — Frontend QueryAnalyzer screen**

Файлы:

- `frontend/src/components/screens/QueryAnalyzer/QueryAnalyzer.tsx` — главный screen
- `frontend/src/components/screens/QueryAnalyzer/FindingsList.tsx` — список findings справа
- `frontend/src/components/editor/QueryEditor.tsx` — обёртка над CodeMirror 6

QueryAnalyzer layout (две колонки):

```
┌─────────────────────────────────────┬─────────────────────────────┐
│ QueryEditor (CodeMirror 6, ~60%)    │ FindingsList (правая, ~40%) │
│                                      │                              │
│  ВЫБРАТЬ                             │  ┌────────────────────────┐  │
│      Тов.Артикул                     │  │ ⚠️ Виртуальная таблица  │  │
│      ИЗ                              │  │ в JOIN                  │  │
│      Документ.Реализация             │  │ Строка 4-5              │  │
│      ВНУТРЕННЕЕ СОЕДИНЕНИЕ           │  └────────────────────────┘  │
│      РегистрНакопления.ТоварыНа... ←━━━━━ подсветка ranges'а        │
│                                      │  ┌────────────────────────┐  │
│  [Анализировать] [Очистить]          │  │ ⚠️ OR в WHERE           │  │
│                                      │  │ Строка 8                │  │
│  Status: 3 warning, 1 info           │  └────────────────────────┘  │
└─────────────────────────────────────┴─────────────────────────────┘
                                       [Переписать через AI →]
```

CodeMirror 6 setup в `QueryEditor.tsx`:

- Language: custom SDBL highlighter (минимальный — ключевые слова `ВЫБРАТЬ`, `ИЗ`, `ГДЕ`, `СГРУППИРОВАТЬ ПО`, `JOIN`, и т.д.)
- `@codemirror/lint` extension для подсветки findings — каждый finding конвертируется в Diagnostic с цветом по severity (red / amber / blue)
- Tooltip on hover — показывает `message` + краткое объяснение из `explanation_md`
- Click on finding в FindingsList — scroll к соответствующему range в editor

Initial state: editor пустой, placeholder «Вставьте запрос 1С здесь...». Кнопка «Анализировать» disabled пока editor пуст.

Action flow:
1. Юзер вставляет запрос
2. Нажимает «Анализировать»
3. Editor показывает loading state (5-15 сек если BSL LS) → findings appear
4. Findings подсвечены в editor + список справа
5. Кнопка «Переписать через AI» становится active

Если `bsl_ls_available == false` — баннер сверху: «BSL Language Server не установлен. Анализ выполнен только встроенными правилами. [Узнать как установить →]».

Sidebar entry: «Анализ запроса» (Ctrl+Q как keyboard shortcut), иконка `Database` или `Code`.

**Phase E — AI rewriter через Claude**

Backend `backend/src/optimyzer_backend/query_analyzer/ai_rewriter.py`:

```python
from anthropic import Anthropic

class QueryRewriter:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.enabled = bool(api_key)
        if self.enabled:
            self.client = Anthropic(api_key=api_key)

    def rewrite(self, query_text: str, findings: list[Finding]) -> dict:
        """Генерирует переписанный вариант запроса с объяснением."""
        if not self.enabled:
            return {"ok": False, "error": "API key not configured"}

        prompt = self._build_prompt(query_text, findings)

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                timeout=30.0,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

        # Парсим ответ — ожидаем structured response с разделами
        text = response.content[0].text
        return self._parse_response(text)
```

System prompt template (RU):

```
Ты — старший 1С-эксперт по производительности запросов. Тебе дан запрос на языке
1С (SDBL) с найденными проблемами. Перепиши запрос так, чтобы устранить все
указанные проблемы.

Правила:
1. Сохрани полностью бизнес-логику исходного запроса — результат должен быть
   эквивалентен.
2. Используй типичные приёмы оптимизации 1С: вынос виртуальных таблиц во
   временные таблицы, замена IN на JOIN, индексация временных таблиц,
   ОБЪЕДИНИТЬ ВСЕ вместо ОБЪЕДИНИТЬ когда дубли невозможны.
3. Пиши на чистом 1С-Запросе (SDBL) с правильными русскими ключевыми словами.
4. Структура твоего ответа — строгий JSON:

{
  "rewritten_query": "ВЫБРАТЬ\n...\n",
  "changes": [
    {
      "what": "Вынес виртуальную таблицу Остатки во временную таблицу с индексом",
      "why": "Виртуальная таблица в JOIN заставляет СУБД повторно вычислять её",
      "lines_in_original": [4, 5]
    },
    ...
  ],
  "estimated_improvement": "Запрос должен работать 5-50x быстрее на больших объёмах",
  "notes_for_developer": "Проверьте что параметр &Дата установлен корректно"
}

Если запрос **не может быть улучшен** или проблемы не критичны — верни тот же
запрос с пустым массивом changes и notes_for_developer объяснением.
```

User prompt template:

```
Исходный запрос:
```sdbl
{query_text}
```

Найденные проблемы:
{findings_list_formatted}

Перепиши запрос устранив все проблемы. Ответь только JSON.
```

Парсинг response — `json.loads(text)` с fallback на текстовый mode (если AI не выдал валидный JSON, попытаться извлечь блок ` ```json ... ``` ` или вернуть error).

AI cache (расширение existing `data/explainer_cache.db`):

```sql
CREATE TABLE IF NOT EXISTS query_rewrite_cache (
    cache_key VARCHAR PRIMARY KEY,
    query_hash VARCHAR,
    findings_hash VARCHAR,
    rewritten_query TEXT,
    changes_json TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`cache_key = sha256(normalized_query + sorted_findings_ids)` — если тот же запрос с теми же findings уже переписывался, возвращаем из кеша.

RPC method:

```python
@rpc.method("query_analyzer.rewrite")
def rewrite_query_rpc(query_text: str, findings: list[dict]) -> dict:
    """Возвращает переписанный вариант, может занять до 30 сек."""
    cache_key = compute_cache_key(query_text, findings)
    cached = check_cache(cache_key)
    if cached:
        return {"ok": True, "from_cache": True, **cached}

    result = rewriter.rewrite(query_text, findings)
    if result["ok"]:
        save_to_cache(cache_key, result)
    return result
```

Frontend `RewriteDiff.tsx` — side-by-side diff:

```
┌─────────────────────────────┬─────────────────────────────┐
│ Исходный запрос             │ Переписанный (AI)           │
│                              │                              │
│ (highlighted findings)       │ (clean version)              │
│                              │                              │
│                              │ Изменения:                   │
│                              │ 1. Вынес виртуальную таб...  │
│                              │ 2. Заменил IN на JOIN...     │
└─────────────────────────────┴─────────────────────────────┘
                              [Скопировать] [Закрыть]
```

Кнопка «Переписать через AI» в QueryAnalyzer → открывает modal с RewriteDiff. Если AI rewriter недоступен (нет API key) — кнопка disabled с tooltip «Настройте ANTHROPIC_API_KEY в .env для AI-переписывания».

**Phase F — Архитектурная подготовка под Sprint 5+8 (solution_generator placeholder)**

Backend `backend/src/optimyzer_backend/query_analyzer/solution_generator.py`:

```python
"""Solution Generator — placeholder для Sprint 8-9.

В Sprint 4 это пустой интерфейс который всегда возвращает 501. Это резервирует
место в API контракте чтобы Sprint 8 (AI-генератор обработок 1С под конкретную
базу через MCP BSL Atlas) не переделывал архитектуру.
"""

class SolutionGenerator:
    def __init__(self):
        self.enabled = False  # Sprint 4: всегда False. Sprint 8: True если MCP подключён.

    def generate_solution(self, finding: Finding, base_context: dict) -> dict:
        """Sprint 8 implementation: генерирует .epf или фрагмент кода под конкретную базу."""
        return {
            "ok": False,
            "error": "Solution generator not yet implemented (planned for Sprint 8)",
            "status_code": 501,
        }
```

RPC:

```python
@rpc.method("query_analyzer.generate_solution")
def generate_solution_rpc(finding_id: str, base_context: dict) -> dict:
    return solution_generator.generate_solution(finding_id, base_context)
```

Frontend в `FindingsList.tsx` — кнопка «Сгенерировать решение» **не рендерится** в Sprint 4 (так как backend всегда 501). Но RPC интерфейс готов — Sprint 8 просто включает кнопку и backend начинает возвращать настоящий ответ.

В `Finding` dataclass добавляется опциональное поле `solution_template_id: str | None = None` — placeholder для Sprint 8.

**Phase G — Real-data acceptance gate**

Acceptance tests `backend/tests/test_sprint4_real_data.py`:

```python
@pytest.mark.skipif(not OPTIMYZER_REAL_FOLDER_PATH, reason="...")
class TestSprint4Acceptance:

    def test_bsl_ls_gap_analysis_documented(self):
        """Phase 0 deliverable: docs/BSL_LS_GAP_ANALYSIS.md существует."""

    def test_native_rules_minimum_8(self):
        """Phase B: минимум 8 native rules в каталоге."""

    def test_query_analyzer_finds_issues_in_real_sql(self):
        """Берём 10 DBMSSQL событий из загруженного архива.
        Извлекаем SQL текст. Прогоняем через QueryAnalyzer.
        Проверяем что хотя бы 70% запросов получают ≥1 finding.
        """

    def test_query_analyzer_under_5s_per_query(self):
        """Rule-based анализ одного запроса < 5 секунд."""

    def test_query_analyzer_works_without_bsl_ls(self):
        """Если BSL LS sidecar недоступен (jar_path=None) — native rules
        всё равно возвращают findings без crashes."""

    def test_ai_rewriter_returns_valid_sdbl(self):
        """AI rewriter возвращает синтаксически корректный SDBL.
        Skip если ANTHROPIC_API_KEY не настроен.
        Проверяем через простую регулярку — есть ВЫБРАТЬ или есть SELECT,
        нет SQL injection patterns.
        """

    def test_ai_cache_works_for_repeated_query(self):
        """Повторный rewrite того же запроса возвращается из cache."""

    def test_solution_generator_returns_501(self):
        """Sprint 4: solution generator всегда 501 (placeholder)."""
```

Manual smoke test:
1. Открыть Query Analyzer (Ctrl+Q)
2. Вставить запрос из набора тестов (из `tests/fixtures/bad_queries.sdbl`)
3. Нажать «Анализировать»
4. Увидеть ≥3 findings с подсветкой
5. Нажать «Переписать через AI»
6. Увидеть rewritten variant с changes list
7. Скопировать rewritten — он должен быть валидным SDBL

**Phase H — Документация + ADR'ы**

`docs/BSL_LS_GAP_ANALYSIS.md` (Phase 0 deliverable) — таблица покрытия.

`docs/INSTALL_BSL_LS.md` — инструкция для пользователя:
1. Установите Java 11+ (ссылка на Adoptium / Liberica JDK)
2. Скачайте `bsl-language-server-N.N.N-exec.jar` с GitHub releases
3. Положите в `~/.bsl-ls/bsl-language-server.jar` или укажите путь в настройках 1C-Optimyzer
4. Перезапустите tool
5. В Query Analyzer внизу будет статус «BSL Language Server: подключён ✓»

`docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` — обновить:
- Раздел 7 (Индексы): 0% → 60%
- Раздел 8 (Анализ плана запроса): 0% → 40% (без EXPLAIN integration — это Sprint 7)
- Раздел 10 (Запросы которые работают быстро): 0% → 85%
- Общее покрытие: ~30% → ~40%

ADR'ы:
- **ADR-025** — BSL Language Server как Java sidecar (subprocess), не linked dependency
- **ADR-026** — GPL-3.0 safety через process isolation
- **ADR-027** — Solution Generator placeholder для Sprint 8 architectural readiness
- **ADR-028** — Native rules engine как complement к BSL LS, не replacement

`docs/SPRINT_4_REPORT.md` — closure report по template Sprint 3.
`docs/OPUS_HANDOVER_SPRINT_4.md` — handoff для Sprint 5.

### DONE WHEN

| # | Criterion | Verification |
|---|---|---|
| 1 | Phase 0 — `docs/BSL_LS_GAP_ANALYSIS.md` создан с таблицей покрытия | file exists, peer review |
| 2 | BSL LS sidecar integration работает: при наличии `.jar` запускается, возвращает диагностики | unit tests |
| 3 | BSL LS sidecar gracefully degrades: при отсутствии `.jar` `bsl_ls_available=False`, no crash | unit tests |
| 4 | Минимум 8 native rules в `backend/src/optimyzer_backend/query_analyzer/native_rules/rules/` | file count |
| 5 | Каждое native rule имеет positive + negative unit test | pytest |
| 6 | `analyze_query` RPC возвращает findings list с line/col ranges | unit + integration tests |
| 7 | Findings из BSL LS и native rules дедуплицируются | unit test |
| 8 | Frontend QueryAnalyzer screen доступен через Sidebar (Ctrl+Q) | manual |
| 9 | CodeMirror 6 подсвечивает findings по line/col ranges | manual |
| 10 | Click on finding в правой панели scroll к соответствующему месту в editor | manual |
| 11 | Если BSL LS недоступен — баннер с инструкцией установки | manual |
| 12 | AI rewriter работает через Claude (backend only, no API key in frontend) | code review |
| 13 | AI rewriter возвращает structured response (JSON с `rewritten_query` + `changes`) | unit test |
| 14 | AI cache работает (повторный запрос мгновенный) | acceptance test |
| 15 | Если ANTHROPIC_API_KEY не настроен — AI rewriter graceful disabled, кнопка disabled | manual |
| 16 | Solution generator интерфейс готов, всегда возвращает 501 в Sprint 4 | unit test |
| 17 | `docs/INSTALL_BSL_LS.md` написана | file |
| 18 | `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновлён со Sprint 4 статусами | file diff |
| 19 | ADR-025..028 written в `docs/DECISIONS.md` | file |
| 20 | pytest суммарно ≥ 320 (Sprint 3.5 had 272, +48+ для query analyzer) | CI |
| 21 | TypeScript build clean (0 errors) | CI |
| 22 | Conventional commits | git log |
| 23 | **ACCEPTANCE GATE:** Query analyzer находит ≥1 finding в 70%+ реальных DBMSSQL запросов из архива | env-gated pytest |
| 24 | **ACCEPTANCE GATE:** Rule-based анализ одного запроса < 5 сек | env-gated pytest |
| 25 | **ACCEPTANCE GATE:** AI rewriter возвращает валидный SDBL за < 30 сек | env-gated pytest, skipped без API key |
| 26 | **ACCEPTANCE GATE:** Native rules работают без BSL LS (degraded mode) | env-gated pytest |
| 27 | SPRINT_4_REPORT.md + OPUS_HANDOVER_SPRINT_4.md written | files |

Пункты 23-26 — обязательные blocking gates. Sprint 4 не закрыт без них.

### VERIFY

- **pytest backend** — 320+ tests зелёные (Sprint 0-3.5 baseline + Sprint 4 add)
- **TypeScript build** — 0 errors
- **Manual smoke (`.\start.bat`):**
  - Открыть Query Analyzer через Sidebar (или Ctrl+Q)
  - Вставить тестовый запрос
  - Нажать «Анализировать» — увидеть findings с подсветкой
  - Если BSL LS установлен — увидеть findings и от BSL LS, и от native rules
  - Если BSL LS не установлен — увидеть только native findings + баннер
  - Нажать «Переписать через AI» (если key есть) — увидеть rewritten variant
  - Скопировать rewritten — это валидный SDBL
- **Регрессия Sprint 0-3.5** не сломана: все anatomy views работают, Errors Feed работает с server-side фильтром, ТЖ-симулятор не тронут

**Rollback plan:**

Если Sprint 4 ломает что-то в Sprint 3:
- `git revert <sprint4_merge_commit>` возвращает на `v0.3.0-internal`
- Schema migration: новая table `query_rewrite_cache` в `data/explainer_cache.db` — можно DROP без последствий, БД пересоздаётся
- BSL LS `.jar` — это user-side asset, наш rollback его не трогает
- Frontend: Query Analyzer screen — изолированный, удаление не ломает другие

### OUTPUT

После закрытия Sprint 4:

- Tag `v0.4.0-internal` на merge commit
- `docs/SPRINT_4_REPORT.md` с измеренными метриками (gap coverage, % real queries with findings, AI rewriter success rate)
- `docs/BSL_LS_GAP_ANALYSIS.md` (Phase 0 deliverable)
- `docs/INSTALL_BSL_LS.md`
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновлён с покрытием ~40%
- ADR-025..028
- `docs/OPUS_HANDOVER_SPRINT_4.md` для следующей архитекторской сессии
- README updated со статусом «Sprint 4 closed, query analyzer with BSL LS + AI rewriter»

### STOP RULES

- **Phase 0 gap analysis — критический.** Если выяснится что BSL LS уже покрывает 12 из 15 target rules — **остановиться и спросить архитектора через ranked options**: (a) добавить только 3 native rules для гэпа, (b) переориентироваться на rules не из списка target, (c) другое. Не делать 8 native rules вслепую если BSL LS их уже даёт.
- Останавливаться при неоднозначности high impact. Не выдумывать архитектуру BSL LS — читать их официальную документацию `https://1c-syntax.github.io/bsl-language-server/`.
- Показывать ranked options (2-4 варианта), не задавать open-ended вопросы.
- Не расширять scope. Смежные задачи (анализ DBMSSQL событий из архива / MCP BSL Atlas / EXPLAIN integration) → `OPUS_HANDOVER_SPRINT_4.md` как Sprint 5/7 кандидаты.
- No time estimates anywhere в reports/commits/docs.
- Light theme only (dark theme FORBIDDEN).
- Не модифицировать `design/opt/*.jsx`.
- Не модифицировать ADR-001..024 без явного указания архитектора.
- Destructive ops (новая table в `data/explainer_cache.db`) → явно проверять `CREATE TABLE IF NOT EXISTS`.
- Conventional commits обязательны: один логический commit = один scope.
- Real-data acceptance gates (DoD #23-26) — блокирующие условия закрытия Sprint 4.
- Anthropic API key — НИКОГДА в commits, `.gitignore`, `.env` только локально.
- AI cache — `data/explainer_cache.db` (расширение existing) или новый `data/query_cache.db` (на структурное усмотрение Claude Code).
- BSL LS subprocess — таймаут 30 секунд **обязательно**. Если subprocess висит — kill и возвращать [].
- Если AI rewriter стабильно генерирует невалидный SDBL — fix prompt итеративно (примеры в few-shot), но **не** замещать на heuristics. Лучше «AI temporarily unavailable» чем плохой AI.
- Native rules — markdown файлы под git. Если меняется формат YAML frontmatter — обновлять `README.md` в `native_rules/`.
- Если Phase 0 показывает что у пользователя BSL LS зависает на синтаксисе 1С (SDBL не его core scope — он для BSL, а это разные языки) — **остановиться и спросить через ranked options**: (a) использовать BSL LS только для соседних `.bsl` файлов (не SDBL), (b) написать свой SDBL parser, (c) переориентироваться только на native rules. Это критическая развилка.

---

**Prepared by:** Claude Opus 4.7 (architect) **For:** Claude Code (Sprint 4 implementation session)
