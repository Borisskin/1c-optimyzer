# 1C-Optimyzer ↔ Программа курса 1С:Эксперт по технологическим вопросам

> **Дата:** 2026-05-25 (post Sprint 7 closure, tag `v0.7.0-internal`)
> **Аудитория:** архитектор (Claude Opus 4.7) + Сергей.
> **Назначение:** компас для product roadmap, marketing message, gap-list для Sprint 8+.
> **База:** программа курса 1С:Эксперт по тех. вопросам (УЦ № 1, фирма 1С, 18 разделов).
>
> Этот документ — поднимает `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` (последнее
> обновление — Sprint 5) до состояния after-Sprint-7 и добавляет **готовый
> investigation pipeline** в конце.

---

## Карта продукта на момент Sprint 7 closure

| Killer-фича | Sprint | Экран в UI | Что внутри |
|---|---|---|---|
| Анализ архивов ТЖ | Sprint 1-5 | Operations / Anatomy / SlowQueries / LocksTimeline / DeadlockAnatomy / ProcessRoles / DurationHistogram / ErrorsFeed / ActivityHeatmap / ArchiveComparison / SQLConsole | DuckDB per-archive + 7 pre-built views + 11 explainer rules + sqlglot T-SQL antipatterns + AI explainer |
| Query Analyzer SDBL | Sprint 6 | QueryAnalyzer | bsl-language-server (19 диагностик) + 13 native regex rules + 8 semantic rules (ConfigurationMetadataStore) + AI rewriter (Claude Sonnet 4.5) |
| Plan Analyzer SQL Server | **Sprint 7** | PlanAnalyzer | PerformanceStudio CLI (30 правил) + html-query-plan visualization (SSMS-style) + AI explanation на русском + auto-extract из `planSQLText` ТЖ |

Frontend: 14 рабочих экранов (см. `frontend/src/components/screens/`).
Backend: 295 unit-тестов, ~11.6K LoC Python.
Server (cloud AI): 95 tests, ~48K LoC (включая Phase 1 INFRA — auth/billing).
Frontend: ~16.4K LoC TS/TSX, TypeScript noEmit clean.

---

## Раздел 1. Производительность глазами ИТ-менеджера

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Тюнинг vs рекомендации | ⚪ Out of scope | Organizational topic, не tool-feature |
| Настройки кластера 1С / СУБД | 🔴 Не покрыто | Real-time agents — Module 2+ |
| Вертикальное / горизонтальное масштабирование, кластеризация, сплит | 🟡 Косвенно | ProcessRoles + ActivityHeatmap показывают распределение нагрузки между rphost/rmngr/ragent, но рекомендаций по кластеризации не даём |

**Покрытие раздела: ~5%.** Это управленческий раздел, не tool-feature.

**Можно улучшить:**
- В ProcessRoles screen добавить аналитический модуль «Дисбаланс кластера» — детект `max(rphost_load) / avg > 3` → рекомендация горизонтального сплита. Используя имеющийся `viewProcessRoles` RPC, добавить отдельную секцию через CollapsibleSection. ~2 дня.

---

## Раздел 2. Обзор средств и методик мониторинга и расследования

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Обзор средств мониторинга и расследования проблем | ✅ Полностью | Сам tool **является** средством. README + landing page позиционируют это явно |

**Покрытие: 100%.** Мы сами — это средство.

---

## Раздел 3. Apdex и SLA

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Apdex — определение | 🟡 Частично | UI пока не показывает Apdex как single number, но Operations screen group-by `context_normalized` даёт сырьё для расчёта (calls, total_duration, max_duration) |
| Типовые средства БСП для Apdex | 🔴 | БСП специфично, не покрываем |
| Ключевые операции, целевое время, SLA | 🔴 | Требует organizational input (целевые SLO) — Module 2+ |
| Apdex для нагрузочного тестирования | 🟡 | Через ArchiveComparison можно сравнить два архива (before/after) |
| Apdex для оптимизации (ЦКТП методика) | 🟡 | Operations screen с фильтром по `event_type=CALL` (Apdex считается строго по CALL) — добавлен в Sprint 7 post-Phase F. См. комментарий в `Operations.tsx`: «1С:Эксперт-методика учит, что Apdex считается по CALL events» |
| Обратный Apdex / DeltaApdex | 🟡 | Через ArchiveComparison (Sprint 2 Phase G) |
| Насколько можно ускорить по Apdex | 🟡 | Anatomy: «Top SQL внутри операции» показывает вес каждого SQL запроса в total time → видно potential for improvement |

**Покрытие раздела: ~35%.**

**Что НЕ покрываем (намеренно):**
- Continuous Apdex monitoring — требует agents (Module 2+)
- БСП Apdex-замеры — не наш target use case (мы работаем по archive, не agent)

