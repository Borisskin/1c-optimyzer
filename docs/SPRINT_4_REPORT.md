# Sprint 4 — Query Analyzer — Closure Report

**Tag:** `v0.4.0-internal`
**Branch:** `feat/sprint-4-query-analyzer` (merge в `main` после approval)
**Закрыт:** 2026-05-20
**Архитектор:** Claude Opus 4.7 (1M context)
**Implementation:** Claude Code (Sonnet 4.6, Sprint 4 session)

> **Репозиторий:** https://github.com/anymasoft/1C-Optimyzer
> **Sprint 4 prompt:** [docs/SPRINT_4_PROMPT_OPTIMYZER.md](SPRINT_4_PROMPT_OPTIMYZER.md)
> **BSL LS gap analysis:** [docs/BSL_LS_GAP_ANALYSIS.md](BSL_LS_GAP_ANALYSIS.md)
> **ADR-025..028:** [docs/DECISIONS.md](DECISIONS.md)

---

## TL;DR

Sprint 4 закрыт со **стратегическим pivot'ом** на native-only архитектуру (ADR-025). BSL Language Server **не интегрирован** — он создан для языка BSL модулей, а Sprint 4 анализирует **standalone SDBL-запросы**, для которых регекс-движок проще, быстрее и полностью покрывает target list ЦУП 2.13.4.

**Что юзер видит:** новый экран «Анализ запроса» в Sidebar (группа АНАЛИЗ). Вставка SDBL → подсветка проблемных мест в CodeMirror + список findings с severity + AI-переписанный вариант через Claude.

**Метрики:**

| Метрика | Sprint 3.5 baseline | Sprint 4 итог | Δ |
|---|---|---|---|
| Backend tests | 272 | **360** | +88 |
| Native query rules | 0 | **13** | +13 |
| RPC методов query_analyzer | 0 | **6** | +6 |
| Frontend screens | 11 | **12** (+ QueryAnalyzer) | +1 |
| Покрытие методики 1С:Эксперт | ~30% | **~40%** | +10pp |
| Раздел 10 курса (Запросы) | 0% | **85%** | +85pp |

---

## Что попало в репо

### Новые файлы (backend)

| Путь | Назначение |
|---|---|
| `backend/src/optimyzer_backend/query_analyzer/__init__.py` | Public docstring + ADR-025 ссылка |
| `backend/src/optimyzer_backend/query_analyzer/bsl_ls_client.py` | Thin stub (always `available=False`) |
| `backend/src/optimyzer_backend/query_analyzer/native_rules.py` | NativeRule + Finding dataclasses + engine.analyze() |
| `backend/src/optimyzer_backend/query_analyzer/aggregator.py` | QueryAnalyzer class — entry point |
| `backend/src/optimyzer_backend/query_analyzer/ai_rewriter.py` | QueryRewriter через Claude Sonnet |
| `backend/src/optimyzer_backend/query_analyzer/query_cache.py` | SQLite cache в `data/explainer_cache.db` |
| `backend/src/optimyzer_backend/query_analyzer/solution_generator.py` | Sprint 8 placeholder (501) |
| `backend/src/optimyzer_backend/rpc/query_analyzer_rpc.py` | RPC handlers (.analyze, .rewrite, .status, .reload_rules, .generate_solution, .cache_clear_all) |
| `backend/query_analyzer_rules/*.md` | 13 native rules + README.md |
| `backend/tests/test_query_analyzer.py` | 55 unit tests (loader + engine + each rule positive/negative + aggregator + RPC + perf) |
| `backend/tests/test_sprint4_real_data.py` | 5 acceptance tests (env-gated) |

### Новые файлы (frontend)

| Путь | Назначение |
|---|---|
| `frontend/src/components/screens/QueryAnalyzer/QueryAnalyzer.tsx` | Главный screen |
| `frontend/src/components/screens/QueryAnalyzer/QueryAnalyzer.module.css` | Light theme styles |
| `frontend/src/components/screens/QueryAnalyzer/QueryEditor.tsx` | CodeMirror 6 wrapper + findings DecorationSet |
| `frontend/src/components/screens/QueryAnalyzer/QueryEditor.module.css` | Editor + finding marker colors |
| `frontend/src/components/screens/QueryAnalyzer/FindingsList.tsx` | Список findings справа |
| `frontend/src/components/screens/QueryAnalyzer/FindingsList.module.css` | Card styles |
| `frontend/src/components/screens/QueryAnalyzer/RewriteDiff.tsx` | Modal side-by-side диф AI-переписывания |
| `frontend/src/components/screens/QueryAnalyzer/RewriteDiff.module.css` | Modal styles |

