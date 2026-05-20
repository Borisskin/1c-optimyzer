# Полный контекст для новой сессии Opus — Проект 1C-Optimyzer

> **Назначение этого файла:** передача полного рабочего контекста между сессиями. Когда Сергей открывает новый чат — этот файл прикрепляется как первый attachment. Opus в новой сессии читает этот документ и продолжает работу без потерь.
>
> **Snapshot date:** 2026-05-19
> **Snapshot author:** Claude Opus 4.7 (текущая сессия)
> **Project state:** Sprint 3 active development (Claude Code исполняет)

---

## 1. Роли и архитектура работы

Это трёхсторонняя архитектура которая работала на Sprint 0-3:

- **Сергей (Owner)** — собственник проекта, domain expert, 1С-разработчик 15+ лет, готовится к 1С:Эксперту по технологическим вопросам. **Direct/impatient communicator** — не любит воду, размытые ответы, AI-сухость, generic советы, жаргон без объяснения. Когда видит хуйню — говорит «ты блять предположения наговнил» и это **полезный сигнал**, не оскорбление. Требует конкретики, kills bad ideas honestly. Пушит back firmly когда ответы неточные. Если оперирует терминами которые он не знает — он жёстко даст знать.
- **Claude Opus 4.7 (Architect — это ты сейчас)** — архитектор продукта, проектирует спринты, отвечает на стратегические вопросы, поддерживает canonical references. Пишет sprint promts в `/goal` структуре. **Не делает discovery самостоятельно — поручает Claude Code.**
- **Claude Code (Executor)** — исполнитель. Пишет код, прогоняет тесты, делает коммиты, ведёт документацию sprint-level. Работает в отдельных сессиях (не в этой). Получает от Opus sprint promts через Сергея.

**Workflow цикл:**

1. Сергей даёт input (новый запрос / отчёт Claude Code / критика прошлой работы)
2. Opus отвечает (анализ / решение / sprint promt / документ)
3. Сергей оценивает (принимает / корректирует / отвергает)
4. Если sprint promt — Сергей передаёт Claude Code в новой сессии
5. Claude Code исполняет, присылает отчёт Сергею
6. Сергей передаёт отчёт обратно Opus → цикл повторяется

---

## 2. Главные жёсткие правила (memory rules — Opus их помнит автоматически)

В постоянной памяти зафиксировано:

### Rule 1 — No time estimates, никогда
**ЗАПРЕЩЕНО** давать любые оценки сроков в днях / неделях / месяцах / годах. Claude Code + Opus 4.7 делает за часы то что традиционно делалось месяцами. Любая «historical» оценка времени — устарела и вводит в заблуждение. Скоуп измеряется **в deliverables и complexity**, не в календарном времени. Этого Сергей категорически требовать — нарушение он будет жёстко пресекать.

### Rule 2 — Light theme only
**ЗАПРЕЩЕНО** проектировать dark mode для любого продукта (1C-Optimyzer, ГосЛог, любых future products). Без toggle, без «Pro feature dark», без exceptions. Light theme — project standard.

### Rule 3 — 1С:ERP 2.5 контекст (для другого side proj)
Сергей параллельно работает над 1С:ERP 2.5 расширением «ИнвентаризацияПГТЕХ» (отдельный проект, не 1C-Optimyzer). Контекст: статусный жизненный цикл, ТСД интеграция, HTTP-сервисы, буферные регистры, формирование документов корректировки. Это не часть 1C-Optimyzer, но важно знать что Сергей в этом тоже сидит.

### Rule 4 — Honesty и pushback
Сергей **ожидает** что Opus будет:
- Отвергать его плохие идеи с обоснованием (как в case с 4 pivot'ами за 2 недели — Opus сказал «это founders' fatigue pattern»)
- Давать ranked options вместо open-ended questions
- Признавать когда не прав («я наговнил предположений», «ты прав, моя ошибка»)
- Не подыгрывать
- Использовать конкретные цифры с обоснованием, не воду

