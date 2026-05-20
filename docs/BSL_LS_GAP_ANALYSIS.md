# Gap analysis: BSL Language Server vs SDBL анализ (Sprint 4)

**Status:** Phase 0 deliverable (Sprint 4). Подтверждает решение — **pivot на native-only** (ADR-025).

## TL;DR

[`1c-syntax/bsl-language-server`](https://github.com/1c-syntax/bsl-language-server) **не используется** в Sprint 4 потому что:

1. BSL Language Server создан для языка **BSL** (`Процедура Х() Конец`) — синтаксис модулей конфигурации 1С.
2. **SDBL** (`ВЫБРАТЬ ... ИЗ ...`) — это **отдельный embedded язык**, который живёт **внутри строковых литералов** BSL (`Запрос.Текст = "ВЫБРАТЬ ..."`).
3. Sprint 4 Query Analyzer работает с **standalone SDBL** (юзер вставляет голый текст запроса), а не с BSL модулями.
4. Чтобы скармливать SDBL в BSL LS, пришлось бы оборачивать его в фейковый `.bsl` файл с фиктивной процедурой и `Запрос.Текст = "..."` — это hack который ломает офсеты диагностик (диагностика указывает на позицию в обёрнутом BSL, а не в исходном SDBL юзера).
5. Native rules engine на regex покрывает весь target list 12 правил методики ЦУП 2.13.4 без зависимости от Java + .jar.

**Решение:** Sprint 4 реализует **native-only** анализ. `BSLLanguageServerClient` остаётся в коде как **архитектурный placeholder** (always `available=False`) — для Sprint 5+, если появится потребность анализировать `.bsl` модули с embedded запросами.

## Target list — 12 правил методики ЦУП 2.13.4

| # | Правило | Severity | Native rule в Sprint 4? | BSL LS покрытие (если бы юзали) |
|---|---|---|---|---|
| 1 | Виртуальная таблица в JOIN | warning | ✅ `virtual_table_in_join.md` | Частично — у BSL LS есть `JoinWithVirtualTable`, но работает только внутри BSL модулей с `Новый Запрос(...)`. |
| 2 | Соединение с подзапросом | warning | ✅ `subquery_in_join.md` | Есть `JoinWithSubQuery` в BSL LS, тот же ограничивающий контекст. |
| 3 | OR в WHERE | info | ✅ `or_in_where.md` | Не покрывает — это runtime/optimizer hint, не статический паттерн. |
| 4 | В с подзапросом | warning | ✅ `in_with_subquery.md` | Есть `UsingInOperatorWithSubQuery`. |
| 5 | НЕ В с подзапросом | critical | ✅ `not_in_with_subquery.md` | Не отдельное правило в BSL LS. |
| 6 | ВЫРАЗИТЬ в WHERE | warning | ✅ `vyrazit_in_where.md` | Не покрывает — нет правила. |
| 7 | ВЫБРАТЬ РАЗЛИЧНЫЕ без нужды | info | ✅ `select_distinct.md` | Не покрывает. |
| 8 | ОБЪЕДИНИТЬ без ВСЕ | warning | ✅ `union_without_all.md` | Не покрывает. |
| 9 | Временная таблица без ИНДЕКСИРОВАТЬ | info | ✅ `temp_table_without_index.md` | Не покрывает — требует анализа последующего использования. |
| 10 | ВЫБРАТЬ * | warning | ✅ `select_star.md` | Не отдельное правило. |
| 11 | ПЕРВЫЕ N без УПОРЯДОЧИТЬ | warning | ✅ `pervye_without_order.md` | Не покрывает. |
| 12 | Неявное декартово произведение через запятую | critical | ✅ `comma_join_implicit.md` | Не покрывает явно. |
| 13 | Функция от поля в WHERE | warning | ✅ `function_in_where.md` (bonus +1) | Не покрывает. |

**13 native rules** в `backend/query_analyzer_rules/*.md` — превышает minimum DoD (8 правил).

## Что BSL LS даёт **в контексте полных BSL модулей** (Sprint 5+ scope)

Если в Sprint 5+ появится **MCP интеграция с конфигурацией 1С** (Sprint 7 BSL Atlas) — там BSL LS будет полезен, потому что:

- Знает все идентификаторы конфигурации (через `bsl-parser`)
- Парсит `Новый Запрос(...)` correctly
- Имеет 100+ диагностик BSL (mutable defaults, async/sync mismatch, etc.) которые **не** относятся к SDBL но полезны для аудита конфигурации
- Работает как Language Server Protocol — может интегрироваться с code editor в нашем UI (Sprint 8+ scope)

**Sprint 4 не делает** этих интеграций — это будущий scope.

## Почему **не** wrapped SDBL в фейковый BSL

Альтернатива — оборачивать SDBL в обёртку:

```bsl
// fake.bsl
Процедура _Запрос()
    Запрос = Новый Запрос;
    Запрос.Текст = "<юзерский SDBL>";
КонецПроцедуры
```

Проблемы:
1. **Offset drift** — диагностики BSL LS вернут line/col в этом обёрнутом файле, не в исходном SDBL. Нужно потом обратно мапить — это сложная и хрупкая логика.
2. **Параметры запроса** — юзерский SDBL может ссылаться на `&Дата`, которая в BSL LS expects `Запрос.УстановитьПараметр("Дата", ...)` в коде. Без этого BSL LS жалуется на missing parameter.
3. **Кавычки/escaping** — SDBL содержит строковые литералы (`"A001"`), они должны быть экранированы при вставке в BSL строковый литерал. Хрупко.
4. **Стартап оверхед** — BSL LS грузится 1-3 секунды при первом вызове. Для UI это уже превышает DoD #24 «< 5 секунд per query».

Эти проблемы решаемы, но **не дают выигрыша** vs native regex для нашего target list. ROI отрицательный.

## Что если кто-то захочет включить BSL LS в Sprint 5+

В `backend/src/optimyzer_backend/query_analyzer/bsl_ls_client.py` сохранена thin stub:

```python
class BSLLanguageServerClient:
    @property
    def available(self) -> bool:
        return self._available  # Sprint 4: всегда False
    def analyze_query(self, query_text, timeout=30.0):
        return []  # Sprint 4: всегда пусто
```

Чтобы включить:
1. Установить Java 11+
2. Скачать `bsl-language-server-N.N.N-exec.jar` с GitHub Releases
3. Положить в `~/.bsl-ls/bsl-language-server.jar`
4. В `bsl_ls_client.py.__init__` снять hard-disable
5. Реализовать `analyze_query` через `subprocess.run([java, -jar, jar, --analyze, -s, tmpfile, -r, json], timeout=30)`
6. Парсить JSON → `BSLDiagnostic`
7. `Aggregator._merge_and_dedupe` уже умеет приоритизировать native над BSL LS — менять не надо

**Это работа на Sprint 5+ если найдётся use case.**

## Sources

- [bsl-language-server документация](https://1c-syntax.github.io/bsl-language-server/)
- [1c-syntax/bsl-parser SDBLParser.g4](https://github.com/1c-syntax/bsl-parser/blob/master/src/main/antlr/SDBLParser.g4) — подтверждает что SDBL это отдельный grammar
- [Методика ЦУП 2.13.4 «Анализ длинных запросов»](https://its.1c.ru/) (внутренний ресурс)
- [Раздел 10 курса 1С:Эксперт «Запросы которые работают быстро»](https://uc1.1c.ru/)
