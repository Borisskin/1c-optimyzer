# Pre-prompt для Claude Code — 1C-Optimyzer (новая сессия)

> **Это первое сообщение в полностью новой сессии Claude Code.**
> Задача — настроить инфраструктуру нового проекта и извлечь готовый дизайн-концепт.

---

## Кто ты и кто я

Ты — **Claude Code**, исполнитель в нашей рабочей троице:
- **Архитектор:** Claude Opus 4.7 (отдельная сессия Claude.ai)
- **Исполнитель:** ты, Claude Code
- **Владелец:** Сергей — соло-фаундер, 1С-специалист с background в платформе и интеграциях

Мы уже работали вместе над проектом **Konvey** (`github.com/anymasoft/konvey`) — desktop-приложение для разработки правил обмена 1С через EnterpriseData (КД 3.1). Эта работа продолжается, текущий статус — Sprint 2.5 закрыт (98.9% real-data coverage), Sprint 3 запланирован как MVP completion.

**Этот проект — новый, параллельный.** Он не отменяет Konvey, он стартует как **второй продукт** Сергея.

---

## Новый проект: 1C-Optimyzer

### Кратко о продукте

**1C-Optimyzer** — desktop-приложение для real-time мониторинга, расследования и оптимизации производительности корпоративных систем 1С. Целевая аудитория — 1С:Эксперты по технологическим вопросам, DBA, senior 1С-разработчики, ИТ-директора компаний с корпоративными системами 1С (1С:ERP, КА, УПП, УХ, УТ-corp).

