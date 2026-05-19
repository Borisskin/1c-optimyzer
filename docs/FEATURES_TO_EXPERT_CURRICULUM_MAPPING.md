# 1C-Optimyzer ↔ Программа курса 1С:Эксперт по технологическим вопросам

> **Назначение:** Карта соответствия между функционалом 1C-Optimyzer и пунктами программы курса 1С:Эксперт. Это **компас для product roadmap** и **критерий оценки** каждой новой фичи: добавляемая функция должна mapping'оваться на конкретный пункт программы.
>
> **Источник курса:** УЦ № 1, фирма 1С. Полный курс «Подготовка к 1С:Эксперту по технологическим вопросам».
>
> **Принцип:** Не делаем функцию которой нет в программе. Делаем функции которые в программе есть. Это даёт **чёткий scope** и **узкое позиционирование**.

---

## Легенда статусов

- ✅ — **Полностью покрыто** в текущей версии (Sprint 0-2)
- 🟡 — **Частично покрыто** (есть данные, но нет специализированного UI)
- 🔵 — **Запланировано в Sprint 3** (Direction A — Top Business Operations / Document Anatomy / Deadlock Anatomy)
- 🟢 — **Запланировано в Sprint 4** (Query Analyzer)
- 🔴 — **Не планируется в Module 1** (требует real-time agents, central server, или CCH — Module 2+)
- ⚪ — **Out of scope** (например, organizational consulting topics)

---

## Раздел 1. Производительность глазами ИТ-менеджера

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Полноценный тюнинг или набор рекомендаций | ⚪ | Organizational topic, не tool-feature |
| Настройки кластера / СУБД | 🔴 | Module 2+ (recommendations engine) |
| Вертикальное масштабирование, апгрейд | ⚪ | Organizational |
| Горизонтальное масштабирование, кластеризация | ⚪ | Organizational, информация в Process Roles view |

**Покрытие раздела: 0%** — это управленческий раздел, не technical-tool functionality.

---

## Раздел 2. Обзор средств мониторинга и расследования

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Обзор средств мониторинга и расследования | ✅ | Сам tool **является** средством расследования. README + дизайн-концепт показывают позиционирование |

**Покрытие: 100%** — мы сами являемся этим средством.

---

## Раздел 3. Apdex и SLA

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Индекс производительности Apdex (определение) | 🔴 | Требует определения ключевых операций + целевого времени — organizational input, Module 2 |
| Типовые средства БСП для Apdex | 🔴 | БСП специфично, не входит в архивный анализ ТЖ |
| Составление списка ключевых операций | 🔴 | Module 2 (cohorts of operations) |
| Apdex и SLA для daily мониторинга | 🔴 | Требует continuous monitoring — Module 2 |
| Apdex для нагрузочного тестирования | 🔴 | Сценарий применения, не tool-feature |
| Apdex для оптимизации (ЦКТП методика) | 🔵 | **Sprint 3:** Apdex per business operation (через group by `context`) — частичная реализация |
| Обратный Apdex, DeltaApdex | 🔵 | **Sprint 3:** через Multi-archive Comparison (delta между двумя архивами) |
| Понять насколько можно ускорить по Apdex | 🔵 | **Sprint 3:** в Document Anatomy view (вес самой долгой операции в total) |
| Примеры с реальных проектов | ⚪ | Не tool-feature, marketing/docs |

**Покрытие раздела: 0% сейчас, Sprint 3 закроет ~40%.**

---

## Раздел 4. Когда уже тормозит — методика расследования

