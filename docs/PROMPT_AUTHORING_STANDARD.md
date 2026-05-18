# Promt Authoring Standard — /goal Structure

> **Статус:** Активный стандарт для всех новых sprint promt'ов и task promt'ов проекта 1C-Optimyzer.
> **Введён:** 2026-05-19 (после Sprint 2 planning)
> **Основан на:** best practices Codex / Claude Code / Hermes сообщества — `/goal` команда

---

## 1. Зачем

Sprint 0, Sprint 1, Sprint 2 промпты были написаны в формате «контекст + epics + acceptance criteria». Это работало, но имело **три повторяющиеся проблемы:**

1. **Scope creep** — Claude Code иногда расширял scope при обнаружении смежной задачи, не спрашивая. Sprint 1 закрыли с 11 phases вместо 8 запланированных.
2. **Open-ended questions** — QUESTIONS.md иногда заполнялся вопросами без ranked options («какую кодировку использовать?» вместо «UTF-8 / cp1251 / cp866 — рекомендую UTF-8 потому что…»).
3. **Missing rollback plans** — для destructive операций (типа удаления OQL в Sprint 2 Phase A) не указывался rollback strategy.

Структура `/goal` решает эти проблемы явным разделением промпта на 8 обязательных секций.

---

## 2. Структура (mandatory для всех sprint promt'ов)

```
GOAL:
<один чёткий, измеримый результат; только одна задача>

CONTEXT:
<репозиторий / файлы / архитектура / текущее состояние>
<известные допущения, зависимости и релевантные предыдущие решения>

CONSTRAINTS:
<что нельзя изменять>
<обязательные стандарты / паттерны>
<запрещённые файлы / действия, если есть>

PRIORITY: (необязательно)
<наивысший приоритет>
<вторичный приоритет>
<третичный приоритет>

PLAN:
<сначала разобраться, потом действовать>
<перед нетривиальными изменениями пересказать своё понимание задачи>
<предпочитать минимально достаточные изменения вместо масштабных переписываний>

DONE WHEN:
<проверяемое состояние завершения>
<ожидаемое поведение сохранено или улучшено>

VERIFY:
<тесты / сборка / lint / typecheck / ручная валидация>
<указать, что не удалось проверить и почему>
<включить rollback-план или меры локализации для деструктивных либо high-risk изменений>

OUTPUT:
<краткое summary / документация / audit / результаты>
<изменённые файлы, ключевые решения, риски и дальнейшие шаги>

STOP RULES:
<останавливаться при неоднозначности или риске с высоким impact; не выдумывать архитектуру, поведение или требования>
<показывать неопределённости вместе с ранжированными вариантами с наибольшей уверенностью перед действием, а не задавать открытые уточняющие вопросы>
<не расширять scope после достижения цели>
```

---

## 3. Правила применения

### Когда использовать `/goal` структуру

**Обязательно:**
- Каждый sprint promt (новый sprint design)
- Каждый hotfix promt (когда что-то сломалось)
- Каждый pre-sprint discovery task (типа inspect_logs)

**Опционально:**
- Mini-tasks на 1-2 коммита, где scope очевиден
- Refactoring task'и без architectural impact
- Documentation-only changes

### Адаптация для крупных спринтов

Sprint 0-2 содержали 7-11 phases каждый. Применение `/goal` к таким спринтам — это **`/goal` на верхнем уровне + phases внутри секций**:

- **GOAL** — high-level outcome всего спринта
- **CONTEXT** — состояние после предыдущего спринта + ссылки на ADR / handover
- **CONSTRAINTS** — глобальные ограничения (CSS Modules, no inline styles, conventional commits, ru-RU locale, no time estimates, и т.д.)
- **PLAN** — последовательность phases с кратким описанием
- **DONE WHEN** — DoD таблица (как было в Sprint 0-2)
- **VERIFY** — acceptance gates + rollback plan для destructive phases
- **OUTPUT** — SPRINT_N_REPORT.md, обновлённые ADR, OPUS_HANDOVER
- **STOP RULES** — universal stop rules (внизу)