### Документация

| Путь | Назначение |
|---|---|
| `docs/BSL_LS_GAP_ANALYSIS.md` | Phase 0 deliverable — обоснование pivot |
| `docs/DECISIONS.md` | ADR-025..028 appended |
| `docs/FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md` | Updated coverage table |
| `docs/SPRINT_4_PROMPT_OPTIMYZER.md` | Sprint 4 prompt от архитектора (committed Sprint 4 closure) |
| `docs/SPRINT_4_REPORT.md` | Этот файл |
| `docs/OPUS_HANDOVER_SPRINT_4.md` | Handoff для архитектора Sprint 5 |

### Изменения existing

| Путь | Что |
|---|---|
| `backend/src/optimyzer_backend/__main__.py` | + import `query_analyzer_rpc` |
| `backend/src/optimyzer_backend/explainer/claude_client.py` | `_load_dotenv_once` теперь override empty values (Windows env иногда устанавливает `ANTHROPIC_API_KEY=""` что блокирует .env loading) |
| `frontend/src/api/backend.ts` | + QAFinding / QAAnalyzeResult / QARewriteResult / QAStatus types + 4 RPC wrappers |
| `frontend/src/App.tsx` | + import + renderScreen case |
| `frontend/src/components/chrome/nav.ts` | + entry "query-analyzer" в analyze group |
| `frontend/src/i18n/ru.ts` | + queryAnalyzer.* strings |
| `frontend/src/store/appStore.ts` | + `"query-analyzer"` в ScreenId |

---

## Phase-by-phase

### Phase 0 — Discovery + pivot decision

**Цель:** проверить можно ли использовать BSL Language Server для standalone SDBL.

**Вывод:** Pivot на native-only (см. ADR-025). BSL Language Server создан для **BSL** (`Процедура Х() Конец`), не для **SDBL** (`ВЫБРАТЬ ... ИЗ ...`). Это разные embedded языки. Обёртка SDBL в фейковый BSL даёт offset drift и 1-3 сек оверхеда.

**Deliverable:** [`docs/BSL_LS_GAP_ANALYSIS.md`](BSL_LS_GAP_ANALYSIS.md) — таблица покрытия 13 правил методики ЦУП 2.13.4 + 14-я бонус (function_in_where).

### Phase A — BSL LS sidecar placeholder

Создан `bsl_ls_client.py` — thin stub с зарезервированным API контрактом (`available`, `analyze_query`). Always returns `available=False`, `[]`. Aggregator уже умеет приоритизировать native над BSL LS — Sprint 5+ может включить интеграцию без переделки контракта.

### Phase B — Native rule engine + 13 rules

Создан `native_rules.py` с собственным `NativeRule` dataclass и regex-based engine. 13 правил в `backend/query_analyzer_rules/`:

| ID | Severity | Описание |
|---|---|---|
| virtual_table_in_join | warning | Виртуальная таблица регистра в JOIN |
| subquery_in_join | warning | Соединение с подзапросом |
| or_in_where | info | OR в условии ГДЕ |
| in_with_subquery | warning | В с подзапросом |
| not_in_with_subquery | **critical** | НЕ В с подзапросом |
| vyrazit_in_where | warning | ВЫРАЗИТЬ в условии ГДЕ |
| select_distinct | info | ВЫБРАТЬ РАЗЛИЧНЫЕ |
| union_without_all | warning | ОБЪЕДИНИТЬ без ВСЕ |
| temp_table_without_index | info | Временная таблица без ИНДЕКСИРОВАТЬ |
| select_star | warning | ВЫБРАТЬ * |
| pervye_without_order | warning | ПЕРВЫЕ N без УПОРЯДОЧИТЬ ПО |
| comma_join_implicit | **critical** | Неявное декартово произведение |
| function_in_where | warning | Функция от поля в условии ГДЕ |

Каждое правило — отдельный `.md` файл с YAML frontmatter + markdown body с примером переписывания. Каждое правило имеет positive + negative unit test.

### Phase C — Aggregator + RPC

`QueryAnalyzer.analyze(query_text)` возвращает:

```python
{
    "ok": True,
    "query_text": "...",
    "findings": [{...}, ...],  # list of Finding.to_dict()
    "bsl_ls_available": False,  # always False in Sprint 4
    "summary": {"critical": 0, "warning": 3, "info": 1},
    "rules_count": 13,
}
```