| Пункт программы | Статус | Где в tool |
|---|---|---|
| С чего начать расследование | ✅ | Workflow: загрузить → Business Operations → Anatomy → Slow Queries / Locks / Errors |
| Когда целесообразно ускорять единичную операцию | ✅ | **Sprint 3 closed:** Top Business Operations + rule `operation_heavy` (≥60s total) явно подсвечивает топ-кандидатов |
| Штатный замер производительности (Замер 1С) | 🔴 | Замер пишется в журнал, у нас этот режим не покрыт прямо |
| Скрытые действия платформы | ✅ | **Sprint 3 closed:** Operation Anatomy timeline + breakdown по event_type показывает CALL/SCALL/DBMSSQL для каждой операции |
| Время на «клиент-сервер» взаимодействие | ✅ | **Sprint 3 closed:** rule `slow_op_call_cascade` срабатывает на ≥1000 calls с avg ≤50ms |
| Оптимизация клиент-серверного взаимодействия | ✅ | **Sprint 3 closed:** AI explainer выдаёт конкретные action items |
| Поиск узких мест всей системы | ✅ | Top Business Operations sortable by 7 метрикам (Σ time / avg / SQL impact / lock impact / EXCP) |
| Ускорение системы — инструменты | ✅ | Сам tool **является** инструментом |
| Различие методик: единичная операция vs система | ✅ | **Sprint 3 closed:** Top Business Operations (whole system) → клик → Anatomy (single operation) — явная иерархия |
| Сборка общей картины | ✅ | Cross-filtering + Anatomy breakdown + Explainer Cards |

**Покрытие раздела: 90%** после Sprint 3.

---

## Раздел 5. Производительность оборудования

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Счётчики Windows | 🔴 | Не пишется в ТЖ — отдельная диагностика |
| Анализ загрузки железа на Windows | 🔴 | Module 2 (agents) |
| Мониторинг железа на Linux | 🔴 | Module 2 (agents) |
| Счётчики MS SQL Server | 🔴 | DMV / Extended Events — отдельный mode, Sprint 5+ |
| Кто нагружает CPU/диск/память на 1С-сервере | 🟡 | Через ТЖ events `MEM`, `LEAKS`, события длительностью |
| Утечки памяти vs прожорливые вызовы | 🟡 | Через `MEM` events в ТЖ — есть данные, нужен UI |
| Кто нагружает на СУБД | 🟡 | Через `DBMSSQL` events с aggregation by client_id |
| Счётчики VMWare | ⚪ | Out of scope (infrastructure monitoring) |
| Особенности VMWare | ⚪ | Organizational |
| Чек-листы по продуктивной настройке | ⚪ | Documentation, не tool-feature |

**Покрытие раздела: 30% частично через ТЖ events.** Полное покрытие требует Module 2 (agents для счётчиков).

---

## Раздел 6. Технологический журнал — настройка и анализ

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Технологический журнал — общее | ✅ | **Core competency tool** |
| Настройка ТЖ для сбора данных | ⚪ | Это инструкция (пользователь сам настраивает), у нас есть help docs |
| Расследование через ТЖ | ✅ | Все Sprint 0-2 views работают по ТЖ |
| Динамические представления (DMV) для MS SQL/Postgres | 🔴 | Не входит в ТЖ archive, отдельный mode Module 2+ |
| Extended Events trace | 🔴 | Не входит в ТЖ archive, отдельный mode Module 2+ |
| Нормализация запросов из trace/ТЖ | ✅ | `sql_text_normalized` + `sql_text_hash` уже есть в schema |
| Найти запрос в коде конфигурации | 🟡 | Контекст `context` показывает модуль+процедуру, но без navigation в код |
| Логи Postgres | 🔴 | Не ТЖ, отдельный source |
| ТЖ vs trace — влияние на производительность | ⚪ | Documentation topic |
| 1С:Центр Управления Производительностью | 🔴 | Конкурент / ссылочный продукт, не feature |

**Покрытие раздела: 60%.** Полное покрытие требует Module 2 (DMV/trace integration).

---