### STOP RULES — универсальный набор для всех спринтов

Этот блок копируется **дословно** в каждый новый promt:

```
STOP RULES:
- Останавливаться при неоднозначности с high impact: не выдумывать архитектуру, поведение или требования. Не предполагать что владелец имел в виду — спрашивать через ranked options.
- При обнаружении неопределённости — показывать 2-4 ранжированных варианта решения с пометкой наиболее вероятного (на основе текущего context'а), НЕ задавать open-ended вопросы.
- Не расширять scope после достижения GOAL. Если по ходу работы обнаружена смежная задача — фиксировать её в QUESTIONS.md / TODO.md, НЕ делать в текущей сессии.
- Не делать time estimates в reports / commits / docs (правило project memory).
- Не использовать dark theme — light theme only (правило project memory).
- Не модифицировать дизайн-концепт в design/opt/*.jsx (это reference).
- Не модифицировать ADR ранее установленных Sprint 0-1, если в новом promt явно не указано.
- При destructive операции (удаление файлов, drop tables, rm -rf) — явно показывать что удаляется + альтернативу через `git stash` / branch для rollback.
- Conventional commits обязательны: feat(scope), fix(scope), refactor(scope), test(scope), docs, chore. Один коммит = одна логическая единица.
- Real-data acceptance gate — обязательное условие закрытия sprint'а если в promt указан.
```

---

## 4. Пример применения — fictional small task

Для иллюстрации формата, не настоящая задача:

```
/goal

GOAL:
Добавить экспорт результатов Top Slow Queries view в CSV формат через кнопку 
"Экспорт CSV" в header панели.

CONTEXT:
- Sprint 2 закрыт, branch main содержит Phase A-K
- Все views в frontend/src/components/screens/*/
- Backend RPC методы в backend/src/optimyzer_backend/rpc/views_rpc.py
- DuckDB connections per-archive в storage/duckdb_store.py

CONSTRAINTS:
- CSS Modules, никаких inline styles
- ru-RU локализация: кнопка label из i18n/ru.ts
- Не модифицировать существующие views логику — только добавить export endpoint

PLAN:
1. Backend: добавить RPC export_view_csv(view_name, archive_id, filters) → возвращает path к temp файлу
2. Frontend: добавить кнопку "Экспорт CSV" в SlowQueriesHeader.tsx
3. На click — RPC call → Tauri file dialog → save
4. Тесты: backend unit test + manual smoke

DONE WHEN:
- В Top Slow Queries view есть кнопка "Экспорт CSV" в правом верхнем углу
- Click открывает Tauri save dialog
- Сохранённый файл содержит все колонки таблицы с правильной структурой
- Файл открывается в Excel / LibreOffice без warnings

VERIFY:
- pytest test_export_csv — проверяет генерацию CSV из mock data
- Manual: открыть в Excel, проверить headers + encoding (utf-8-sig для русских колонок)
- Rollback: фича опциональная, при ошибке frontend показывает toast, не падает

OUTPUT:
- Commit feat(export): csv export for slow queries view
- 1-2 файла backend + 1 файл frontend
- Обновить i18n/ru.ts с новой строкой
- Status message: "Экспорт CSV для Slow Queries готов. Тесты passing."

STOP RULES:
- Универсальный набор (см. PROMPT_AUTHORING_STANDARD.md)
- Дополнительно: если export для других views (Locks Timeline etc.) — НЕ делать в этой сессии, 
  фиксировать как TODO для следующего task'а
```

---

## 5. Что меняется в практике

### Что НЕ меняется

- Sprint 0-2 promt'ы остаются как есть (исторические артефакты). Не переписываем ретроактивно.
- Дисциплина conventional commits / real-data testing / ADR — без изменений.
- Архитектура работы Architect ↔ Executor ↔ Owner — без изменений.

### Что меняется

- **Все promt'ы Sprint 3+** пишутся в `/goal` структуре
- **Все mini-task promt'ы** (hotfix / refactoring) пишутся в `/goal` структуре
- **Architect prefix** новых promt'ов: явно начинается с `/goal` маркера + 8 секций