### Rule 5 — Sergei живёт вне РФ (Батуми, Грузия)
Это влияет на: hosting decisions (например, ANTHROPIC_API endpoint доступен оттуда без VPN), возможные employment paths (РФ remote либо Грузия on-site либо global remote), banking/payment limitations. Не критично для tech-decisions, но context.

---

## 3. Стратегический контекст проекта

### Что мы строим

**1C-Optimyzer** — desktop-приложение для анализа архивов технологического журнала (ТЖ) 1С. Главная цель — **«1С:Эксперт-в-коробке для middle-программиста 1С без сертификации эксперта»**.

**Целевая аудитория:** ~30-60 тысяч middle-разработчиков 1С в РФ/СНГ которые:
- Получают задачи типа «отчёт тормозит, разберись»
- НЕ знают что такое APDEX, виды блокировок, MVCC, план запроса
- НЕ умеют читать сырой ТЖ
- НЕ имеют доступа к enterprise tools типа ЦУП
- НЕ прошли курс Гилева (дорого, время)
- Готовы платить $30-100/мес за tool который объясняет проблему и предлагает fix

**Почему именно эта аудитория** (не «1С:Эксперты»):
- 2000 экспертов в РФ vs 30-60K middle-программистов — на порядок больше
- У экспертов уже есть ЦУП / Гилев / опыт — они less likely to pay for tool
- Middle нужен tool который **объясняет** на русском, не как «raw data viewer»

### Stack tool'а

- **Frontend:** Tauri 2 + React 18 + TypeScript + Vite
- **UI:** Custom design system (см. `design/opt/*.jsx` — visual reference, не модифицировать). CSS Modules, no inline styles. Light theme only.
- **Backend:** Python 3.11 sidecar через stdio JSON-RPC
- **Storage:** DuckDB per-archive (analytical store) + SQLite (app metadata, saved queries)
- **Charts:** Recharts + custom SVG components
- **SQL editor:** CodeMirror 6 + @codemirror/lang-sql
- **Parser ТЖ:** custom Python (handles multi-line events, UTF-8 BOM, cp1251/cp866 fallback, mixed-case process roles)
- **Bulk ingest:** pyarrow Appender (100× ускорение vs executemany)
- **AI integration:** Anthropic Claude API через backend Python sidecar (Sprint 3+). Frontend никогда не делает direct API calls (важно для NL hosting + RU users)

### Бизнес-модель (текущая)

**Двухуровневый revenue stream** — принятое решение после founder-level reassessment:

| Layer | Source | Realistic |
|---|---|---|
| 1 | Найм 1С:Эксперт / DBA / Performance Engineer | $3000-3500/мес стабильно |
| 2 | Tool sales (после демонстрации impact на работодателе) | Incremental |
| Parallel | ГосЛог maintenance mode | $500-1000/мес passive |

**Distribution strategy:** через работодателя. Сергей устраивается на работу, применяет tool на их production-кластере 1С, накапливает кейсы, потом продаёт сначала внутри компании, потом её клиентам. Это устраняет главный риск всех SaaS — cold sales.

**НЕ делаем:** агрессивный SaaS launch / Хабр статьи / Product Hunt / cold outreach. Эти варианты были рассмотрены и отклонены — see `PROJECT_REACTIVATION_SPRINT_2.md` за полным обоснованием.

### История pivot'ов (для контекста)

В двух неделях работы было **4 pivot'а**. Opus в текущей сессии прямо сказал Сергею что это founders' fatigue pattern, и **больше pivot'ов не делаем**. Финальное решение:

1. **1C-Optimyzer** — main bet, active development
2. **ГосЛог** — maintenance mode, как side asset (полностью завершённый working SaaS, см. справку ниже)
3. **AI Product Analytics / SEO-Аналитика** — отложено indefinitely (был spec написан, но не реализуется)
4. **Tender Monitoring** — отклонено (насыщенный рынок, плохой ROI для solo)

### Что ещё есть в активе