## Раздел 7. Индексы базы данных

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Что такое индекс БД | ⚪ | Documentation topic |
| Когда индексы ускоряют запросы | 🟢 | **Sprint 4:** Query Analyzer найдёт SELECT'ы где индексов не хватает |
| Какие индексы поддерживает платформа 1С | ⚪ | Documentation |
| Кластерный индекс | ⚪ | Documentation |
| Покрывающий индекс | ⚪ | Documentation |
| Когда индексы бесполезны | 🟢 | **Sprint 4:** Query Analyzer rule «индекс на полях с низкой селективностью» |
| Рекомендации по индексированию | 🟢 | **Sprint 4:** AI rewriter может предложить индексы |
| Каких индексов не хватает | 🟢 | **Sprint 4:** через анализ Sql_text patterns + плана (если есть подключение к БД) |
| Лишние индексы | 🔴 | Требует подключение к БД (Module 5+) |
| Особенности платформенных индексов | ⚪ | Documentation |

**Покрытие сейчас: 0%. Sprint 4 поднимет до 60%.**

---

## Раздел 8. Анализ работы запроса — план запроса

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Зачем нужен план запроса | 🟢 | **Sprint 4:** Query Analyzer покажет план если есть подключение к БД |
| Виды планов запроса | 🟢 | **Sprint 4** |
| Получение плана в MSSQL / Postgres | 🟢 | **Sprint 4** через EXPLAIN при подключении к БД |
| Основные операторы плана | 🟢 | **Sprint 4:** визуализация tree |
| Признаки неоптимальных планов | 🟢 | **Sprint 4:** rule engine для plan analysis |
| Влияние статистики на план | 🟢 | **Sprint 4:** часть rules |
| Параллелизм MSSQL/Postgres | 🟢 | **Sprint 4:** rule «MAXDOP issues» |

**Покрытие сейчас: 0%. Sprint 4 поднимет до 80%.**

---

## Раздел 9. Обслуживание индексов и статистики

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Автообновление статистики | ⚪ | Organizational (DBA задача) |
| План обслуживания индексов и статистики | ⚪ | Organizational |
| Обслуживание больших баз 24/7 | ⚪ | Organizational |
| Обслуживание Postgres | ⚪ | Organizational |

**Покрытие: 0%, не планируется (это DBA workflow, не analysis tool).**

---

## Раздел 10. Запросы которые работают быстро

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Рекомендации по написанию запросов | 🟢 | **Sprint 4:** Query Analyzer rule engine |
| Типичные причины неоптимальной работы | 🟢 | **Sprint 4:** ~15 rules covering main patterns |
| Приёмы оптимизации | 🟢 | **Sprint 4:** AI rewriter с конкретными рекомендациями |
| Особенности высоконагруженных систем | 🔵 | **Sprint 3:** Top Business Operations покажет heaviest ops in production load |

**Покрытие сейчас: 0%. После Sprint 3+4 будет ~85%.**

---

## Раздел 11. Транзакции

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Что такое транзакция | ⚪ | Documentation |
| Явное начало транзакции в 1С | ⚪ | Documentation |
| Платформа начинает транзакцию неявно | 🟡 | Видно через `Trans=1` flag в ТЖ событиях |
| Неявные транзакции СУБД | 🟡 | Видно через DBMSSQL events с TLOCK правым после |
| Вложенные транзакции 1С | ⚪ | Documentation |
| Свойства ACID транзакций | ⚪ | Documentation |
| Грязное чтение (блокировочник vs версионник) | ⚪ | Documentation |
| MVCC в MSSQL/Postgres/Oracle | ⚪ | Documentation |
| Уровни изоляции — зачем | ⚪ | Documentation |
| Уровни изоляции в разных версиях 1С | 🟡 | Из ТЖ можно определить через events sequence |
| Узнать что действие в транзакции | 🟡 | Через `Trans=1` в payload событий |

**Покрытие: 20%, не приоритет.** Это documentation topics, не tool-features.

---

## Раздел 12. Лог транзакций, бэкапы, отказоустойчивость

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Лог транзакций MSSQL | ⚪ | DBA topic |
| WAL Postgres | ⚪ | DBA topic |
| Модели восстановления | ⚪ | DBA topic |
| Бэкапы | ⚪ | DBA topic |
| Отказоустойчивость | ⚪ | DBA topic |