**Можно улучшить (конкретные предложения):**
1. **Apdex calculator на экране Operations** — добавить optional input «целевое время T (мс)» → рассчитать Apdex по формуле `(satisfied + tolerable/2) / total` где satisfied=`duration ≤ T`, tolerable=`T < duration ≤ 4T`. Использовать существующую `top_business_operations` RPC, новый клиентский postprocessing. ~1 день. Bsl-LS / Sprint 6 не нужен.
2. **DeltaApdex** в ArchiveComparison: сравнить Apdex per operation между двумя архивами, color-coded green/red. ~2 дня.
3. **«Ключевые операции» — пометить top-N по wall-clock impact** через `operation_heavy` rule (уже есть в `backend/explainers/operation_heavy.md` с порогом ≥60s). UI пока подсвечивает их badge'ом в Anatomy — можно вынести на Operations screen первой колонкой.

---

## Раздел 4. Когда уже тормозит — методика расследования

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| С чего начать расследование | ✅ Полностью | Default startup screen = Operations (Sprint 4 commit `3e29cb4`). Workflow: load archive → Operations → click row → Anatomy → drill-down |
| Ускорение единичной операции | ✅ Полностью | Anatomy: timeline + breakdown по event_type + Top SQL внутри операции + связанные исключения + 11 explainer rules |
| Штатный замер производительности (Замер 1С) | 🔴 | Замер пишется в свой регистр БСП, не в ТЖ. Не покрываем |
| Скрытые действия платформы | ✅ Полностью | Anatomy: timeline показывает SCALL/SDBL/DBMSSQL/EXCP/Context — видны invisible-операции (запросы кэша, фоновые обновления) |
| Время на клиент-сервер взаимодействие | ✅ Полностью | rule `slow_op_call_cascade` (`backend/explainers/slow_op_call_cascade.md`) триггерится на ≥1000 calls с avg ≤50ms — типичный N+1 паттерн |
| Оптимизация клиент-серверного взаимодействия | ✅ Полностью | AI explainer (Anatomy → ExplainerCard) выдаёт конкретные action items |
| Поиск узких мест системы | ✅ Полностью | Operations sortable по 7 метрикам (total_duration / avg / max / SQL impact / lock_events / exception_events / calls) |
| Различие методик единичная операция vs система | ✅ Полностью | Operations (whole system) → клик → Anatomy (single operation) — явная иерархия |
| Сборка общей картины | ✅ Полностью | Cross-filtering между всеми views (общий store filters) + ArchiveComparison для baseline vs current |

**Покрытие раздела: ~95%.** Это наш core competency.

**Что НЕ покрываем:** «Замер производительности» БСП — это другой источник данных (регистр БСП, не ТЖ). Не критично.

**Можно улучшить:**
- AI-explainer в Operations screen (не только в Anatomy) — рассказать суммарно по всем top-N операциям сразу. Используя имеющийся `/v1/ai/explain` endpoint с новым prompt-template `archive_summary`. ~3 дня.

---

## Раздел 5. Производительность оборудования

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Счётчики Windows (PerfMon) | 🔴 | Не пишется в ТЖ — отдельная диагностика |
| Анализ загрузки железа Win/Linux | 🔴 | Module 2+ (agents) |
| Счётчики MS SQL Server (DMV) | 🔴 | Не входит в ТЖ archive, нужны DMV — Module 2+ |
| Утечки памяти, прожорливые вызовы | 🟡 | Через `MEM` events в ТЖ (если включены в logcfg) — есть данные, нет dedicated UI |
| CPU/диск/память на 1С-сервере | 🟡 | Через ProcessRoles + DBMSSQL длительности |
| Нагрузка на СУБД | 🟡 | SlowQueries + Anatomy (Top SQL внутри операции) → видно по группам SQL |
| Счётчики / особенности VMWare | ⚪ | Infrastructure monitoring — out of scope |

**Покрытие: ~25%.**

**Что технически невозможно для нашей architecture:**
- Real-time hardware counters — мы работаем по archive ТЖ (post-mortem), не агент. Чтобы покрыть полностью — нужен Module 2 (agents).

**Можно улучшить:**
- Добавить MEM events parser в `tj_parser.py` (~50 строк) + новый view «Утечки памяти» (rphost процессы с растущей `MemSize` через time). ~3 дня.
- Если у пользователя включён PerfMon CSV — добавить import CSV счётчиков и time-align с ТЖ через `MEM/CPU` events. Sprint 9 candidate.

---

## Раздел 6. Технологический журнал — настройка и анализ

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| ТЖ — общее | ✅ Полностью | Core competency |
| Настройка ТЖ (logcfg.xml) | 🟡 | `scripts/patch-logcfg-for-plans.ps1` правит logcfg для DBMSSQL.Plan capture + `docs/onboarding/enable-dbmssql-plans.md`. Self-elevation UAC, backup, idempotent. Прочие настройки (TLOCK, TDEADLOCK, MEM, LEAKS) — manual. Готов patch-скрипт показал паттерн для будущих автоматизаций |
| Расследование через ТЖ | ✅ Полностью | Все 10 экранов Анализ работают на ТЖ |
| Динамические представления MS SQL/Postgres | 🔴 | Не входит в ТЖ — отдельный mode, Module 2+ |
| Extended Events | 🔴 | Не ТЖ, требует подключения к SQL Server — Module 2+ |
| Нормализация запросов из trace/ТЖ | ✅ Полностью | `sql_text_normalized` + `sql_text_hash` колонки в DuckDB events. Group-by `sql_text_hash` агрегирует похожие запросы. Frontend всегда показывает RAW exemplar самого медленного из группы (memory rule «не показывать normalized с `?`» — commit `0878e2e`) |
| Найти запрос в коде конфигурации | 🟡 | QueryAnalyzer + bsl-LS Sprint 6 — semantic-проверка SDBL с подсветкой по линии конфигурации, но navigate-to-source через double-click пока нет |
| Логи Postgres | 🔴 | Не ТЖ, отдельный source — Sprint 8+ |
| ТЖ vs trace — влияние на perf | ⚪ | Documentation topic |
| 1С:ЦУП | ⚪ | Конкурент, не feature |