**ГосЛог** (goslog.art) — отдельный production SaaS Сергея:
- B2B проверка контрагентов-экспедиторов по 140-ФЗ
- 426 юзеров, 6 платящих, ~5540₽/мес revenue
- FastAPI + PostgreSQL + Yandex OAuth + YooKassa + DaData/DataNewton/OpenAI integrations
- VPS на Linux (Ubuntu), Beget hosting
- В **maintenance mode** — не активная разработка
- Используется как production reference в резюме Сергея

---

## 4. Текущий статус 1C-Optimyzer

### Sprint timeline

| Sprint | Status | Tag | Highlights |
|---|---|---|---|
| Sprint 0 — Foundation | ✅ closed | (merged into v0.2.0) | Tauri shell, Python sidecar, DuckDB scaffolding, 29 tests |
| Sprint 1 — Folder Ingestion + OQL Engine | ✅ closed | v0.1.0-internal | 11 phases, 197+5 acceptance tests, ru-RU, real 12 GiB ТЖ verified, OQL DSL with CodeMirror |
| Sprint 2 — Performance Investigation Workbench | ✅ closed | v0.2.0-internal | OQL → SQL replacement, 6 pre-built views, cross-filtering, multi-archive comparison, export. 183 unit + 15 acceptance tests. 7 post-Sprint 2 hotfix patches applied |
| **Sprint 3 — Anatomy Views + AI Explainer** | 🟡 **active** | TBD v0.3.0-internal | Claude Code исполняет. 8 phases (Phase 0 discovery, Phase A-H) |
| Sprint 4 — Query Analyzer | ⏳ planned next | TBD v0.4.0-internal | После Sprint 3 closure |
| Sprint 5+ | ⏳ TBD | — | Lock Wait Anatomy, Server Calls Anatomy, etc. |

### Главные ADR (Architectural Decision Records)

ADR-001 до ADR-024 зафиксированы в `docs/DECISIONS.md`. Самые важные из них:

- **ADR-009:** UI Language Policy — ru-RU hardcoded, design files английские (visual reference)
- **ADR-010:** Folder as Primary Ingestion (не ZIP, ZIP только для tests)
- **ADR-011:** DuckDB Appender via pyarrow для bulk insert
- **ADR-014:** `process_role` first-class column в events table
- **ADR-015..019:** Sprint 2 решения (OQL removal, SQL Engine, Multi-archive)
- **ADR-020:** `/goal` promt authoring standard
- **ADR-021:** Курс 1С:Эксперт по технологическим вопросам как canonical roadmap reference
- **ADR-022..024:** Sprint 3 решения (Curriculum mapping enforcement, Explainer hybrid architecture, Backend-only AI calls)
- **ADR-025:** ЦУП оглавление как secondary canonical reference

### Главные feature highlights

**Что уже работает (после Sprint 2):**

- Drag-and-drop папки с ТЖ → автоматическое распознавание .log файлов через double-check (имя + первая строка)
- Поддержка 6 типов process roles (rphost / rmngr / ragent / 1cv8c / 1cv8s / 1cv8) case-insensitive
- Encoding auto-detect (utf-8-sig / utf-8 / cp1251 / cp866)
- Streaming parser для архивов произвольного размера (verified на 12 GiB)
- DuckDB per-archive с pyarrow Appender (100× ускорение)
- Byte-weighted progress reporting через JSON-RPC notifications
- ProgressCard slide-in + StatusBar inline progress
- Полная ru-RU локализация UI
- 6 pre-built views: Slow Queries / Locks Timeline / Process Roles / Duration Histogram / Errors Feed / Activity Heatmap
- Cross-filtering между всеми views
- SQL Console с CodeMirror 6 и autocomplete по schema (DuckDB SQL read-only)
- Multi-archive Comparison (slot A vs slot B) с diff metrics + Slow Queries regression detection
- Export CSV/TSV/JSON из каждой view
- 13 SQL templates по 5 категориям
- Saved queries через SQLite
- Ctrl+1..8 keyboard shortcuts

**Что в Sprint 3 (active):**