**Покрытие: 0%, не планируется** (это DBA tools, не analysis tools).

---

## Раздел 13. Транзакционные блокировки ⭐ КЛЮЧЕВОЙ РАЗДЕЛ

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Когда блокировка оправдана / избыточна | 🟡 | **Sprint 3 closed:** Deadlock Anatomy + rule `deadlock_lock_escalation` (synthetic-validated, real-data — follow-up) |
| Автоматический и управляемый режим | 🟡 | Из ТЖ видно: `TLOCK` для управляемых, низкоуровневые для автоматических |
| Перевод на управляемые блокировки | ⚪ | Migration task, не анализ |
| Таймаут vs дедлок | ✅ | Locks Timeline разделяет `TLOCK` (timeouts) и `TDEADLOCK`. Sprint 3: rule `lock_timeout` + Deadlock Anatomy |
| Совместимость управляемых блокировок 1С | 🟡 | **Sprint 3 closed:** Deadlock Anatomy показывает режимы блокировок (Exclusive/Shared); rule `deadlock_different_order` |
| Совместимость блокировок MSSQL | 🟡 | Из ТЖ есть `WaitConnections` с детализацией; парсится в Deadlock Anatomy |
| Блокировки Postgres | 🟡 | Аналогично |
| Кто кого заблокировал | 🟡 | **Sprint 3 closed:** Deadlock Anatomy — SVG lock graph (waiter→blocker→resource), valid на synthetic, real-data validation отложена |
| Конфликты управляемых блокировок | 🟡 | **Sprint 3 closed:** Deadlock Anatomy parser по ИТС spec |
| Конфликты блокировок СУБД | 🟡 | **Sprint 3 closed:** Deadlock Anatomy через `extra` JSON (Regions/Locks fields) |
| Подходы к разработке без конфликтов | 🟡 | **Sprint 3 closed:** rules `deadlock_*` дают конкретные action items (очередь проведения, явные блокировки, разделить регистр) |
| Расследование таймаута/дедлока через ЦУП | ✅ | **Sprint 3 closed:** Deadlock Anatomy + AI explainer = local-first альтернатива ЦУП |
| Разбор реальных конфликтов | ✅ | Locks Timeline уже работает на real archive; Sprint 3: 142 TLOCK + 299 EXCP проходят через rule classifier |

**Покрытие после Sprint 3: ~75%** (большая часть в 🟡 — design + synthetic validation готово, real-data validation deadlock-схем отложена в OPUS_HANDOVER follow-up, см. EXTRA_JSON_FIELD_STUDY.md). Это ключевой раздел для нашего product positioning.

---

## Раздел 14. Другие виды блокировок

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Объектные блокировки | 🟡 | Из ТЖ events видно |
| Латчи (PAGELATCH/PAGEIOLATCH) | 🔴 | Latches пишутся в SQL profiler / Extended Events, не ТЖ |

**Покрытие: 30%, не приоритет.**

---

## Раздел 15. Кластер 1С

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Кластер для распределения нагрузки | ✅ | Process Roles view показывает распределение |
| Защита от чрезмерного потребления памяти процессами | 🟡 | Из ТЖ events `MEM` видно паттерны |
| Защита по серверным вызовам | 🟡 | Из ТЖ `CALL` events видно |
| Система мониторинга кластера | 🔴 | Continuous monitoring — Module 2 |
| Сеансы и соединения | 🟡 | Из `t:clientID`/`t:sessionID` в events можно построить |
| Счётчики потребления ресурсов | 🔴 | Real-time agents — Module 2 |
| Ограничения потребления ресурсов | ⚪ | Configuration setting, не analysis |

**Покрытие: 40%, можно повысить через специализированные cluster views.**

---