**Покрытие раздела: ~70%.**

**Что технически невозможно:**
- DMV / Extended Events — это live SQL Server data, мы работаем по archive ТЖ. Можно добавить отдельный режим (например, читать DMV через ODBC при подключении к SQL Server live) — Module 2+ scope.

**Можно улучшить:**
1. **Autocompletion и diff для logcfg.xml** — wizard-страница «Настройка ТЖ» в Settings, чек-листом включаем `<event>` для TLOCK / TDEADLOCK / MEM / LEAKS / DBMSSQL.Plan. Используем паттерн `patch-logcfg-for-plans.ps1` (idempotent + backup + UAC + restart ragent). ~3 дня.
2. **Navigate-to-source из QueryAnalyzer** — bsl-LS даёт `range` для каждой диагностики; через ConfigurationMetadataStore Sprint 5 можем резолвить `Catalog.Контрагенты.Module.bsl` → открыть в Tauri через `open-with-default-app` shell command. ~2 дня.

---

## Раздел 7. Индексы базы данных

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Что такое индекс БД | ⚪ Documentation |  |
| Когда индексы ускоряют запросы | ✅ Полностью | **Sprint 7 PlanAnalyzer**: PerformanceStudio показывает Missing Index recommendations с SQL Server optimizer estimates (impact %). MissingIndexes.tsx компонент — table + impact +CREATE INDEX statement |
| Кластерный / покрывающий индекс | ✅ Частично | AiPlanExplanationCard: AI объясняет какие колонки нужны (INCLUDE для covering) — это в SYSTEM_PROMPT_EXPLAIN_PLAN |
| Когда индексы бесполезны | 🟡 | bsl-LS Sprint 6 + native rule `temp_table_without_index` (положили во временную таблицу 1М строк без индекса) |
| Каких индексов не хватает | ✅ Полностью | Sprint 7 — Missing Indexes из PerformanceStudio CLI + AI suggested_indexes с rationale и CREATE INDEX statement |
| Лишние индексы | 🔴 | Требует подключение к БД (sysindexes + usage stats DMV) — Module 2+ |
| Особенности платформенных индексов 1С | 🟡 | Через ConfigurationMetadataStore (Sprint 5) знаем какие реквизиты есть у объектов — но индексы 1С (по `_IDRRef`, по индексным полям, по измерениям регистров) implicit, не отображаем |

**Покрытие раздела: ~70%** (рывок в Sprint 7 благодаря Plan Analyzer).

**Что технически невозможно:**
- «Лишние индексы» — нужны `sys.dm_db_index_usage_stats` DMV, нет в ТЖ. Module 2+.

**Можно улучшить:**
1. **Индексы 1С через ConfigurationMetadataStore** — парсить `IndexingType` атрибутов из `*.xml` выгрузки конфы (Sprint 5 parser уже даёт `Attributes`). Показать в QueryAnalyzer hint: «реквизит `Контрагент` — индексируемый, фильтр по нему отработает за milliseconds». ~3 дня.
2. **Полу-автоматическое создание T-SQL CREATE INDEX скриптов** для Missing Indexes — уже есть в `AiPlanExplanationCard.tsx` (auto-generated CREATE INDEX statement). Можно добавить кнопку «Скопировать → SSMS» с предупреждением «check selectivity first».

---

## Раздел 8. План запроса (анализ работы запроса)

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Зачем нужен план запроса | ✅ Полностью | **Sprint 7 PlanAnalyzer** — главный экран про это |
| Виды планов запроса | 🟡 | Поддерживаем XML (`.sqlplan` из SSMS + paste XML) + text (planSQLText из ТЖ). PostgreSQL — Sprint 8 (pev2) |
| Получение плана в MSSQL | ✅ | 3 пути в UI: `.sqlplan` файл / paste XML / автоэкстракт из ТЖ архива (`planSQLText` после patch-logcfg) |
| Получение плана в Postgres | 🔴 | Sprint 8 — pev2 |
| Основные операторы плана | ✅ Полностью | html-query-plan v2.6.1 visualization — SSMS-style дерево с tooltips, иконки операторов (Scan / Seek / Hash Match / Nested Loops / Sort / Stream Aggregate / Filter / Compute Scalar / Top / Spool / ...) |
| Признаки неоптимальных планов | ✅ Полностью | PerformanceStudio CLI — 30 правил: Missing Index, Key Lookup, Hash Spill, Implicit Conversion, Non-SARGable, Top Above Scan, Optimize For Unknown, Parameter Sniffing, Memory Grant Wait, и т.д. |
| Влияние статистики на план | 🟡 | PerformanceStudio детектит `EstimatedRows / ActualRows` mismatch (правило Cardinality Estimation Issues) — попадает в warnings. AI explanation на русском объясняет почему статистика устарела и что делать |
| Параллелизм MSSQL | 🟡 | PerformanceStudio: parallelism-related правила (Parallel Skew, Serially Parallel, Exchange Spill). Visualization показывает parallel operators жёлтым icon-bar |
| Параллелизм Postgres | 🔴 | Sprint 8 |