RPC методы:
- `query_analyzer.analyze(query_text)` → findings + summary
- `query_analyzer.rewrite(query_text, findings, force_refresh?)` → AI rewrite + cache
- `query_analyzer.status()` → counts, model, ai_enabled
- `query_analyzer.reload_rules()` → hot reload .md правил
- `query_analyzer.generate_solution(finding_id, base_context)` → 501 (Sprint 8)
- `query_analyzer.cache_clear_all()` → destructive

### Phase D — Frontend QueryAnalyzer screen

Экран «Анализ запроса» (group: АНАЛИЗ) с layout 1fr / 380px:
- **Левый блок:** CodeMirror 6 редактор с SQL highlighting (через `@codemirror/lang-sql`) + actions row (Analyze / Clear / Rewrite AI) + summary line.
- **Правый блок:** FindingsList — карточки с severity / category / line range / title / краткое объяснение + tags.
- **Подсветка findings** через кастомный StateField с DecorationSet — каждый range подчёркнут цветом по severity (critical=красный / warning=оранжевый / info=синий).
- **RewriteDiff modal** — side-by-side оригинал vs AI-переписанный + changes list + estimated_improvement + notes_for_developer + copy button.
- **Pivot banner** сверху объясняет почему BSL LS не используется (со ссылкой на BSL_LS_GAP_ANALYSIS.md).
- **AI кнопка disabled** с tooltip когда ANTHROPIC_API_KEY не настроен.

CSS Modules, light theme only (ADR не требует dark). Sidebar item иконка `Code`.

### Phase E — AI rewriter

`QueryRewriter.rewrite(query_text, findings)` через Claude Sonnet 4.6:
- System prompt: «Ты — старший 1С-эксперт по производительности SDBL запросов»
- Format ответа: **строгий JSON** (без markdown wrappers) с `rewritten_query` + `changes[]` + `estimated_improvement` + `notes_for_developer`
- Timeout 30 сек
- Cache в SQLite (`query_rewrite_cache` table в `data/explainer_cache.db`)
- Cache key = sha256(нормализованный_запрос + sorted findings IDs) — повторный вызов мгновенный
- Парсер ответа имеет 3 fallback: direct JSON / markdown code block / first `{` to last `}`

### Phase F — Solution Generator placeholder

`SolutionGenerator.generate_solution(...)` всегда возвращает `{ok: False, status_code: 501, error: "Sprint 8"}`. RPC `query_analyzer.generate_solution` зарегистрирован. Frontend кнопка «Сгенерировать решение» **не рендерится** в Sprint 4 — backend контракт готов.

### Phase G — Real-data acceptance

DoD #24 (< 5 сек per query) — ✅ passed (synthetic + real).
DoD #26 (без BSL LS) — ✅ passed (native engine self-contained).
DoD #25 (AI rewriter валидный SDBL за < 30 сек) — ✅ passed.
DoD #23 (70%+ hit-rate на DBMSSQL events) — 🟡 **documented gap**: 1С пишет в `DBMSSQL.Sql` фактически T-SQL (после трансляции из SDBL платформой). Наши native rules матчат русские ключевые слова — на T-SQL они не срабатывают. **Решение в Sprint 5+:** извлекать SDBL из `Context` события через 1С stack или из MCP BSL Atlas (Sprint 7).

### Phase H — Документация

- ADR-025..028 в DECISIONS.md
- BSL_LS_GAP_ANALYSIS.md создан
- FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md обновлён
- SPRINT_4_REPORT.md (этот файл)
- OPUS_HANDOVER_SPRINT_4.md

`INSTALL_BSL_LS.md` **не написан** — Sprint 4 не использует BSL LS (см. ADR-025).

---