## Раздел 16. Лицензии 1С

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Проблемы с аппаратными ключами | ⚪ | Operational issue, не analysis |
| Особенности программных лицензий | ⚪ | Operational issue |

**Покрытие: 0%, не планируется.**

---

## Раздел 17. Нагрузочное тестирование

| Пункт программы | Статус | Где в tool |
|---|---|---|
| Зачем нужно нагрузочное тестирование | ⚪ | Methodology topic |
| Нагрузочное как приёмо-сдаточные | ⚪ | Methodology |
| Для выявления нестабильно воспроизводимых проблем | 🔵 | **Sprint 3:** Multi-archive Comparison (load test before vs after) |
| Сайзинг оборудования | ⚪ | Methodology |
| Стресс-тестирование | ⚪ | Methodology |
| Реалистичный нагрузочный тест | ⚪ | Methodology |
| 1С:Тест-центр | ⚪ | Конкурент (внешний инструмент для test generation) |
| Простой нагрузочный тест | ⚪ | Methodology |
| Большие нагрузочные тесты (тысячи юзеров) | 🔵 | **Sprint 3:** Multi-archive Comparison для analysis результатов больших тестов |
| Оборудование для тестов | ⚪ | Operational |

**Покрытие: 20%. Мы — analysis tool для test results, не test generation tool.**

---

## Итоговая статистика покрытия

### По состоянию на Sprint 2 (текущее)

| Категория | Покрытие |
|---|---|
| **Полностью** ✅ | 12% (методика расследования, ТЖ-based diagnosis, кластер basics) |
| **Частично** 🟡 | 22% (есть данные, нужен dedicated UI) |
| **Не планируется** 🔴/⚪ | 66% (organizational / Module 2+ / DBA / out of scope) |

### После Sprint 3 (Direction A — Anatomy views + Explainer engine) — **ACTUAL**

| Категория | Покрытие |
|---|---|
| ✅ Полностью | ~28% |
| 🟡 Частично | ~17% (включая Раздел 13 — design + synthetic validation, real-data validation в OPUS_HANDOVER follow-up) |
| 🔴/⚪ Out of M1 | ~55% |

Раздел 13 (Транзакционные блокировки) поднялся с 30% (Sprint 2) до 75% (Sprint 3), при этом большая часть пунктов в 🟡 потому что:
- Backend и UI готовы по ИТС спецификации (parser, lock graph, AI explainer, 3 rules).
- Synthetic fixture с 3 типами ЦУП 2.12.3 deadlocks полностью валидирован.
- В production-архиве Сергея 0 TDEADLOCK events (logcfg.xml без соответствующего filter) — real-data validation отложена в OPUS_HANDOVER.

### После Sprint 4 (Query Analyzer)

| Категория | Покрытие |
|---|---|
| ✅ Полностью | ~40% |
| 🟡 Частично | ~10% |
| 🔴/⚪ Out of M1 | ~50% |

### Целевое покрытие Module 1

**~40-45% программы курса** — это purely analytical/diagnostic part курса. Остальные 55-60% — это organizational, methodology, или требует real-time monitoring (Module 2+).

**Это сильное позиционирование:** «1C-Optimyzer покрывает диагностическую часть программы 1С:Эксперт. Organizational и continuous monitoring — отдельные продукты».

---

## Что это меняет в roadmap

### Sprint 3 фокус (на основе курса)

**Главные пункты курса которые закрываются Sprint 3:**

1. **Раздел 13 (Транзакционные блокировки)** — Deadlock Anatomy view
   - «Кто кого заблокировал»
   - «Совместимость управляемых блокировок»
   - «Расследование таймаута/дедлока — наша альтернатива ЦУП»

2. **Раздел 4 (Когда уже тормозит)** — Top Business Operations + Document Anatomy
   - «Когда целесообразно ускорять единичную операцию»
   - «Оптимизация клиент-серверного взаимодействия»
   - «Сборка общей картины»