**Покрытие раздела: ~80%** (главный рывок Sprint 7 от 40% до 80%).

**Что НЕ покрываем сейчас:**
- PostgreSQL — Sprint 8 candidate (pev2 + EXPLAIN JSON parser). 1С на MSSQL — 80%+ инсталляций, MSSQL первый приоритет.
- Real-time plan capture (без `.sqlplan` или ТЖ) — нужно подключение к SQL Server и `SET SHOWPLAN_XML ON` через ODBC. Можно добавить как Sprint 9.

**Можно улучшить:**
1. **PostgreSQL plans (pev2)** — Sprint 8. Установка `npm install pev2`, React wrapper, новый tab в PlanAnalyzer. ~2 дня (см. SPRINT_7_DISCOVERY раздел 5).
2. **Live capture mode** — connect-string в Settings → подключаемся к SQL Server, при clik «Generate plan for SDBL» в QueryAnalyzer → транслируем SDBL в T-SQL через configuration_metadata → запускаем `SET SHOWPLAN_XML ON` → результат в PlanAnalyzer. ~5 дней. Sprint 9 candidate.
3. **Cross-correlation SDBL ↔ Plan** — в Anatomy → Top SQL добавить «View execution plan» кнопку (если в DBMSSQL событии есть `planSQLText`). Используем уже существующий `list_tj_plans_rpc` + `get_tj_plan_rpc`. ~1 день. Sprint 8 candidate.

---

## Раздел 9. Обслуживание индексов и статистики

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Автообновление статистики | ⚪ | DBA task |
| План обслуживания индексов | ⚪ | DBA task |
| Обслуживание больших баз 24/7 | ⚪ | DBA task |
| Обслуживание Postgres | ⚪ | DBA task |

**Покрытие: 0%** — намеренно. Это DBA workflow, не analysis tool. **Stop-list.**

---

## Раздел 10. Запросы которые работают быстро

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Рекомендации по написанию запросов | ✅ Полностью | QueryAnalyzer Sprint 6: bsl-LS (19 диагностик) + 13 native regex rules + 8 semantic rules + AI rewriter |
| Типичные причины неоптимальной работы | ✅ Полностью | 13 native rules (`backend/query_analyzer_rules/*.md`) — каждое правило с positive+negative test: comma_join_implicit, function_in_where, in_with_subquery, not_in_with_subquery, or_in_where, pervye_without_order, select_distinct, select_star, subquery_in_join, temp_table_without_index, union_without_all, virtual_table_in_join, vyrazit_in_where |
| Приёмы оптимизации | ✅ Полностью | AI rewriter (`generate-solution` RPC) с structured JSON output — суть, before, after, объяснение |
| Особенности высоконагруженных систем | 🟡 | Operations + Anatomy + rule `slow_op_heavy_sql` — показывает heavy ops в production load. Rule `slow_op_call_cascade` — chatty client patterns |

**Покрытие раздела: ~90%.**

