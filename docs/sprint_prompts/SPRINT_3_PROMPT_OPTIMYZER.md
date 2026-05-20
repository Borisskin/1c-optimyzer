# Sprint 3 — Business Anatomy Views + AI Explainer

> **Контекст:** Sprint 2 закрыт (tag v0.2.0-internal), 11 phases, 183 unit + 15 acceptance tests passing. Field Report (commit 6b5eb0b) выявил что product сейчас — «SQL-консоль над ТЖ для тех кто понимает структуру». Sprint 3 переводит его в **«1С:Эксперт-в-коробке для обычного 1С-программиста»** через 3 anatomy views с AI explainer.
>
> **Working directory:** `D:\1C-Optimyzer\1c-optimyzer\`
> **Branch:** `feat/sprint-3-anatomy-and-explainer` (от main, tag v0.2.0-internal)

---

## /goal

### GOAL

Превратить 1C-Optimyzer из data-first инструмента в **explainer-first инструмент для middle-программистов 1С без сертификации эксперта**. Конкретно:

1. Добавить 3 anatomy views: Top Business Operations (group by нормализованному `context`), Document/Operation Anatomy (drill-down по session_id + операция), Deadlock Anatomy (детальный разбор каждого TDEADLOCK)
2. Каждая anatomy view имеет **explainer layer** сверху — человеко-читаемое объяснение происходящего на русском, понятное middle-программисту без знания методики 1С:Эксперта
3. Explainer = гибрид rule-based classifier + AI generation. Rule catalog живёт в `explainers/*.md` (markdown files). AI работает через backend Claude API call с кешем
4. Поднять покрытие курса 1С:Эксперт в `FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` с ~25% до ~40% (особенно Раздел 13 — Транзакционные блокировки — с 30% до 80%)

**Measurable outcome:** middle-программист 1С без сертификации эксперта открывает anatomy view → понимает причину торможения → видит конкретный actionable next step. **Без чтения курса 1С:Эксперт.**

### CONTEXT

**Состояние после Sprint 2 (baseline для Sprint 3):**

- Tag v0.2.0-internal на main, merge commit `b7fccbd`
- 6 pre-built views работают: Slow Queries / Locks Timeline / Process Roles / Duration Histogram / Errors Feed / Activity Heatmap
- Cross-filtering работает между views (shared state в FilterBar)
- Multi-archive Comparison работает (slot A + slot B + diff)
- SQL Engine read-only (sqlparse validator, max 100K rows, 30s timeout)
- CodeMirror SQL editor с autocomplete по schema из DuckDB
- Charts library (5 Recharts wrappers + custom SVG Heatmap)
- Export CSV/TSV/JSON из каждой view
- ru-RU локализация полная
- 183 unit tests + 15 env-gated acceptance — все зелёные
- 7 post-Sprint 2 hotfix patches применены (UI layout, DuckDB read_only, reattach archive, SchemaPanel, ErrorsFeed expand, real cancel ingestion)
- Tauri 2 + React 18 + Python sidecar + DuckDB + SQLite — без изменений

**Стратегические решения принятые перед Sprint 3:**

- **ADR-021 (mapping document):** курс 1С:Эксперт по технологическим вопросам — canonical roadmap reference. `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновляется после каждого спринта
- **Direction A** выбрано из 4 направлений Field Report (Q1) — Anatomy views на сырых данных без архитектурных изменений
- **Позиционирование:** «1С:Эксперт-в-коробке для middle-программиста 1С без сертификации». Целевая аудитория — ~30-60 тыс. middle-разработчиков в РФ/СНГ, не ~2000 сертифицированных экспертов
- **Stop-list (ADR-021):** continuous monitoring, DBA tools, test generation, hardware monitoring, organizational consulting — НЕ делаем никогда в Module 1
- **Explainer engine:** rule-based classifier + AI conversational generator работают параллельно. Rule = identifies pattern, AI = writes natural language explanation with rule context
- **Claude API calls:** только backend (Python sidecar). Frontend никогда не знает API ключ. Учитывает потенциальный hosting NL + users RU
- **AI explainer UX:** гибрид fire-and-forget — открытие anatomy view → rule-based explainer показывается мгновенно → AI запрос в фоне → через 3-5 сек AI explanation замещает/дополняет rule-based. Кеш per `(archive_id, anatomy_kind, target_id)`

**Field Report findings которые применяем:**

- Поле `context` несёт бизнес-смысл (`Документ.РеализацияТоваровУслуг.МодульОбъекта`) — но в Sprint 2 НЕ нормализован для group by. Sprint 3 решает (Q2 ответ: regex `^([^:]+?)(\s*:.*)?$` оставляет `Тип.Имя.Сущность`, отбрасывает `: line : statement`)
- Drill-down UX = отдельный экран с URL `/anatomy/<event_id>` (Q3 ответ: shareable, browser history works, deep drill-down)
- Real schema `extra` JSON в TJ архивах нужна разведка (Q4 — Phase 0 Sprint 3)
- N>2 archives отложено (Q5 — не Sprint 3)
- Позиционирование «investigation workbench для 1С:Эксперта-в-коробке» (Q6 — финал)
- Demo recording после Sprint 3 closure (Q7 — текущий Sprint 2 demo less compelling, после anatomy views будет business-oriented история)

**Ключевые файлы которые трогаем:**

- `backend/src/optimyzer_backend/parsers/tj_parser.py` — добавить `context_normalized`
- `backend/src/optimyzer_backend/storage/duckdb_store.py` — schema migration: новая колонка `context_normalized`, новые индексы
- `backend/src/optimyzer_backend/views/` — 3 новых модуля (operations / anatomy / deadlock_anatomy)
- `backend/src/optimyzer_backend/explainer/` — **новый пакет** (rule engine + Claude client)
- `backend/explainers/` — **новая папка с markdown файлами** правил
- `frontend/src/components/screens/Operations/` — Top Business Operations
- `frontend/src/components/screens/Anatomy/` — Document/Operation Anatomy с URL routing
- `frontend/src/components/screens/DeadlockAnatomy/` — Deadlock Anatomy
- `frontend/src/components/explainer/ExplainerCard.tsx` — общий компонент explainer layer
- `frontend/src/i18n/ru.ts` — новые strings
- `frontend/src/components/chrome/Sidebar.tsx` — enable новые views
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` — обновить статусы
- `docs/EXTRA_JSON_FIELD_STUDY.md` — результат Phase 0 discovery
- `docs/DECISIONS.md` — ADR-022, 023, 024
- `.env.example` — добавить `ANTHROPIC_API_KEY`

### CONSTRAINTS

**Глобальные (universal):**
- CSS Modules, no inline styles
- ru-RU локализация в `i18n/ru.ts` (signature совместимо с future i18n framework)
- Conventional commits (feat/fix/refactor/test/docs/chore) с scope
- No time estimates anywhere
- Light theme only — dark theme FORBIDDEN
- Не модифицировать `design/opt/*.jsx` (visual reference)
- ADR-001..021 в силе (не пересматривать)
- Conventional commits — один логический commit = один scope, никаких mega-commits

**Sprint 3 специфичные:**
- Claude API calls ТОЛЬКО из backend Python sidecar. Никаких прямых fetch к api.anthropic.com из frontend
- `ANTHROPIC_API_KEY` читается из `.env` или environment variable. Создаётся `.env.example` с пустым значением. Реальный `.env` в `.gitignore`. Tool fails gracefully если ключ не указан — explainer показывает только rule-based, AI отключен
- `explainers/*.md` файлы хранятся в репозитории под git version control. Hot-reload в runtime backend (если меняется .md — backend перечитывает без рестарта)
- AI cache — SQLite table `explainer_cache` (отдельный SQLite db `data/explainer_cache.db` или integration с existing app SQLite store)
- AI API timeout — 15 секунд. Если timeout — показываем только rule-based explainer + retry button
- AI response max tokens — 1024 (достаточно для 3-4 параграфов объяснения)
- Sprint 3 НЕ трогает существующие Sprint 2 views (Slow Queries / Locks Timeline / ...). Они работают как было

**Запрещено в Sprint 3:**
- Не делать Query Analyzer (Sprint 4 scope)
- Не делать APDEX/SLA computations (Direction B отложен)
- Не делать file watcher / continuous monitoring (Direction C исключён)
- Не расширять multi-archive comparison до N>2 (Direction D отложен)
- Не интегрировать DMV / Extended Events / Postgres logs (Module 2+)
- Не делать onboarding tour (отложен на Sprint 5 или позже)

### PRIORITY

- **P1 (блокирующее закрытие Sprint 3):** Phase 0 discovery, Phase A normalization, Phase B Top Business Operations, Phase C Document Anatomy, Phase D Deadlock Anatomy, Phase E Rule-based explainer engine, Phase F AI explainer integration с кешем, Phase H acceptance gate
- **P2 (важно но не блокирующее):** Phase G обновление curriculum mapping document
- **P3 (nice-to-have):** Sidebar polish, новые keyboard shortcuts для anatomy navigation

### PLAN

**Phase 0 — Discovery: реальная схема `extra` JSON и event_type распределение**

Цель: получить fact-based input для Phases C и D, не работать на гипотезах.

Создать `backend/scripts/inspect_extra_json.py` который:
1. Идёт по реальному архиву (path из `.env.test` или command line arg)
2. Группирует events по `event_type`, считает распределение
3. Для top-10 event_types — собирает schema всех полей в `extra` JSON с примерами значений
4. Для `TDEADLOCK` и `TLOCK` отдельно — полная schema всех ключей с типами и frequency
5. Для `EXCP` — распределение Exception types и Descr patterns
6. Записывает результат в `docs/EXTRA_JSON_FIELD_STUDY.md`

Output формат:

```markdown
# Extra JSON Field Study — реальный архив

## Event type distribution (12 GiB архив)

| Event Type | Count | % |
|---|---|---|
| DBMSSQL | 8 234 567 | 67% |
| CALL | 2 145 233 | 18% |
| TLOCK | 567 234 | 5% |
| ... | | |

## TDEADLOCK schema

| Field | Frequency | Type | Example |
|---|---|---|---|
| WaitConnections | 100% | string | "12345,67890" |
| Regions | 100% | string | "Документ.РеализацияТоваровУслуг.Записи" |
| ... | | | |

## Common patterns

(семейства паттернов: "deadlock between 2 sessions on regional lock", "timeout on object lock", ...)
```

Этот документ — **критический input** для design Phase C и D. Без него мы гадаем.

**Phase A — Context normalization + schema migration**

В `backend/src/optimyzer_backend/parsers/tj_parser.py`:

```python
import re

CONTEXT_NORMALIZE_RE = re.compile(r'^([^:]+?)(?:\s*:.*)?$')

def normalize_context(raw_context: str | None) -> str | None:
    """Нормализация поля context из ТЖ к виду 'Тип.Имя.Сущность'.
    Отбрасывает '<line> : <statement>' часть.
    """
    if not raw_context:
        return None
    match = CONTEXT_NORMALIZE_RE.match(raw_context.strip())
    return match.group(1).strip() if match else raw_context.strip()
```

Применить в parser при insert event'а — заполнять новую колонку `context_normalized`.

Schema migration в `DuckDBStore`:

```sql
ALTER TABLE events ADD COLUMN IF NOT EXISTS context_normalized VARCHAR;

-- Backfill для existing archives
UPDATE events 
SET context_normalized = regexp_replace(context, '^([^:]+?)(\s*:.*)?$', '\1')
WHERE context IS NOT NULL AND context_normalized IS NULL;

CREATE INDEX IF NOT EXISTS idx_events_context_norm 
ON events(archive_id, context_normalized);
```

Migration выполняется автоматически при первом запуске Sprint 3 на existing archive. Для новых ingest'ов (после Sprint 3) — заполняется при insert.

Тесты: 5+ unit tests на `normalize_context` (edge cases: empty, no colon, multi-colon, whitespace, Cyrillic).

**Phase B — Top Business Operations view**

Backend `backend/src/optimyzer_backend/views/operations.py`:

```python
def get_top_business_operations(
    archive_id: str,
    time_range: tuple[str, str] | None = None,
    process_role: str | None = None,
    limit: int = 50,
    sort_by: str = 'total_duration_ms',
) -> dict:
    """Группировка событий по нормализованному context."""
    sql = """
    SELECT 
        context_normalized AS operation,
        COUNT(*) AS calls,
        SUM(duration_us)/1000.0 AS total_duration_ms,
        AVG(duration_us)/1000.0 AS avg_duration_ms,
        MAX(duration_us)/1000.0 AS max_duration_ms,
        SUM(CASE WHEN event_type = 'DBMSSQL' THEN duration_us ELSE 0 END)/1000.0 AS sql_duration_ms,
        SUM(CASE WHEN event_type IN ('TLOCK','TDEADLOCK') THEN 1 ELSE 0 END) AS lock_events,
        SUM(CASE WHEN event_type = 'EXCP' THEN 1 ELSE 0 END) AS exception_events,
        COUNT(DISTINCT session_id) AS unique_sessions,
        COUNT(DISTINCT process_role) AS unique_process_roles
    FROM events
    WHERE archive_id = ?
      AND context_normalized IS NOT NULL
    """
    # ... filters, ORDER BY, LIMIT
```

Frontend `Operations.tsx`:
- Filter bar (time range, process role) — переиспользует cross-filtering из Sprint 2
- Main table: operation name, calls, total time, avg time, sql%, lock count, exception count
- Sort selector: total time / avg time / count / sql impact / lock impact
- Click on row → navigate to `/anatomy/operation/<operation_url_encoded>`
- Color hints: heavy red если operation > 30% archive total, amber > 10%
- Export CSV (наследует Sprint 2 export)

Mapping на курс: Раздел 4 «Когда уже тормозит» (когда целесообразно ускорять отдельную операцию), Раздел 3 «Apdex для оптимизации» (частично — без T-targets).

**Phase C — Document/Operation Anatomy view**

URL routing: `/anatomy/operation/<context_url_encoded>` или `/anatomy/session/<session_id>`.

Backend `backend/src/optimyzer_backend/views/anatomy.py`:

```python
def get_operation_anatomy(
    archive_id: str,
    operation: str,           # normalized context
    limit_sessions: int = 20, # последние N сессий этой операции
) -> dict:
    """Анатомия операции — все её executions + breakdown."""
    
    # 1. Summary: количество executions, avg/max/min duration, success rate
    # 2. Timeline: top-20 последних executions (timestamp + duration + status)
    # 3. Breakdown: где время уходит — SQL queries / lock waits / exceptions
    # 4. Top SQL inside this operation (group by sql_text_hash)
    # 5. Связанные exceptions
    
def get_session_anatomy(
    archive_id: str,
    session_id: str,
) -> dict:
    """Анатомия конкретной сессии — timeline events + breakdown."""
    # 1. Header: session_id, user_name, process_role, начало/конец, total events
    # 2. Timeline: все events этой сессии в порядке (с группировкой повторов)
    # 3. Where time was spent: SQL/locks/exceptions percentage
    # 4. Slowest SQL queries inside session
    # 5. Errors timeline
```

Frontend `Anatomy.tsx`:
- React Router route: `/anatomy/operation/:operation` и `/anatomy/session/:sessionId`
- Header card: summary metrics + позитивные/негативные indicators
- **ExplainerCard sticky наверху** (Phase E-F)
- Timeline component — vertical timeline события за событием
- Breakdown chart (DonutChart): «70% SQL, 20% locks, 10% other»
- Top SQL table — top-10 medlennejshих запросов внутри операции
- Cross-link: clicking SQL row → Sprint 2 Slow Queries с filter pre-applied

Mapping на курс: Раздел 4 «единичная операция», «сборка общей картины», Раздел 6 «расследование через ТЖ».

**Phase D — Deadlock Anatomy view**

Используем results Phase 0 (real `extra` JSON schema для TDEADLOCK).

Backend `backend/src/optimyzer_backend/views/deadlock_anatomy.py`:

```python
def get_deadlock_anatomy(archive_id: str, deadlock_event_id: str) -> dict:
    """Полный разбор одного TDEADLOCK события."""
    
    # 1. The TDEADLOCK event itself: timestamp, context, extra JSON parsed
    # 2. Participants — extract from WaitConnections / DeadlockConnectionIntersections
    # 3. Resources — extract from Regions / Locks JSON (схема из Phase 0)
    # 4. Lock graph — кто кого ждал (можно построить DAG из participants + resources)
    # 5. Surrounding events — ±30 сек до и после с участниками
    # 6. Related context — какие операции были у участников перед deadlock
```

Frontend `DeadlockAnatomy.tsx`:
- URL: `/anatomy/deadlock/:eventId`
- Header: timestamp, operation context, lock mode
- **ExplainerCard sticky** (Phase E-F)
- Lock graph visualization (простой SVG: 2-3 boxes для участников + arrows ресурсов между ними)
- Participants table: session_id, user_name, process_role, что делал, какой lock хотел
- Resources table: что блокировал каждый
- Timeline ±30 сек: список events до/после deadlock с timestamp

Mapping на курс: **Раздел 13 «Транзакционные блокировки» — core deliverable**. Покрывает: «кто кого заблокировал», «совместимость блокировок», «расследование таймаута/дедлока — наша альтернатива ЦУП».

**Phase E — Rule-based Explainer Engine**

Backend `backend/src/optimyzer_backend/explainer/`:

```
explainer/
├── __init__.py
├── classifier.py        # rule-based pattern matcher
├── rule_loader.py       # читает explainers/*.md files
└── claude_client.py     # AI generator (Phase F)
```

`backend/explainers/` (markdown files):

```
explainers/
├── README.md                                    # формат правил
├── deadlock_parallel_posting.md                 # parallel document posting deadlock
├── deadlock_register_balance.md                 # балансовый регистр deadlock
├── deadlock_session_conflict.md                 # session lock conflict
├── slow_operation_heavy_sql.md                  # operation slow due to SQL
├── slow_operation_locks.md                      # operation slow due to locks
├── slow_operation_calls_cascade.md              # каскад server calls
├── exception_timeout.md                         # generic timeout pattern
├── exception_deadlock_victim.md                 # deadlock victim exception
└── ...
```

Формат `*.md`:

```markdown
---
id: deadlock_parallel_posting
applies_to: deadlock
priority: 100
patterns:
  - field: event_type
    value: TDEADLOCK
  - field: participants_count
    operator: ">="
    value: 2
  - field: same_operation
    value: true
  - field: operation_kind
    matches: "Документ\\..*\\.МодульОбъекта"
---

# Парадная блокировка параллельного проведения

## Что произошло

Две сессии пользователей провели одинаковый документ ({{operation}}) **одновременно**. 
Каждая сессия захватила свою часть регистров, и каждая ждёт другую. Платформа выбрала 
«жертву» (одна из сессий получила ошибку), вторая прошла.

## Почему так получилось

При проведении документа платформа блокирует регистры в определённом порядке. Если две 
сессии проводят документы которые **пересекаются** по записываемым регистрам (например, 
оба пишут в Партии товаров на складах), они **блокируют один тот же регистр в разном порядке** 
— классический deadlock.

## Что делать (приоритеты от простого к сложному)

1. **Очередь проведения** (быстро). Если документы критичны — настройте отложенное 
   проведение через одну очередь в фоновом задании. Это устранит параллельность.

2. **Управляемые блокировки** (среднее). Перевести регистр-конфликт на управляемые 
   блокировки 1С (если ещё не). Параметры блокировки определяются явно — меньше места 
   для конфликтов на уровне СУБД.

3. **Изменение архитектуры** (долго). Если конфликт регулярный и блокирует бизнес — 
   возможно, нужно изменить структуру регистра (разделить на несколько, добавить измерения).

## Связано в курсе 1С:Эксперт

Раздел 13 — «Транзакционные блокировки. Совместимость управляемых блокировок 1С. 
Подходы к разработке, приводящие к конфликтам блокировок, и как разрабатывать правильно».
```

Rule loader при старте backend читает все `*.md` из `explainers/`, парсит YAML frontmatter, индексирует. Hot-reload через `watchdog` или просто перечитывает при каждом explainer-запросе (overhead минимальный — десятки md файлов).

Classifier при вызове `classify(event_data, context)`:
1. Перебирает правила в порядке `priority` DESC
2. Для каждого правила проверяет match patterns (operator: `==`, `!=`, `>=`, `<=`, `matches` regex)
3. Возвращает первое matching правило + filled-in templates (`{{operation}}` → real value)

API:

```python
class ExplainerEngine:
    def classify(self, event: dict, context: dict) -> RuleMatch | None:
        """Возвращает первое matching правило с filled templates."""
        
    def reload_rules(self):
        """Перечитывает explainers/*.md."""
```

Тесты: для каждого rule — unit test с positive case + negative case.

**Phase F — AI Explainer Integration**

`backend/src/optimyzer_backend/explainer/claude_client.py`:

```python
import os
import httpx
from anthropic import Anthropic
from .classifier import RuleMatch

class ExplainerClaudeClient:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.enabled = False
            return
        self.enabled = True
        self.client = Anthropic(api_key=api_key)
    
    def generate_explanation(
        self,
        anatomy_data: dict,
        rule_match: RuleMatch | None,
        anatomy_kind: str,  # 'operation' | 'session' | 'deadlock'
    ) -> dict:
        """Генерирует conversational explanation."""
        if not self.enabled:
            return {"ok": False, "error": "API key not configured"}
        
        prompt = self._build_prompt(anatomy_data, rule_match, anatomy_kind)
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5",  # балланс качество/cost
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                timeout=15.0,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
        
        return {
            "ok": True,
            "text": response.content[0].text,
            "model": "claude-sonnet-4-5",
            "tokens_in": response.usage.input_tokens,
            "tokens_out": response.usage.output_tokens,
        }
    
    def _build_prompt(self, data, rule_match, anatomy_kind):
        """Build prompt with rule context if available."""
        ...
```

System prompt template (RU):

```
Ты — старший 1С-эксперт по технологическим вопросам, который объясняет проблему 
производительности middle-программисту 1С БЕЗ сертификации эксперта.

Правила:
1. Пиши на русском, conversational, как коллеге.
2. НЕ используй жаргон без объяснения: если используешь "латч", "MVCC", "уровень изоляции" — 
   объясни в скобках простыми словами.
3. Структура ответа:
   - Что произошло (2-3 предложения по существу)
   - Почему так получилось (объяснение причины)
   - Что делать (3 конкретных action items от простого к сложному)
4. Не пиши "возможно", "может быть" — пиши уверенно, ты эксперт.
5. Не упоминай APDEX/SLA если их нет в контексте.
6. Если знаешь конкретный пункт курса 1С:Эксперт — упомяни.
7. Длина ответа: 200-400 слов.
```

User prompt template:

```
{rule_context if matched else "Произошло событие, для которого нет готового правила."}

Данные события:
{anatomy_data_summarized}

Объясни происходящее и дай рекомендации.
```

Где `rule_context` — это тело markdown правила без YAML frontmatter (Phase E).

AI cache:

```python
# SQLite table в data/explainer_cache.db
CREATE TABLE explainer_cache (
    cache_key VARCHAR PRIMARY KEY,  -- hash(archive_id + anatomy_kind + target_id)
    archive_id VARCHAR,
    anatomy_kind VARCHAR,
    target_id VARCHAR,
    rule_id VARCHAR,
    ai_text TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

При запросе:
1. Проверить кеш — если есть, вернуть мгновенно
2. Иначе запустить AI generation в background thread + вернуть rule-based explainer immediately
3. Когда AI ответит — записать в кеш + push через WebSocket / Server-Sent Events / polling RPC к frontend
4. Frontend обновляет ExplainerCard когда приходит AI текст

Frontend `ExplainerCard.tsx`:

```tsx
type ExplainerProps = {
  archiveId: string;
  anatomyKind: 'operation' | 'session' | 'deadlock';
  targetId: string;
};

export function ExplainerCard({ archiveId, anatomyKind, targetId }: ExplainerProps) {
  const [ruleExplainer, setRuleExplainer] = useState<RuleExplainer | null>(null);
  const [aiExplainer, setAiExplainer] = useState<AiExplainer | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  
  useEffect(() => {
    // 1. Сразу запрашиваем rule-based (мгновенно)
    rpc.getRuleExplainer({ archiveId, anatomyKind, targetId })
      .then(setRuleExplainer);
    
    // 2. Параллельно запрашиваем AI (3-5 sec)
    setAiLoading(true);
    rpc.getAiExplainer({ archiveId, anatomyKind, targetId })
      .then(result => {
        if (result.ok) setAiExplainer(result);
        setAiLoading(false);
      });
  }, [archiveId, anatomyKind, targetId]);
  
  // Render:
  // - Header: ruleExplainer.title (если rule matched) или "Объяснение"
  // - Если AI пришёл — показываем AI text + small label "AI"
  // - Если AI ещё loading — показываем rule-based text + spinner "AI генерирует развёрнутое объяснение..."
  // - Если AI failed — показываем rule-based text + кнопка "Попробовать ещё раз"
  // - Если ни rule ни AI — показываем "Это нестандартный паттерн. Информация: <raw>"
}
```

RPC methods:

```python
@rpc.method("explainer.get_rule_based")
def get_rule_based_explainer(archive_id: str, anatomy_kind: str, target_id: str) -> dict:
    """Synchronous, instant."""
    # 1. Загрузить anatomy data
    # 2. classify через ExplainerEngine
    # 3. Если matched — вернуть rendered template
    # 4. Если нет — вернуть generic placeholder
    pass

@rpc.method("explainer.get_ai")
def get_ai_explainer(archive_id: str, anatomy_kind: str, target_id: str) -> dict:
    """Может занять 3-15 секунд. Кеш-aware."""
    cache_key = hash_key(archive_id, anatomy_kind, target_id)
    cached = check_cache(cache_key)
    if cached:
        return {"ok": True, "text": cached.ai_text, "from_cache": True}
    
    # ... generate via Claude API
    # ... save to cache
    return {"ok": True, "text": result.text, "from_cache": False}
```

**Phase G — Update curriculum mapping document**

Обновить `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md`:

- Раздел 3 (Apdex): обновить статусы — некоторые пункты 🔵 переводятся в 🟡 (частично closed)
- Раздел 4 (Когда уже тормозит): большинство 🟡 → ✅
- Раздел 6 (ТЖ): «Найти запрос в коде» 🟡 → ✅ (через operation context navigation)
- Раздел 13 (Транзакционные блокировки): большинство 🔵 → ✅. Это **главное достижение Sprint 3**

Обновить итоговую статистику:
- До Sprint 3: ~25% полное покрытие
- После Sprint 3: ~40% полное покрытие
- Раздел 13: 30% → 80%

**Phase H — Real-data Acceptance Gate + Demo recording**

Acceptance tests `backend/tests/test_sprint3_real_data.py`:

```python
@pytest.mark.skipif(not OPTIMYZER_REAL_FOLDER_PATH, reason="...")
class TestSprint3Acceptance:
    
    def test_extra_json_field_study_completed(self):
        """Phase 0 deliverable: docs/EXTRA_JSON_FIELD_STUDY.md exists с разумным содержимым."""
        
    def test_context_normalization_works_on_real_archive(self):
        """Все events в архиве имеют context_normalized если context не NULL."""
        
    def test_top_business_operations_under_3s(self):
        """Phase B view < 3 секунды на 12 GiB."""
        
    def test_document_anatomy_under_3s(self):
        """Phase C view < 3 секунды для типичной операции."""
        
    def test_deadlock_anatomy_works_for_real_deadlock(self):
        """Phase D view загружается для real TDEADLOCK event."""
        
    def test_rule_based_explainer_classifies_at_least_60_percent(self):
        """Не менее 60% real TDEADLOCK events матчатся к одному из rules."""
        
    def test_ai_explainer_generates_for_uncached(self):
        """AI explainer возвращает text за <15 сек для uncached event."""
        # Skip если ANTHROPIC_API_KEY не настроен
        
    def test_ai_cache_works(self):
        """Повторный запрос для того же event возвращается из cache (мгновенно)."""
```

Manual demo recording 5-7 минут:
1. Загрузка реального архива (drag&drop)
2. Top Business Operations → click на топ операцию
3. Document Anatomy → читаем AI explainer вместе со слушателем
4. Deadlock в errors feed → click → Deadlock Anatomy → AI разбор
5. Multi-archive comparison (Sprint 2 feature как bonus)
6. SQL Console для power users (показать что под капотом есть SQL)

Recording = `docs/demo/sprint3_demo_v1.mp4` или ссылка на YouTube unlisted.

### DONE WHEN

| # | Criterion | Verification |
|---|---|---|
| 1 | Phase 0 — `docs/EXTRA_JSON_FIELD_STUDY.md` создан с реальной schema | file exists, peer review |
| 2 | `context_normalized` колонка добавлена, backfill выполнен | SQL query verification |
| 3 | Top Business Operations view работает с group by `context_normalized` | manual + unit tests |
| 4 | Document Anatomy view доступна по URL `/anatomy/operation/<context>` или `/anatomy/session/<id>` | manual |
| 5 | Deadlock Anatomy view доступна по URL `/anatomy/deadlock/<event_id>` | manual |
| 6 | `explainers/` папка содержит минимум 10 markdown rule files | file count, peer review |
| 7 | Rule-based classifier работает (тесты для каждого rule) | pytest |
| 8 | AI explainer интегрирован через backend (no API key in frontend) | code review |
| 9 | `.env.example` создан с `ANTHROPIC_API_KEY=` | file exists |
| 10 | AI cache работает (повторный запрос мгновенный) | acceptance test |
| 11 | ExplainerCard компонент показывает rule + AI gracefully | manual |
| 12 | Если API key не настроен — tool работает с rule-based only без crashes | manual smoke |
| 13 | `FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновлён с Sprint 3 статусами | file diff |
| 14 | Sidebar enable 3 новых views | manual |
| 15 | ru-RU strings добавлены для всех новых UI elements | grep i18n/ru.ts |
| 16 | pytest суммарно ≥ 240 (Sprint 2 had 183, +50+ minimum для anatomy views + explainers) | CI |
| 17 | Conventional commits | git log |
| 18 | SPRINT_3_REPORT.md, ADR-022..024 written | files |
| 19 | **ACCEPTANCE GATE:** Top Business Operations работает < 3 сек на 12 GiB | env-gated pytest |
| 20 | **ACCEPTANCE GATE:** Document Anatomy работает < 3 сек | env-gated pytest |
| 21 | **ACCEPTANCE GATE:** Deadlock Anatomy работает | env-gated pytest |
| 22 | **ACCEPTANCE GATE:** Rule classifier матчит ≥ 60% real TDEADLOCKs | env-gated pytest |
| 23 | **ACCEPTANCE GATE:** AI explainer работает для uncached events (если API key есть) | env-gated pytest |
| 24 | **DEMO RECORDING:** 5-7 минут screen recording для портфолио | mp4 file |
| 25 | OPUS_HANDOVER_SPRINT_3.md подготовлен | file |

Пункты 19-24 — обязательные blocking gates. Sprint 3 не закрыт без них.

### VERIFY

- **pytest backend** — 240+ tests всё зелёные (включая Sprint 0-2 baseline)
- **TypeScript build** — 0 errors (frontend)
- **Manual smoke (.\start.bat):** загрузить архив, открыть каждый из 3 anatomy views, увидеть rule-based explainer мгновенно, увидеть AI explainer через 3-5 сек (если API key настроен), увидеть graceful fallback без crash (если API key не настроен)
- **Multi-archive Comparison (Sprint 2)** работает без regression
- **All Sprint 2 views (Slow Queries / Locks / Roles / Duration / Errors / Activity)** работают без regression
- **Cross-filtering** работает без regression

**Rollback plan:**

Если Sprint 3 ломает что-то в Sprint 2:
- `git revert <sprint3_merge_commit>` возвращает на `v0.2.0-internal`
- `git reset --hard v0.2.0-internal` если revert не сработал
- Schema migration: `context_normalized` колонка остаётся (read-only — не мешает), индекс `idx_events_context_norm` можно DROP вручную если конфликтует
- `data/explainer_cache.db` можно удалить — пересоздаётся
- `explainers/*.md` файлы — это просто markdown, не активны без backend Sprint 3 кода

### OUTPUT

После закрытия Sprint 3:
- Tag `v0.3.0-internal` на merge commit
- `docs/SPRINT_3_REPORT.md` с измеренными метриками (event distribution, rule coverage, AI cache hit rate)
- `docs/EXTRA_JSON_FIELD_STUDY.md` (Phase 0 deliverable)
- `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` обновлён
- ADR-022 — Curriculum mapping enforcement
- ADR-023 — Explainer hybrid architecture
- ADR-024 — Backend-only AI calls
- `docs/OPUS_HANDOVER_SPRINT_3.md` для следующего архитектора-Opus сессии
- README updated со status «Sprint 3 closed, anatomy views + AI explainer»
- Demo recording файл / ссылка

### STOP RULES

- Останавливаться при неоднозначности с high impact: не выдумывать архитектуру `extra` JSON, не предполагать как платформа 1С пишет события. Сначала Phase 0 (discovery), потом design Phases C и D.
- Показывать ranked options (2-4 варианта), не задавать open-ended вопросы.
- Не расширять scope. Смежные задачи (Query Analyzer / continuous monitoring / Apdex) → TODO.md.
- No time estimates anywhere в reports/commits/docs.
- Light theme only (dark theme FORBIDDEN).
- Не модифицировать `design/opt/*.jsx`.
- Не модифицировать ADR-001..021 без явного указания архитектора.
- Destructive ops (schema migrations) → явно показывать rollback plan через `data/` cleanup или branch.
- Conventional commits обязательны: один логический commit = один scope.
- Real-data acceptance gates (DoD #19-24) — блокирующие условия закрытия Sprint 3.
- Anthropic API key — НЕВЕРАЯ в commits, .gitignore, .env только локально.
- AI cache table в **отдельном** SQLite db `data/explainer_cache.db` — НЕ смешивать с app metadata.
- `explainers/*.md` файлы — markdown с YAML frontmatter. Если формат меняется — обновлять README в `explainers/`.
- Если Phase 0 discovery показывает что `extra` JSON schema **сильно** отличается от ожидаемой (например, поля Regions/WaitConnections отсутствуют) — **остановиться и спросить архитектора через ranked options**, не угадывать.
- Если AI explainer стабильно генерирует мусор / галлюцинации — fix prompts итеративно, но **не** замещать на heuristics в Phase F. Лучше rule-based + «AI temporarily unavailable» чем плохой AI.