### Промежуточные документы

Промежуточные документы (`PROJECT_REACTIVATION_SPRINT_2.md`, `PROJECT_CLOSURE_MODULE_1.md`, и т.д.) — **остаются в свободном формате**, потому что они не promt'ы, а strategic context документы для будущих architect-сессий.

---

## 6. ADR-020: Adopt /goal Promt Authoring Standard

**Решение:** все sprint promt'ы и task promt'ы проекта пишутся в `/goal` структуре с 8 mandatory секциями (GOAL / CONTEXT / CONSTRAINTS / PRIORITY / PLAN / DONE WHEN / VERIFY / OUTPUT / STOP RULES).

**Обоснование:**
- Sprint 0-2 опыт показал scope creep, missing rollback plans, open-ended questions без ranked options
- `/goal` структура — community-established best practice для Claude Code / Codex / Hermes
- 8 секций покрывают все типичные дыры авторской работы над promt'ами

**Принято:** Сергей (owner) + Claude Opus 4.7 (architect), 2026-05-19.

---

## 7. Шаблон для копирования в новый promt

Сохранён в `docs/templates/sprint_promt_template.md` (если файл создан):

```markdown
# Sprint N — <название>

> **Контекст:** <ссылка на предыдущий sprint report + reactivation/closure docs>
> **Working directory:** D:\1C-Optimyzer\1c-optimyzer\
> **Branch:** feat/sprint-N-<scope>

/goal

GOAL:
<один чёткий, измеримый результат всего спринта>

CONTEXT:
- Состояние после Sprint N-1: <ключевые факты>
- ADR-XXX..XXX в силе: <список>
- Working branch: <branch_name>

CONSTRAINTS:
- CSS Modules, no inline styles
- ru-RU локализация в i18n/ru.ts
- Conventional commits (feat/fix/refactor/test/docs/chore)
- No time estimates
- Light theme only (dark theme FORBIDDEN)
- Не модифицировать design/opt/*.jsx
- ADR Sprint 0-1 в силе если не сказано иначе

PRIORITY:
- P1: <критичные phases / acceptance gates>
- P2: <значимые но не блокирующие>
- P3: <nice-to-have>

PLAN:
Phase A: <название> — <краткое описание>
Phase B: ...
...

DONE WHEN:
| # | Criterion | Verification |
|---|---|---|
| 1 | <criterion> | <how to verify> |
| ... | | |

VERIFY:
- pytest всё зелёное (sprint N-1 baseline + новые tests)
- Manual smoke tests (.\start.bat)
- Real-data acceptance gate: <условие>
- Rollback plan: <как откатить если что-то сломается>

OUTPUT:
- SPRINT_N_REPORT.md
- Обновлённые ADR-XXX (если новые)
- OPUS_HANDOVER_SPRINT_N.md
- README обновлён (если изменения user-facing)
- Conventional commits log

STOP RULES:
- Останавливаться при неоднозначности с high impact: не выдумывать архитектуру.
- Показывать ranked options (2-4 варианта), не задавать open-ended вопросы.
- Не расширять scope. Смежные задачи → TODO.md.
- No time estimates.
- Light theme only.
- Не модифицировать design/opt/*.jsx.
- Destructive ops → явно показывать что удаляется + git stash/branch для rollback.
- Conventional commits обязательны.
- Real-data acceptance gate — блокирующее условие закрытия.
```

---

## 8. Финальное замечание

Этот стандарт **не делает работу медленнее**. Он делает её **дисциплинированнее**:
- Меньше re-work из-за scope creep
- Меньше пропущенных acceptance criteria  
- Меньше неконтролируемых destructive операций
- Меньше open-ended questions без направления

Sprint 0-2 показали что **structure matters** — Sprint 0 был более жёстко структурирован чем Sprint 1, и closure был чище. `/goal` формат универсализирует эту дисциплину для всех будущих promt'ов.