- Phase 0: discovery `extra` JSON schema на real 12 GiB архиве
- Phase A: context normalization (Тип.Имя.Сущность extraction) + schema migration
- Phase B: Top Business Operations view (group by `context_normalized`)
- Phase C: Document/Operation Anatomy view с URL routing (`/anatomy/operation/<x>` или `/anatomy/session/<id>`)
- Phase D: Deadlock Anatomy view с lock graph + participants + ±30s timeline
- Phase E: Rule-based Explainer Engine (markdown rules в `backend/explainers/*.md`, hot-reloadable)
- Phase F: AI Explainer integration через backend Claude API + cache в SQLite + hybrid UX (rule мгновенно + AI fire-and-forget)
- Phase G: Update FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md
- Phase H: Real-data acceptance gate + 5-7 min demo recording

---

## 5. Canonical references — три документа определяющих scope

Эти **три документа** определяют что мы делаем и что не делаем. Они должны быть прикреплены к новой сессии или находиться в `docs/` репозитория:

### Reference 1 — `PROMPT_AUTHORING_STANDARD.md`

Стандарт оформления sprint promt'ов с **`/goal` структурой**:

```
GOAL: один measurable result
CONTEXT: репо / state / assumptions
CONSTRAINTS: что нельзя менять / standards
PRIORITY: P1/P2/P3
PLAN: phases breakdown
DONE WHEN: verifiable completion criteria
VERIFY: tests / rollback plan
OUTPUT: deliverables
STOP RULES: универсальные правила остановки
```