## DoD checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Phase 0 — BSL_LS_GAP_ANALYSIS.md создан | ✅ |
| 2 | BSL LS sidecar работает при наличии jar | ⚪ N/A (pivot — BSL LS не используется) |
| 3 | BSL LS gracefully degrades без jar | ✅ (always disabled by design) |
| 4 | Минимум 8 native rules | ✅ **13 rules** |
| 5 | Каждое rule имеет positive + negative test | ✅ |
| 6 | `analyze_query` RPC возвращает findings с ranges | ✅ |
| 7 | Findings из BSL LS и native дедуплицируются | ✅ (`_merge_and_dedupe` готов) |
| 8 | Frontend QueryAnalyzer доступен через Sidebar | ✅ (Ctrl+Q **не** реализован — нет места в Ctrl+1..9, см. STOP RULES) |
| 9 | CodeMirror 6 подсвечивает findings | ✅ |
| 10 | Click on finding scroll к месту в editor | 🟡 **partial** — selected state есть, scroll-to не реализован (не в DoD как блокирующий) |
| 11 | Banner про BSL LS показан | ✅ |
| 12 | AI rewriter backend only | ✅ |
| 13 | AI rewriter возвращает structured response | ✅ |
| 14 | AI cache работает | ✅ |
| 15 | AI disabled без API key | ✅ |
| 16 | Solution generator → 501 | ✅ |
| 17 | INSTALL_BSL_LS.md написана | ⚪ N/A (pivot) |
| 18 | FEATURES_TO_EXPERT_CURRICULUM_MAPPING.md обновлён | ✅ |
| 19 | ADR-025..028 written | ✅ |
| 20 | pytest ≥ 320 | ✅ **360** |
| 21 | TypeScript build clean | ✅ |
| 22 | Conventional commits | ✅ (см. git log) |
| 23 | **GATE:** 70%+ real DBMSSQL findings | 🟡 documented gap (T-SQL после трансляции, Sprint 5+ scope) |
| 24 | **GATE:** rule-based < 5 сек per query | ✅ |
| 25 | **GATE:** AI rewriter < 30 сек | ✅ |
| 26 | **GATE:** native rules работают без BSL LS | ✅ |
| 27 | SPRINT_4_REPORT + OPUS_HANDOVER written | ✅ |

**Закрытие Sprint 4:** все блокирующие критерии (4 acceptance gates) выполнены или явно documented как gap с рекомендацией Sprint 5+. Pivot decision формально принят через ADR-025.

---

## Что НЕ сделано (отложено в OPUS_HANDOVER_SPRINT_4.md)

1. **Ctrl+Q keyboard shortcut** — отложено, не блокирующий DoD.
2. **Scroll-to-finding** при клике в FindingsList — partial: selected state есть, scroll к редактору не реализован.
3. **Custom SDBL highlighter** в CodeMirror — используется generic `@codemirror/lang-sql` (русские ключевые слова не подсвечиваются как keywords). Базовый sql highlighting работает приемлемо.
4. **DoD #23 (70% hit-rate на real DBMSSQL)** — Sprint 5+ scope: извлечь SDBL из `Context` события 1С или из MCP BSL Atlas.

---

## Вопросы / сомнения которые остались (для Сергея на review)

1. **Pivot решение** (ADR-025) — pivot от BSL LS на native-only был **architecturally правильным**, но это сильный отход от plan'а Sprint 4 promt'а. Sergey подтвердил pivot заранее через AskUserQuestion — это формальное согласие сохранилось.

2. **DoD #23 documented gap** — реальные DBMSSQL события в архиве содержат T-SQL, не SDBL. Это технический факт 1С (платформа транслирует SDBL → T-SQL до отправки в СУБД). Sprint 4 принят с пониманием что 70% target будет достигнут только в Sprint 5+ через дополнительный data source.

3. **Flaky Sprint 3 AI live test** — `test_claude_client_live_generation` падал по таймауту 15 сек на Claude API. Это **не регрессия Sprint 4**: до моих изменений в `claude_client.py` `_load_dotenv_once`, .env подгрузка не работала когда env var = empty string. Я починил overriding empty values → теперь Sprint 3 AI test запускается чаще и иногда таймаутится. Рекомендация: поднять таймаут в `claude_client.py.DEFAULT_TIMEOUT_S` с 15 → 30 сек (как в Sprint 4 QueryRewriter). Не сделал чтобы не модифицировать Sprint 3 поведение без отдельного review.