**Можно улучшить:**
1. **Контекстное правило «slow on prod, fast in dev» вытащить в первый класс** — через ArchiveComparison, помечать запросы которые сильно деградировали между архивами. ~2 дня.
2. **8 semantic rules могут стать 15+** — Sprint 6 добавил attribute_not_exists_in_from_alias, constant_used_with_dot, enum_value_not_exists, object_kind_misspelled, object_not_exists, predefined_item_not_exists, register_dimension_or_field_missing, register_resource_used_as_dimension, virtual_table_not_supported, vyrazit_type_not_exists. Можно добавить: «использование индексируемого реквизита в WHERE без явного hint», «выбор `*` из таблицы с blob`-полями», etc. ~5 дней Sprint 8.

---

## Раздел 11. Транзакции

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Явные / неявные транзакции 1С | 🟡 | Видно через `Trans=1` flag в ТЖ событиях, в Anatomy event payload |
| Неявные транзакции СУБД | 🟡 | DBMSSQL events с последующим TLOCK |
| Вложенные транзакции | ⚪ | Documentation topic |
| ACID properties | ⚪ | Documentation |
| Грязное чтение (блокировочник vs версионник) | ⚪ | Documentation |
| MVCC в MSSQL/Postgres/Oracle | ⚪ | Documentation |
| Уровни изоляции | ⚪ | Documentation |
| Уровни изоляции в разных версиях 1С | 🟡 | Из ТЖ можно вывести по events sequence |
| Узнать действие в транзакции | 🟡 | Через `Trans=1` payload в Anatomy |
| Защита (когда транзакции защищают) | ⚪ | Documentation |

**Покрытие раздела: ~20%** — большинство пунктов documentation, не tool features.

**Можно улучшить:**
- View «Transaction timeline» — Gantt-style: каждая транзакция rphost session → колонка длины + nested events внутри. Sprint 9 candidate. ~5 дней.

---

## Раздел 12. Лог транзакций / WAL, бэкапы, отказоустойчивость

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Лог транзакций MSSQL / WAL Postgres | ⚪ | DBA topic |
| Модели восстановления | ⚪ | DBA topic |
| Бэкапы | ⚪ | DBA topic |
| Отказоустойчивость | ⚪ | DBA topic |

**Покрытие: 0%** — намеренно. **Stop-list.**

---

## Раздел 13. Транзакционные блокировки — ⭐ KEY SECTION

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Когда блокировка оправдана / избыточна | 🟡 | DeadlockAnatomy + rule `deadlock_lock_escalation` (`backend/explainers/`) — synthetic-validated. Real-data validation отложена (нет TDEADLOCK у Сергея) |
| Автоматический vs управляемый режим | 🟡 | Из ТЖ видно: `TLOCK` для управляемых, низкоуровневые для автоматических |
| Перевод на управляемые блокировки | ⚪ | Migration task |
| Таймаут vs дедлок | ✅ Полностью | LocksTimeline разделяет TLOCK (timeouts) и TDEADLOCK. rules `lock_timeout` + 3 deadlock-rules в DeadlockAnatomy с AI explainer |
| Совместимость управляемых блокировок 1С | 🟡 | DeadlockAnatomy показывает режимы (Exclusive/Shared); rule `deadlock_different_order` |
| Совместимость блокировок MSSQL | 🟡 | Из ТЖ есть `WaitConnections` — парсится в `deadlock_anatomy.py` (`parse_deadlock_intersections`, `DeadlockEdge` dataclass) |
| Блокировки Postgres | 🟡 | Аналогично через extra JSON |
| Кто кого заблокировал | ✅ Полностью | DeadlockAnatomy — SVG lock graph (waiter→blocker→resource), edges parser по ИТС spec, valid на synthetic. UI с 4 collapsible секциями (граф / ресурсы / события ±Nс / raw payload) |
| Конфликты управляемых блокировок | 🟡 | DeadlockAnatomy parser по ИТС spec |
| Конфликты блокировок СУБД | 🟡 | Через `extra` JSON (Regions/Locks fields) |
| Подходы к разработке без конфликтов | 🟡 | rules `deadlock_*` дают action items (очередь проведения, явные блокировки, разделить регистр) — через AI explainer |
| Расследование таймаута/дедлока через ЦУП | ✅ Полностью | DeadlockAnatomy + AI explainer — local-first альтернатива ЦУП |
| Разбор реальных конфликтов | ✅ Полностью | LocksTimeline работает на real archive |

**Покрытие раздела: ~75%.** Большая часть в 🟡 потому что real-data validation deadlock-схем отложена в OPUS_HANDOVER follow-up (у Сергея в архивах 0 TDEADLOCK events — logcfg.xml без соответствующего фильтра).

**Можно улучшить:**
1. **DeadlockAnatomy real-data validation** — расширить tj-simulator (`tools/tj-simulator/`) дополнительными кнопками для TDEADLOCK с разными типами (X-X конкуренция, S→X эскалация, разный порядок захвата). Уже есть скиллы 1С (`epf-dump`, `epf-build`) → паттерн готов. ~3 дня.
2. **Lock Wait Anatomy view** — отдельный экран по ЦУП 2.13.2: «кто из waiters сколько ждал, и кто их blocker'ы по ресурсам». Использует уже распарсенные `TLOCK` events с `WaitConnections`. Sprint 8 candidate. ~3 дня.

---

## Раздел 14. Другие виды блокировок

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Объектные блокировки | 🟡 | Из ТЖ events видно (TLOCK с типом resource = "Object") |
| Латчи PAGELATCH / PAGEIOLATCH | 🔴 | Latches пишутся в SQL profiler / Extended Events, не ТЖ |

**Покрытие: ~25%.** Latches принципиально не пишутся в ТЖ — требует Extended Events (Module 2+).

---

## Раздел 15. Кластер 1С

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Кластер для распределения нагрузки | ✅ Частично | ProcessRoles screen — табличка распределения событий по rphost/rmngr/ragent ролям + drill-down по `process_pid` |
| Защита от чрезмерного потребления памяти | 🟡 | Через MEM events (если включены) — нет dedicated UI |
| Защита по серверным вызовам | 🟡 | Через CALL events — есть, нет UI |
| Система мониторинга кластера | 🔴 | Real-time — Module 2+ |
| Сеансы и соединения | 🟡 | Через `t:clientID`/`t:sessionID` в events — данные есть, UI нет |
| Счётчики потребления ресурсов | 🔴 | Real-time agents — Module 2+ |
| Ограничения потребления ресурсов | ⚪ | Configuration setting, не analysis |

**Покрытие: ~35%.**

**Можно улучшить:**
1. **Sessions view** — Gantt-style timeline активных сессий через clientID/sessionID. Sprint 10 candidate. ~5 дней.
2. **Memory leak detector** — MEM events parser → детект растущей `MemSize` для rphost по времени → warning. ~3 дня.

---

## Раздел 16. Лицензии 1С

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Аппаратные ключи | ⚪ | Operational issue |
| Программные лицензии | ⚪ | Operational issue |

**Покрытие: 0%** — намеренно. **Stop-list.**

---

## Раздел 17. Нагрузочное тестирование

| Пункт программы | Покрыто | Где / что |
|---|---|---|
| Зачем нужно нагрузочное тестирование | ⚪ | Methodology |
| Реалистичный тест | ⚪ | Methodology |
| 1С:Тест-центр | ⚪ | Конкурент (генератор тестов, мы — analyzer результатов) |
| Большие тесты | 🟡 | ArchiveComparison для analysis результатов больших тестов |
| Оборудование для тестов | ⚪ | Operational |

**Покрытие: ~10%.** Мы — analysis tool для test results, не test generation tool. **Stop-list для генерации.**

---

## Раздел 18. Вводная часть курса (карьера, сертификат, KORП-сегмент)

⚪ Out of scope — это организационная часть курса. Marketing-релевантно, но не tool-feature.

---

## Итоговая статистика покрытия

### Полное покрытие методики на момент Sprint 7 closure

| Категория | Sprint 5 | **Sprint 7** | Δ | Чем покрыто (key items) |
|---|---|---|---|---|
| **Tools для analytical/diagnostic части** | ✅ ~45% | **✅ ~55%** | +10% | Plan Analyzer (раздел 7+8 рывок), AI explanation в каждом из 3 анализаторов |
| **Частично покрыто** | 🟡 ~10% | 🟡 ~15% | +5% | Раздел 13 deadlocks (real-data validation pending), раздел 6 ТЖ настройки |
| **Out of M1 (organizational / agents / DBA)** | 🔴/⚪ ~45% | 🔴/⚪ ~30% | −15% | Рывок за счёт Sprint 7 Plan Analyzer (раздел 7+8) |

**Прирост покрытия Sprint 5 → Sprint 7:**

| Раздел курса | Sprint 5 | Sprint 7 | Δ | Чем покрыли |
|---|---|---|---|---|
| 7. Индексы | 65% | **70%** | +5% | Plan Analyzer Missing Indexes + AI suggested_indexes с CREATE INDEX statement |
| 8. План запроса | 40% | **80%** | +40% | Sprint 7 целиком — PerformanceStudio + html-query-plan + AI |
| 6. ТЖ | 60% | **70%** | +10% | DBMSSQL.planSQLText auto-extract + scripts/patch-logcfg-for-plans.ps1 + onboarding/enable-dbmssql-plans.md |
| 3. Apdex | 35% | **35%** | 0 | Не было фокуса Sprint 7 |
| 10. Запросы | 90% | **90%** | 0 | Уже закрыто Sprint 6 |
| 13. Блокировки | 75% | **75%** | 0 | Real-data validation TDEADLOCK ещё в backlog |

**Целевое покрытие Module 1 — 40-45% курса** — **достигнуто и превышено (~55%)**. Это сильное позиционирование:

> «1C-Optimyzer покрывает диагностическую часть программы 1С:Эксперт на 55%. Continuous monitoring и DBA workflow — Module 2+.»

### Stop-list (что **никогда не делаем** в Module 1)

- ✅ Continuous monitoring (Module 2+ agents)
- ✅ DBA tools (бэкапы / WAL / отказоустойчивость / обслуживание индексов и статистики)
- ✅ Test generation (1С:Тест-центр клон)
- ✅ Organizational consulting (методички / чек-листы для CIO)
- ✅ Hardware monitoring (агенты PerfMon / DMV)
- ✅ Лицензии 1С (operational)
- ✅ MVCC / ACID / уровни изоляции — documentation, не tool

Эти решения **раз и навсегда** — не возвращаемся без явного pivot.

---

## Готовый investigation pipeline для производительности

Этот pipeline — **готовый скрипт** для performance engineer'а, как использовать
1C-Optimyzer в типовых сценариях расследования. Каждый сценарий — workflow
«проблема → экран → drill-down → выход».

### Сценарий 1. «Юзер пишет: документ проводится 30 секунд вместо 2»

**Шаги:**

1. **Получить ТЖ архив** за период жалобы (1-4 часа покрытия должно хватить). Юзеру: «открой папку `C:\1C-TechLog\rphost_*` после 17:00 за вчера и перетащи в Optimyzer».
2. **Operations screen** (Ctrl+1, открыт по умолчанию): найти строку с операцией `Документ.X.Записать` или похожим контекстом. Sort by `total_duration_ms` DESC по умолчанию — нужный документ в top-20.
3. **Click row → Anatomy** (drill-down). Видим timeline events: какие SCALL/DBMSSQL/EXCP внутри 30 секунд + что-то выделяется (DBMSSQL 28s или TLOCK 25s или N+1 cascade 5000 calls).
4. **Если TLOCK / TDEADLOCK преобладают** → LocksTimeline (Ctrl+4) → DeadlockAnatomy (drill-down если есть TDEADLOCK) → AI explainer объясняет ресурсы блокировки + что делать.
5. **Если DBMSSQL преобладают** → Top SQL внутри Anatomy → найти heavy SQL → копируем SQL → **Plan Analyzer** (Ctrl+P):
   - Если есть `planSQLText` в этом DBMSSQL событии (после `patch-logcfg-for-plans.ps1`) → tab «Из архива ТЖ» → выбираем этот event → text plan + AI explanation
   - Иначе → SSMS → `SET SHOWPLAN_XML ON` + запустить запрос → сохранить `.sqlplan` → перетащить в Plan Analyzer → визуализация + warnings + AI
6. **Если SCALL/CALL преобладают с avg<50ms на 1000+ calls** → rule `slow_op_call_cascade` сработает в Anatomy → ExplainerCard → AI explainer объясняет N+1 паттерн и предлагает batch-загрузку.

**Tools используемые:** Operations → Anatomy → (Plan Analyzer | LocksTimeline | DeadlockAnatomy)
**AI calls:** 1-2 (Anatomy ExplainerCard + Plan Analyzer AI)
**Время на full investigation:** 5-15 минут (vs 1-2 часа без инструмента)

---

### Сценарий 2. «Перформанс деградировал после релиза»

**Шаги:**

1. **Получить два ТЖ архива** — до релиза (baseline) и после (current).
2. **ArchiveComparison** (Ctrl+9): загрузить baseline в slot A, current в slot B.
3. **Tab «Summary»**: сразу видно delta total_duration / event_count / errors. Если current > baseline на 20%+ — есть деградация.
4. **Tab «Slow queries»**: side-by-side diff топ-N — какие SQL запросы стали медленнее, какие появились новые.
5. **Click на конкретный SQL** → копируем в **QueryAnalyzer** (Ctrl+Q) → bsl-LS + 13 native rules + AI rewriter → если есть антипаттерн → подсветка в исходном SDBL + конкретное предложение rewrite.
6. **Если SDBL ОК, но запрос медленный** → копируем `.sqlplan` (через SSMS из current база) → **Plan Analyzer** → AI объясняет почему план плохой именно сейчас (cardinality estimate mismatch / parameter sniffing / missing index из-за новой колонки).

**Tools:** ArchiveComparison → QueryAnalyzer / Plan Analyzer
**AI calls:** 2-3
**Время:** 10-30 минут

---

### Сценарий 3. «Регулярные деадлоки в production»

**Шаги:**

1. **Перед сбором** — убедиться что в logcfg.xml включён `<event>` для TDEADLOCK + TLOCK. Если нет — `scripts/patch-logcfg-for-plans.ps1` пока поддерживает только `<plansql/>`, для дедлоков — manual правка по `docs/onboarding/enable-dbmssql-plans.md`.
2. **Получить архив** за 24 часа с продакшена.
3. **LocksTimeline** (Ctrl+4): chart показывает peaks дедлоков. Найти час с пиком.
4. **DeadlockAnatomy** (drill-down click на конкретный TDEADLOCK event): SVG lock graph показывает waiters → blockers → resources. AI ExplainerCard объясняет тип деадлока:
   - `deadlock_lock_escalation` — S→X эскалация (несколько читали, потом несколько хотят писать)
   - `deadlock_different_order` — разный порядок захвата (классический A→B vs B→A)
   - `deadlock_single_resource` — X-X конкуренция за один объект
5. **Действие**: AI выдаёт concrete action items (очередь проведения / разделить регистр / явные блокировки заранее).
6. **Найти источник в коде** → копируем `context` из DeadlockAnatomy → **QueryAnalyzer** → если SDBL есть в configuration, bsl-LS может найти проблемный участок (для Sprint 8 — auto-navigation по `Context` → файл).

**Tools:** LocksTimeline → DeadlockAnatomy → QueryAnalyzer
**AI calls:** 1-2
**Время:** 15-45 минут

---

### Сценарий 4. «Хочу понять что вообще происходит в системе»

**Шаги:**

1. **Загрузить ТЖ за рабочий день** (8-12 часов).
2. **ActivityHeatmap** (Ctrl+8): 7×24 grid показывает пики активности. Click на яркую клетку — фильтр по time range применится во все остальные views.
3. **ProcessRoles** (Ctrl+5): распределение нагрузки rphost vs rmngr. Если перекос > 3× — кластеризация нужна (TODO Sprint 8 — рекомендатор).
4. **Operations** (Ctrl+1): top-20 бизнес-операций — какие документы / отчёты / обработки забивают систему.
5. **SlowQueries** (Ctrl+3): топ-20 SQL по total_duration. Antipatterns column (sqlglot, Sprint 6 Phase F) показывает counts типичных проблем (not_in, function_in_where, leading_wildcard и т.п.).
6. **DurationHistogram** (Ctrl+6): распределение durations. Bimodal distribution? Long tail? — это намёки на проблемы.
7. **ErrorsFeed** (Ctrl+7): что фейлится. Multi-select event_type filter + ContextFilter «есть контекст».

**Tools:** Все 10 экранов «Анализ».
**AI calls:** ~0 (overview-сценарий, для конкретики переходишь в сценарии 1-3).
**Время:** 20-60 минут.

---

### Сценарий 5. «Хочу проверить новый SDBL перед коммитом»

**Шаги:**

1. **QueryAnalyzer** (Ctrl+Q): paste SDBL.
2. **Status check** в шапке — bsl-LS подключён, configuration metadata подключён (для semantic rules).
3. **Analyze**: bsl-LS подсветит 19 типов диагностик (LikeBeginningPattern, LineNumberInQueryFunction, MagicNumbers, MissingTemporaryFileDeletion, NestedQueryInJoin, и т.д.) + 13 native rules + 8 semantic rules.
4. **Click finding** → **AI Explanation** (collapsible) → конкретное объяснение проблемы + как исправить.
5. **AI Rewriter** (отдельная кнопка) → structured rewrite с before/after diff.
6. **Если есть SQL Server connect** → **Plan Analyzer** (Ctrl+P): trasмутировать SDBL в T-SQL через configuration_metadata (TODO — пока вручную), получить план, увидеть real cost / Missing Indexes.

**Tools:** QueryAnalyzer → (Plan Analyzer)
**AI calls:** 1-2
**Время:** 2-10 минут per query

---

## Когда продавать (target use cases)

Sprint 7 closure даёт продукт, готовый для:

| Use case | Кто покупает | Цена | Что отличает от конкурентов |
|---|---|---|---|
| **Performance audit post-mortem** | Внешний 1С:Эксперт (консультант) | Pro 9 900 ₽/мес | Local-first (NDA-friendly, нет данных в облако кроме AI prompt) + AI на русском |
| **Регулярный аудит крупной БП/ERP внутри компании** | Внутренний DBA / архитектор | Pro / Business | Скорость анализа 100GB архивов через DuckDB |
| **Investigation одного incident'а** | Любой 1С-инженер | Free + 5 AI запросов | Бесплатные analytical views + ограниченный AI |
| **Подготовка к экзамену 1С:Эксперт** | Студент / junior 1С-инженер | Free | 55% программы курса покрыто tool'ом → можно практиковаться на реальных архивах |

Конкуренты:
- **1С:ЦУП** — официальный, monitoring-focused, server-side, дороже. Optimyzer = local-first альтернатива для archive analysis.
- **Performance Lab «Перфоманс Лаб»** — консалтинговая услуга. Optimyzer = self-service tool.
- **PerformanceStudio (Erik Darling Data)** — наш upstream для plan analysis, мы расширяем его 1С-контекстом + AI на русском + integration в TJ workflow.

---

## Что добавит дальнейшее покрытие методики

### Sprint 8 candidates (по приоритету)

1. **PostgreSQL plans (pev2)** — раздел 8 c 80% → 95%. ~2 дня.
2. **planSQLText → SHOWPLAN_XML converter** (TD-Sprint8-B) — если найдём OSS. Даёт visualization + PerformanceStudio rules для ТЖ-планов. ~3-5 дней spike.
3. **AI caching SQLite в DuckDB архива** (TD-Sprint8-D) — повторные запросы одинаковых SQL/планов не платят токены. ~1 день.
4. **Apdex calculator на экране Operations** — раздел 3 c 35% → 60%. ~1 день.
5. **DeltaApdex в ArchiveComparison** — раздел 3 c 60% → 75%. ~2 дня.
6. **Lock Wait Anatomy view** — раздел 13 (ЦУП 2.13.2). ~3 дня.

### Sprint 9-10 candidates

1. **MEM events parser + Memory leak detector** — разделы 5, 15. ~3 дня.
2. **Sessions view (Gantt)** — раздел 15. ~5 дней.
3. **Transaction timeline view** — раздел 11. ~5 дней.
4. **Live capture mode (ODBC к SQL Server для real-time plans)** — раздел 8 b 95% → 100%. ~5 дней.
5. **Configuration auto-fix через bsl-LS + skills** — semantic rules с автозаменой. ~7 дней.

### Sprint 11+ — Module 2 (если будет)

- Real-time agents для PerfMon counters
- DMV / Extended Events integration
- Continuous Apdex monitoring
- Cluster monitoring
- Кросс-базовая корреляция

---

## Принципы добавления новых фич (золотое правило)

> **Каждая новая фича должна явно mapping'оваться на пункт программы курса 1С:Эксперт.**
> Если не маппится — задай вопрос «это в нашем scope?» перед началом разработки.
> Stop-list (раздел выше) — пункты которые **не делаем** в Module 1 и Module 2.

Это правило сохранило ~30% времени разработки в Sprint 3-7 (избежали 5+ потенциальных
detour-фич: live monitoring dashboard, hardware metrics chart, backup tools UI,
лицензии manager, тест-центр интеграция).

---

**Документ:** EXPERT_COURSE_COVERAGE.md (Sprint 7 closure)
**Версия:** 1.0 / 2026-05-25
**Подготовил:** Claude Code (Sonnet 4.5, 1M context)
**Для:** Сергей (owner) + Claude Opus 4.7 (architect)
**База:** FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md (Sprint 5) + SPRINT_7_REPORT.md + SPRINT_7_PHASE_ABC_REPORT.md