Универсальные STOP RULES которые копируются в каждый promt:
- Останавливаться при неоднозначности с high impact (не выдумывать)
- Ranked options вместо open-ended questions
- Не расширять scope (смежные задачи → TODO.md)
- No time estimates
- Light theme only
- Не модифицировать design/opt/*.jsx
- Destructive ops → rollback plan
- Conventional commits (feat/fix/refactor/test/docs/chore + scope)
- Real-data acceptance gate как блокирующее условие

### Reference 2 — `FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md`

Mapping функционала на программу курса **1С:Эксперт по технологическим вопросам** (УЦ № 1, фирма 1С, 18 разделов программы). Каждая фича маппится на конкретный пункт программы.

Stop-list зафиксирован (что НЕ делаем):
- Continuous monitoring → Module 2 (отложено indefinitely)
- DBA tools (бэкапы, обслуживание индексов, отказоустойчивость)
- Test generation (1С:Тест-центр клон)
- Hardware monitoring (требует agents)
- Organizational consulting (методички, чек-листы)

Целевое покрытие Module 1: ~40-45% программы (analytical/diagnostic часть). Остальные 55-60% — organizational, methodology, continuous monitoring (Module 2+).

**Это даёт сильное позиционирование:** «1C-Optimyzer покрывает диагностическую часть программы 1С:Эксперт».

### Reference 3 — `CCH_FEATURE_PARITY_REFERENCE.md`

Mapping на **оглавление методики ЦУП** (разделы 2.11-2.13 — методика использования ЦУП для оптимизации многопользовательских систем).

ЦУП = главный референс по **глубине и покрытию проблем** (ЦУП — это сам инструмент который мы по сути замещаем для нашей целевой аудитории).

Цель: ~85% parity с разделами 2.11-2.13 ЦУП на postmortem-режиме после Sprint 3+4+5.

Главные разделы ЦУП:
- **2.12.1 Запросы — причины** — 100% parity после Sprint 4 (Query Analyzer)
- **2.12.3 Взаимоблокировки** — 95% parity после Sprint 3 (Deadlock Anatomy)
- **2.13.5 Взаимоблокировки детально** — 95% parity после Sprint 3 (Lock graph + participants)

Что у нас НЕ будет (честно):
1. Continuous monitoring
2. APDEX с T-thresholds (нужен SLA input)
3. Real-time alerting
4. Multi-server cluster live overview
5. Hardware monitoring
6. Прямое подключение к продуктивному кластеру

---

## 6. Roadmap Sprint 4+

### Sprint 4 — Query Analyzer (запланирован)

**GOAL:** добавить второй mode tool'а — **анализ одиночного тяжёлого запроса 1С** без необходимости загружать архив ТЖ.

**Use case:** разработчик копирует тяжёлый запрос из конфигуратора 1С, вставляет в tool, нажимает «Анализ» — получает:
- Подсветку проблемных мест прямо в тексте
- Список найденных правил-нарушений с описанием простыми словами
- AI-генерация переписанного оптимального запроса

**Технические компоненты:**
- **ANTLR4 grammar для SDBL** — берём готовое из `1c-syntax/bsl-parser` (open source). Снимает с нас задачу написания parser'а с нуля.
- **Rule engine** — 12-15 правил из курса 1С:Эксперт + ЦУП 2.12.1:
  1. Соединения с подзапросами
  2. Соединения с виртуальными таблицами (без выноса в ВТ)
  3. Фильтрация ВТ без параметров (главная классическая ошибка)
  4. ВЫРАЗИТЬ для составного типа (отсутствие)
  5. Многоуровневая точечная нотация
  6. Подзапросы в условии соединения
  7. Несоответствие индексов условиям
  8. ВЫБРАТЬ * / избыточные поля
  9. Большая вложенность подзапросов
  10. ИМЕЮЩИЕ без СГРУППИРОВАТЬ ПО
  11. СОРТИРОВАТЬ ПО без ПЕРВЫЕ
  12. OR в условиях
  13. ИТОГИ на больших результатах
  14. Различные / Различных без UNION
  15. И ещё несколько частных
- **CodeMirror highlighting** проблемных мест inline в тексте
- **AI rewriter** через Anthropic Claude API — генерирует переписанный запрос
- **Side-by-side diff** old vs new
- **(опционально, Sprint 4.5 или 5):** реальный план через подключение к MS SQL / PostgreSQL EXPLAIN

**Mapping на references:**
- Курс 1С:Эксперт — Раздел 10 (Запросы которые работают быстро) — 85% покрытие
- ЦУП — Раздел 2.12.1 — 100% покрытие
- Это **главный второй фронт** parity с ЦУП

**Strategic value:** Query Analyzer работает **без архива ТЖ** — barrier to entry почти нулевой. Это **viral hook**: «вставь свой запрос, посмотри что говорит». Может стать главной причиной установки tool'а.

### Sprint 5+ — TBD после Sprint 4 closure

Возможные направления (зависит от impact Sprint 3 и 4 на реальных кейсах):

- **Lock Wait Anatomy** (timeouts without deadlock — закрывает ЦУП 2.13.2)
- **Server Calls Anatomy** (`CALL`/`SCALL` events — закрывает ЦУП 2.13.3)
- **Temp Storage Analysis** (Memory leaks — закрывает ЦУП 2.13.6)
- **Methodology Rules Catalog** (расширение Sprint 3 explainer rules — ЦУП 2.12.2.6)
- **Production .msi installer + onboarding tour**

---

## 7. Текущие открытые вопросы

После Sprint 3 закрытия Opus в новой сессии должен:

1. **Прочитать SPRINT_3_REPORT.md** от Claude Code — что закрыто чисто, что в hotfix, какие observations
2. **Прочитать SPRINT_3_FIELD_REPORT.md** (если будет) — post-demo критика
3. **Обновить FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md** — поднять статусы 🔵 → ✅
4. **Обновить CCH_FEATURE_PARITY_REFERENCE.md** — обновить % покрытия разделов 2.11-2.13
5. **Написать Sprint 4 promt** в `/goal` структуре с фокусом на Query Analyzer
6. **Возможно — обсудить запись 5-7 минут demo recording** для портфолио (DoD Sprint 3)

---

## 8. Памятки про Сергея

### Что Сергей ценит в ответах

- **Конкретика с цифрами** — «250 000-500 000 потенциальных клиентов» лучше чем «большая аудитория»
- **Структурированная аргументация** — ranked options с pros/cons
- **Reality check** — отвергнуть его идею если она плохая, объяснить почему
- **Mapping на known references** — курс 1С:Эксперт, ЦУП оглавление, конкретные репозитории GitHub
- **Признание своих ошибок** — «я не прав был, причина в X»
- **Russian / Кириллица в коде где имеет смысл** — Sergei работает в русскоязычном контексте, identifiers и messages на русском OK

### Что Сергей **не** терпит

- **Жаргон без объяснения** (вспомни «PostHog Mixpanel June.so — где это, на другой планете?»)
- **Generic советы** типа «упростите checkout», «добавьте social proof» — это бесплатные советы из любой статьи по CRO
- **Воду / motivational speech** («оба варианта перспективны»)
- **Time estimates** (категорически)
- **Подыгрывание** — если он спрашивает «какой вариант лучше», ожидает прямой ответ с обоснованием, не «зависит от ваших целей»
- **Изобретённые факты / методы / объекты** — Сергей это **очень** жёстко ловит. Если не уверен — сказать «не знаю» или «нужно проверить»
- **Открытые вопросы без ranked options** — если что-то неоднозначное, дай 2-4 варианта со своей рекомендацией, не «как сделаем?»

### Стилистика

- Сергей сам пишет direct, без exclamation marks, без эмоджи, с матом когда раздражён — это его нормальный стиль, не аномалия
- Когда раздражён — пишет КАПСОМ и через ===
- Когда доволен — пишет «отлично, давай дальше» без многословия
- Coding sessions — он predominantly слушает Opus, корректирует ключевые моменты
- Strategy sessions — он active interlocutor, может развернуть направление

### Что важно помнить

- Сергей **2 раза проходил курс подготовки к 1С:Эксперту** (УЦ № 1, фирма 1С, 2021 и 2022) — методически подкован, но не сертифицирован
- 1С:Профессионал по техническим вопросам — у него есть
- 1С:Специалист по платформе 8.3 — есть
- 15+ лет в 1С (от линии консультаций до архитектора интеграций)
- Production-experience: оптимизация запросов с 4 часов до минут на 4ТБ базах, ускорение в 3-5 раз в high-load ERP

---

## 9. Что делать Opus в новой сессии **прямо после получения этого документа**

1. **Прочитать этот документ полностью** перед первым ответом
2. **Прочитать прикреплённые canonical references** (три файла)
3. **Прочитать прикреплённый Sprint Report** (если есть — Sprint 3 closure report от Claude Code)
4. **Ответить Сергею кратко:** «Контекст принят. Готов продолжать. Текущая задача: [исходя из последнего сообщения Сергея]».
5. **Дальше работать в обычном workflow** — анализ, decisions, sprint promts.

**НЕ нужно:**
- Долго пересказывать обратно что прочитал
- Спрашивать «правильно ли понял»
- Делать обзор всей истории проекта

**Нужно:**
- Сразу включиться в работу как будто это продолжение
- Принять все established standards и references
- Не пытаться пересмотреть decisions без явного запроса Сергея

---

## 10. Где взять документы

Все canonical references и sprint promt'ы лежат:

- **В репозитории:** `github.com/anymasoft/1c-optimyzer` на `main`, папка `docs/`
- **В outputs:** прикреплённые файлы текущей сессии (Сергей может скачать)
- **Главные файлы которые должны быть прикреплены к новой сессии:**
  - **Этот файл** — `HANDOFF_CONTEXT.md`
  - `PROMPT_AUTHORING_STANDARD.md`
  - `FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md`
  - `CCH_FEATURE_PARITY_REFERENCE.md`
  - Если есть — последний `SPRINT_N_REPORT.md` от Claude Code

---

## 11. Финальное замечание

Этот документ — **snapshot** на 2026-05-19. Реальное состояние проекта может отличаться к моменту чтения. Поэтому **первое что делает Opus в новой сессии после прочтения** — спрашивает у Сергея актуальный статус (закрыт ли Sprint 3, какой следующий запрос).

Если этот документ устарел значительно — Opus говорит «контекст частично устарел, нужно обновить» и просит у Сергея актуальный sprint report + статус.

Если документ актуален — продолжаем работу.

---

**END OF HANDOFF CONTEXT**