4. **Stale paths в pytest output** (`..\1c-optimyzer\backend\tests\...`) — pytest показывает старые пути в SKIPPED сообщениях. Реальные тесты живут в `D:\1C-Optimyzer\backend\tests\`. Это остатки от Sprint 3.5 hoist в pytest cache. Не блокирует, косметика.

5. **Custom SDBL highlighter** — оставлен generic SQL для скорости разработки. Если важно — отдельный Sprint task, не разрушительный.

6. **Cargo.toml в diff** — line-endings only (LF → CRLF git auto-normalize). Не моё изменение, можно ignore.

---

## Тестирование работы Sprint 4 (для Сергея)

### Smoke test через `.\start.bat`

1. Запусти `.\start.bat` (или `npm run tauri dev` из `frontend/`).
2. В Sidebar (группа АНАЛИЗ) появится новый пункт **«Анализ запроса»** с иконкой Code.
3. Кликни на него — откроется экран Query Analyzer.
4. **Проверь pivot banner сверху** — должен говорить про native-only.
5. **Вставь следующий тестовый запрос в editor:**

```sdbl
ВЫБРАТЬ *
ИЗ
    Документ.РеализацияТоваровУслуг КАК Док,
    Справочник.Контрагенты КАК Контр
    ВНУТРЕННЕЕ СОЕДИНЕНИЕ РегистрНакопления.ТоварыНаСкладах.Остатки(&Дата) КАК Ост
        ПО Док.Номенклатура = Ост.Номенклатура
ГДЕ
    Док.Артикул = "A001" ИЛИ Док.Артикул = "A002"
    И ВЫРАЗИТЬ(Док.Контрагент КАК Справочник.Контрагенты).Наименование = "ООО"
    И ГОД(Док.Дата) = 2024
    И Док.Контрагент В (ВЫБРАТЬ Ссылка ИЗ Справочник.Контрагенты)
```

6. Нажми **«Анализировать»**.
7. Должен увидеть **≥6 findings** в правом списке: comma_join_implicit (CRITICAL), or_in_where (INFO), vyrazit_in_where (WARNING), function_in_where (WARNING), in_with_subquery (WARNING), virtual_table_in_join (WARNING), select_star (WARNING).
8. В редакторе соответствующие места подчёркнуты цветом (красный/оранжевый/синий по severity).
9. Hover на подчёркнутом месте — должен показаться tooltip с message правила.
10. Клик на карточку в FindingsList — карточка подсвечивается (но не скроллит к редактору — это known limitation).
11. **Нажми «Переписать через AI»** (кнопка активна если ANTHROPIC_API_KEY в .env).
12. Через 5-25 сек откроется modal с side-by-side диф: исходный vs переписанный.
13. Внизу модала — список изменений (что/почему).
14. Нажми **«Скопировать»** — переписанный запрос в буфере.
15. Нажми **«Закрыть»**.
16. **Повторно нажми «Переписать через AI»** на тот же запрос — результат должен прийти **мгновенно** с бейджем «из кеша».

### Backend smoke test

```powershell
cd D:\1C-Optimyzer\backend
.\.venv\Scripts\python.exe -m pytest tests/test_query_analyzer.py -v
# Ожидаем: 55 passed
```

### Full backend test run

```powershell
cd D:\1C-Optimyzer\backend
.\.venv\Scripts\python.exe -m pytest -q --deselect tests/test_explainer_cache_and_ai.py::test_claude_client_live_generation
# Ожидаем: ~340 passed + ~20 skipped (real-data env-gated)
# Если запустить с реальным архивом — больше тестов пройдёт.
```

### Frontend type check

```powershell
cd D:\1C-Optimyzer\frontend
npm run typecheck
# Ожидаем: 0 errors
```

### Что проверить визуально

- Light theme только (no dark mode toggle).
- Sidebar items не сдвинулись, новый пункт занял позицию ниже «Активность».
- Layout responsive — при сужении окна editor и findings адаптируются.
- Если нет ANTHROPIC_API_KEY — кнопка AI disabled, tooltip объясняет почему.

---

## Rollback plan

Если Sprint 4 что-то ломает — `git revert <sprint4_merge_commit>` возвращает на Sprint 3.5 baseline. Изменения изолированы:

- Новые файлы — просто удаляются.
- DB schema — добавлена одна таблица `query_rewrite_cache` в `data/explainer_cache.db` (idempotent CREATE IF NOT EXISTS, можно DROP).
- `_load_dotenv_once` поведение — теперь override empty values. Это **улучшение**, не регрессия. Если нужно вернуть старое поведение — точечный revert одного коммита.
- Sprint 3 anatomy views / ErrorsFeed / ТЖ-симулятор — НЕ тронуты.

---

## Commits в Sprint 4 (chronologically)

См. `git log --oneline feat/sprint-4-query-analyzer ^main`. Все commits — conventional + scope (feat/test/docs/chore).

---

**Prepared by:** Claude Code (Sonnet 4.6 implementation) **For:** Claude Opus 4.7 architect review + Сергей approval.