Категория продукта: **APM (Application Performance Monitoring) + Performance Engineering Workbench**, специализированный под 1С. Соединяет глубокую specialization на 1С (структура rphost'ов, сеансы, кластер, BSL, метаданные, ТЖ) с современным APM-стеком (real-time streaming, time-series storage, AI-driven insights, alerting).

Полный визионный документ с 18 ключевыми экранами — будет передан архитектором Opus в следующем сообщении (после того, как ты выполнишь эту задачу setup и архитектор получит доступ к дизайн-концепту).

### Стратегия разработки — модульный подход

Архитектор и владелец приняли **критическое стратегическое решение**: разработка **не идёт** «всё сразу как big bang». Вместо этого — **последовательный modular release**:

**Module 1 (первый MVP — будем строить сейчас): OptimyzerQL Standalone Tool**

Это **standalone desktop-приложение** для анализа технологического журнала 1С через специальный DSL (Domain-Specific Language) под названием **OptimyzerQL** (или OQL).

Что входит в Module 1:
- Desktop app для Windows (потом Linux/macOS)
- Drag-and-drop загрузка архива ТЖ (zip)
- Парсинг ТЖ в локальную базу (DuckDB)
- **OptimyzerQL DSL** — полная grammar, syntax highlighting, autocomplete, templates library
- Results view: Table / Chart / Timeline / Raw
- Saved queries, sharing, export (CSV / JSON / XLSX)
- Премиальный UI (из готового дизайн-концепта)

Что **НЕ входит** в Module 1:
- Real-time agents на production-серверах
- Central server и multi-base view
- Live monitoring и dashboards
- AI Co-pilot (опционально как micro-subscription, но скорее всего Module 2+)
- Investigation Workbench, Lock Graph, BSL Profiler, и т.д.

Этот узкий MVP даёт **максимальную скорость до launch** и **самостоятельную ценность** даже без всего остального стека.

**Module 2, 3, 4...** — будут добавляться последовательно после каждого validation cycle.

### Архитектура (общая)

- **Desktop client:** Tauri 2 + React/TypeScript (как у Konvey — тот же стек, тот же опыт работы)
- **Locale storage:** DuckDB (embedded) для парсенных ТЖ данных, SQLite для метаданных приложения
- **Парсер ТЖ:** Python sidecar (Pydantic + парсинг через regex/grammar)
- **Икл-формат деплоя:** один `.msi` инсталлятор, нулевые зависимости у пользователя
- **OptimyzerQL:** parser + interpreter на Python, который компилирует OQL → SQL для DuckDB

Зрелое архитектурное решение будет в Sprint 0 promt'е, сейчас это общий контекст.

---

## Working directory

**Все файлы проекта живут в `D:\1C-Optimyzer\`.**

Сергей уже создал эту папку. В ней могут уже быть подпапки:
- `D:\1C-Optimyzer\Design\` — папка с дизайн-концептами (в ней наш + другие дизайны Сергея, которые не относятся к этому проекту)
- Возможно ещё что-то

Не создавай файлы вне `D:\1C-Optimyzer\` без явной инструкции.

---

## Твоя задача сейчас (setup phase)

### Task 1: Найти наш дизайн-концепт

В папке `D:\1C-Optimyzer\Design\` лежат разные HTML файлы — это дизайн-концепты от Claude Design, которые Сергей делал в разное время для разных проектов. Один из них — **наш дизайн-концепт для 1C-Optimyzer**.

Как идентифицировать **наш** дизайн:
- Скорее всего самый свежий по дате создания (только что положил Сергей)
- Имя файла возможно содержит «Optimyzer» / «1C» / «1C-Optimyzer» / «monitoring» / «performance»
- Содержимое HTML — на тему **мониторинга производительности 1С** (видны темы: ТЖ, SQL queries, Apdex, deadlocks, rphost, OptimyzerQL Console и подобные)
- В файле упоминаются реальные 1С-объекты: `Документ.РеализацияТоваровУслуг`, `Справочник.Контрагенты`, `_AccumRgT5634` и т.п.

**Алгоритм:**
1. Сделай `dir D:\1C-Optimyzer\Design\` (или `ls`) — получи список файлов
2. Покажи Сергею список с датами модификации
3. Для самых свежих HTML — открой/прочитай первые 200-500 строк, проверь содержимое на match с темой 1C-Optimyzer
4. Когда нашёл наш дизайн — продолжи к Task 2
5. Если уверенности нет — спроси Сергея, какой именно файл

**Если в папке только один HTML файл** — это наш, пропускай ambiguity-check.

### Task 2: Создать GitHub репозиторий

Создай новый публичный репозиторий: **`anymasoft/1c-optimyzer`**

Если у тебя нет CLI access к GitHub (gh tool) — попроси Сергея создать репо вручную через github.com (Public, без README/gitignore/license initially) и потом продолжишь.

Структура изначального коммита (`main` ветка):

```
1c-optimyzer/
├── README.md                       # минимальный README (см. ниже)
├── design/
│   └── 1c-optimyzer-design-v1.html # наш дизайн-концепт (переименуй файл к этому имени)
├── docs/
│   ├── DECISIONS.md                # пустой шаблон ADR
│   ├── QUESTIONS.md                # пустой шаблон Q&A
│   └── ARCHITECT_NOTES.md          # пустой шаблон memory архитектора
└── .gitignore                      # стандартный для Python + Node + Tauri
```

### Task 3: Минимальный README.md

Создай `D:\1C-Optimyzer\1c-optimyzer\README.md` с таким содержимым (только русский, без английского):

```markdown
# 1C-Optimyzer

**AI-инструмент для мониторинга и оптимизации производительности корпоративных систем 1С.**

## Статус

Проект в активной разработке. Текущая фаза: **Module 1 — OptimyzerQL Standalone Tool** (Sprint 0).

## О продукте

1C-Optimyzer — desktop-приложение для real-time мониторинга, расследования и оптимизации производительности корпоративных систем 1С. Целевая аудитория — 1С:Эксперты по технологическим вопросам, DBA, senior 1С-разработчики, ИТ-директора компаний с корпоративными системами 1С (1С:ERP, КА, УПП, УХ, корпоративная УТ).

Категория продукта: APM (Application Performance Monitoring) + Performance Engineering Workbench, специализированный под 1С.

## Архитектура разработки

Продукт строится **модульно**, последовательным release'ом:

- **Module 1** (текущий MVP): OptimyzerQL Standalone Tool — анализ архивов технологического журнала 1С через специализированный DSL
- **Module 2+**: real-time agents, central server, live monitoring, AI Co-pilot, Investigation Workbench, и другие модули, которые будут добавляться после validation Module 1

## Команда

- **Архитектор:** Claude Opus 4.7
- **Исполнитель:** Claude Code
- **Владелец и domain expert:** Сергей

## Документация

- [Decisions (ADR)](docs/DECISIONS.md)
- [Open Questions](docs/QUESTIONS.md)
- [Architect Notes](docs/ARCHITECT_NOTES.md)
- [Design Concept](design/1c-optimyzer-design-v1.html) (открой в браузере)

## Лицензия

Коммерческий продукт. Все права защищены © 2026 anymasoft.
```

### Task 4: Шаблоны DECISIONS.md / QUESTIONS.md / ARCHITECT_NOTES.md

Создай три пустых документа с заголовками:

**`docs/DECISIONS.md`:**
```markdown
# Architectural Decisions (ADR) — 1C-Optimyzer

> Все принципиальные архитектурные решения проекта.

## ADR-001: [пока пустой, наполнится в Sprint 0]

(заполнится архитектором в Sprint 0)
```

**`docs/QUESTIONS.md`:**
```markdown
# Open Questions — 1C-Optimyzer

> Вопросы, требующие решения от владельца или дополнительной разведки.

## Q1: [пока пустой]
```

**`docs/ARCHITECT_NOTES.md`:**
```markdown
# Architect Notes — 1C-Optimyzer

> Observations и hypotheses архитектора между сессиями. Не для исполнителя, не ADR, не QUESTIONS — наблюдения по проекту, помогающие continuity между сессиями.

## Initial baseline (pre-Sprint 0)

Проект в фазе setup. Sprint 0 promt будет передан архитектором после изучения дизайн-концепта.

### Что архитектор уже знает про проект

- Модульный release strategy: Module 1 = OptimyzerQL standalone tool (analyzer архивов ТЖ)
- Стек технологий: Tauri 2 + React/TS + Python sidecar (как у Konvey)
- Working directory: D:\1C-Optimyzer\
- Дизайн-концепт готов, premium стиль (DataGrip / IntelliJ aesthetic, deep teal accent, Inter + JetBrains Mono шрифты)
- Целевая аудитория: 1С:Эксперты, DBA, senior 1С-разработчики

### Что архитектор хочет узнать после Task 1-4

- Точная структура дизайн-концепта (какие экраны там реализованы, mock-data, interaction patterns)
- Особенности UI решений в дизайне, которые надо отразить в архитектуре кода

### Открытые рабочие вопросы

- (заполнятся после изучения дизайна)
```

### Task 5: .gitignore

Стандартный для Python + Node + Tauri:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/

# Node
node_modules/
dist/
.next/
*.log

# Tauri
src-tauri/target/
src-tauri/Cargo.lock

# IDE
.idea/
.vscode/
*.swp
.DS_Store

# Build artifacts
*.msi
*.exe
*.dmg
*.AppImage

# Local data
*.db
*.duckdb
*.sqlite
.env
.env.local
```

### Task 6: Push в GitHub

После создания всех файлов:

1. `git init` в `D:\1C-Optimyzer\1c-optimyzer\`
2. `git add .`
3. `git commit -m "Initial setup: design concept + project structure"`
4. `git remote add origin https://github.com/anymasoft/1c-optimyzer.git`
5. `git branch -M main`
6. `git push -u origin main`

(Если GitHub auth не настроен — попроси Сергея.)

### Task 7: Подтверждение архитектору

После выполнения всех tasks — пришли Сергею **краткий status message** для передачи архитектору:

```
✅ Setup завершён. Репо: github.com/anymasoft/1c-optimyzer

Дизайн доступен по raw URL:
https://raw.githubusercontent.com/anymasoft/1c-optimyzer/main/design/1c-optimyzer-design-v1.html

(Для preview через браузер — clone repo и открой файл локально, либо GitHub Pages — настрою если попросишь)

Структура репо:
- README.md (минимальный, обзор проекта)
- design/1c-optimyzer-design-v1.html (наш концепт)
- docs/DECISIONS.md, QUESTIONS.md, ARCHITECT_NOTES.md (пустые шаблоны)
- .gitignore (Python + Node + Tauri)

Готов к Sprint 0 как только архитектор пришлёт promt.
```

---

## Что от тебя не требуется сейчас

- НЕ начинай разработку (это Sprint 0 — отдельный promt)
- НЕ устанавливай dependencies (Python venv, npm install и т.д.)
- НЕ создавай scaffold проекта (Tauri init, React init, etc.)
- НЕ настраивай Anthropic API key или other credentials
- НЕ запускай тесты
- НЕ создавай дополнительные docs кроме перечисленных выше

Просто **setup инфраструктуры** для архитектора, чтобы он мог изучить дизайн и спроектировать Sprint 0.

---

## Контекст работы (для Sprint 0 и далее)

Методология работы — та же, что у Konvey:

- **Архитектор** проектирует sprint promt'ы с epic'ами, acceptance criteria, ADR proposals
- **Исполнитель** (ты) реализует, держит дисциплину real-data testing, документирует решения в ADR / SPRINT_N_REPORT
- **Владелец** контролирует, даёт feedback, принимает strategic decisions

Каждый спринт — закрытый contract: список deliverables + acceptance criteria + лимит scope.

После каждого спринта — `OPUS_HANDOVER.md` (стандартный pattern, который мы делали в Konvey) для передачи в следующую сессию архитектора. Это часть мандатной работы исполнителя.

Архитектор работает без оценок времени — только в плоскости complexity / scope / dependencies. Не указывай в reports «займёт N часов / дней» — это бессмысленно с современным стеком Opus 4.7 + Claude Code.

---

## Дисциплина

- **Conventional commits** обязательны: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- **Один коммит = одна логическая единица работы.** Никаких «git add -A; git commit -m 'wip'» megacommits.
- **Документация в момент изменений**, не «потом задокументирую»
- **Тесты обязательны** для всего кода кроме одноразовых scripts (это будет важно в Sprint 0+, не сейчас)

---

## Готов к работе

Выполни Task 1-7. После завершения пришли краткий status message Сергею.

Архитектор ждёт raw URL дизайн-концепта на raw.githubusercontent.com — после изучения дизайна, спроектирую Sprint 0 promt с полным scope, epic'ами, acceptance criteria.

Удачи. Это **второй продукт** Сергея — пусть стартует так же чисто, как Konvey.