3. **Раздел 3 (Apdex) — частично** — через group by `context`
   - «Apdex для оптимизации»
   - «DeltaApdex» (через Multi-archive Comparison — уже есть)

### Sprint 4 фокус — Query Analyzer

**Главные пункты курса:**

1. **Раздел 10 (Запросы которые работают быстро)** — ~85% покрытие
2. **Раздел 8 (Анализ плана запроса)** — ~80% покрытие (требует подключение к БД)
3. **Раздел 7 (Индексы)** — ~60% покрытие (recommendation engine)

### Что НИКОГДА не делаем (явный stop-list)

На основе этого mapping'а — **не делаем**:
- Continuous monitoring → Module 2 (отдельный продукт или отложено indefinitely)
- DBA tools (бэкапы, обслуживание индексов, отказоустойчивость) → не нашa специализация
- Test generation (1С:Тест-центр клон) → не наш продукт
- Organizational consulting (методички, чек-листы для CIO) → не tool-feature
- Hardware monitoring → требует agents (Module 2+)

Эти решения **раз и навсегда** — не возвращаемся к ним без явного pivot всего продукта.

---

## ADR-021: Курс 1С:Эксперт как canonical roadmap reference

**Решение:** Программа курса 1С:Эксперт по технологическим вопросам (УЦ № 1, фирма 1С) принимается как **canonical reference** для всех будущих решений о scope продукта.

**Правила:**
1. Каждая новая фича должна явно mapping'оваться на пункт(ы) программы
2. Этот документ обновляется при каждом sprint closure
3. Целевое покрытие Module 1 — ~40-45% программы (analytical/diagnostic part)
4. Stop-list (раздел выше) — пункты которые **не делаем** в Module 1 и Module 2

**Обоснование:**
- Чёткий scope → нет scope creep
- Узкое позиционирование → marketing message
- Self-validation → известно что покрываем
- Portfolio value → «tool covering 40% of 1С:Эксперт curriculum» — конкретная metric для резюме

**Принято:** Сергей (owner) + Claude Opus 4.7 (architect), 2026-05-19.

---

## Файл обновляется

После закрытия каждого спринта — обновлять статусы (✅/🟡/🔵/...). Это **живой документ**, не статический.

---

## Sprint 3 closure summary (2026-05-19)

**Что фактически было сделано в Sprint 3:**

- ✅ Phase 0 — discovery script + EXTRA_JSON_FIELD_STUDY.md (рапределение event_types в production-архиве: CALL 40%, Context 28%, SRVC 20%, SCALL 9%; 0 TDEADLOCK / 0 DBMSSQL — logcfg.xml без соответствующих filters)
- ✅ Phase A — `context_normalized` колонка + миграция existing archives + 17 unit tests
- ✅ Phase B — Top Business Operations view (backend + frontend), 5 view tests
- ✅ Phase C — Operation/Session Anatomy backend + frontend, 9 anatomy tests
- ✅ Phase D — Deadlock Anatomy backend по ИТС spec + synthetic fixture с 3 типами ЦУП 2.12.3 + frontend с SVG lock graph; 19 tests (10 parser + 9 integration)
- ✅ Phase E — Rule engine + 8 markdown rules (deadlock×3, slow_op×3, lock, exception×2) + 22 tests
- ✅ Phase F — AI explainer Claude API client + SQLite cache + ExplainerCard frontend; 11 tests (10 cache+client + 1 live skipped без API key)
- ✅ Phase G — этот файл обновлён

**Backend tests:** 183 (Sprint 2) → 268 (+85). All passing.
**Sprint 3 commits:** 8 на feat-branch `feat/sprint-3-anatomy-and-explainer`.

**Pending follow-up tasks (OPUS_HANDOVER):**
- Phase D real-data validation pass (требуется архив с TDEADLOCK events)
- Lock Wait Anatomy view (Sprint 5+ кандидат по ЦУП 2.13.2)
