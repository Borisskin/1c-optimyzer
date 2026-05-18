# Project Reactivation — 1C-Optimyzer (Module 1)

> **Status:** Maintenance mode → **Active development reactivated** (2026-05-18)
> **Decision-maker:** Сергей (owner) + Claude Opus 4.7 (architect)
> **Supersedes:** `docs/PROJECT_CLOSURE_MODULE_1.md` (closure decision overruled)

---

## 1. Что меняется

`PROJECT_CLOSURE_MODULE_1.md` (созданный в Sprint 1 closure) **отменён**. Module 1 переходит обратно в **active development** с расширенной стратегией:

1. **Не "complete and pause"**, а **"complete and ship as portfolio + employment tool"**
2. **Удаление OQL DSL** — стратегическое упрощение, не downgrade
3. **Pre-built investigation views** как primary UX — вместо DSL-first approach
4. **Multi-archive comparison** — новая киллер-фича для портфолио и реального применения

---

## 2. Стратегический контекст reactivation

### Что изменилось со времени closure

На момент closure (предыдущая сессия архитектора) решение было: pause Module 1, переход к AI Product Analytics. После cold founder-level reassessment (см. transcript архитектурной сессии):

**AI Product Analytics rejected** по следующим причинам:
- Главный customer (ГосЛог) имеет фундаментальный issue с recurring revenue (разовые проверки, разовая ценность) — даже идеальная аналитика не починит
- Решение оставить ГосЛог "как есть" → SEO-Аналитика теряет primary polygon
- Pivot fatigue: четвёртое направление за две недели, паттерн founders' chasing shiny objects

**1C-Optimyzer + employment** выбран как primary direction:
- **Детерминированный доход** через employment ($3000-3500/мес реалистично для 1C-эксперта/DBA)
- **Synergy между job и product**: на работе access к real production кластерам (250+ юзеров одновременно), которые solo founder не воссоздаст. Job-experience напрямую двигает product вперёд
- **Existing accumulated work**: Module 1 = ready portfolio piece, не start from scratch
- **Distribution через работодателя**: применение tool в production кластере работодателя → накопление кейсов → продажа сначала внутри компании, потом её клиентам. Это устраняет главный риск всех SaaS — cold sales

### Новая business modeль (явно зафиксирована)

| Уровень | Source revenue | Реалистичная сумма |
|---|---|---|
| Layer 1 | Зарплата (employment как 1C-эксперт/DBA) | $3000-3500/мес стабильно |
| Layer 2 | Tool sale внутри работодателя (после демонстрации impact) | $500-2000/мес incremental |
| Layer 3 | Tool sale внешним клиентам (через работодательскую сеть) | $1000-5000/мес incremental |
| ГосЛог (parallel) | Maintenance mode, паssive income | $500-1000/мес stable |

**Cumulative potential** в обозримом периоде: $5000-11500/мес. Не unicorn, но **детерминированный путь** к sustainable income vs spekulative SaaS path.

---

## 3. Что отменяется из closure document

В `PROJECT_CLOSURE_MODULE_1.md`:

| Положение | Статус |
|---|---|
| "Active development paused" | ❌ Отменено |
| "Module 2+ deferred indefinitely" | 🔄 Изменено: Module 2 (real-time agents) остаётся deferred, но Module 1 расширяется через Sprint 2-3 до full product |
| "Maintenance policy: no new features" | ❌ Отменено |
| "Conditions для re-activation" (5000 users / 50 запросов / партнёрство / команда) | ❌ Отменено — re-activated по другому reasoning |
| "License TBD" | 🔄 Decision сохраняется на потом, но проект НЕ становится opensource в обозримом периоде |
| "GitHub repo public, paused" | 🔄 Изменено: public, **active** development |
| README update про paused | ✅ Обновляется при closure Sprint 2 |
| Tag `v0.1.0-internal` | ✅ Сохраняется как marker точки reactivation |

---

## 4. Что НЕ меняется

| Положение | Статус |
|---|---|
| Module 1 как функционально завершённый — **остаётся true** | ✅ Sprint 2 расширяет, но Sprint 1 не недоделан |
| 18-screen дизайн-концепт остаётся valid | ✅ Sprint 2 реализует часть Module 1 views |
| ADR-001..014 (Sprint 0-1) остаются в силе | ✅ |
| Стек (Tauri 2 + React/TS + Python sidecar) — без изменений | ✅ |
| Real-data acceptance gate как требование | ✅ Усиливается в Sprint 2 |
| Premium UI / design system из shared.jsx | ✅ |
| Никаких сроковых оценок в reports | ✅ |
| Light theme only, dark theme forbidden | ✅ |

---

## 5. Sprint 2 — что планируется

См. `docs/SPRINT_2_PROMPT.md` (или передача через архитектора-Opus отдельным документом).

Краткое summary:
- **Phase A:** Remove OQL DSL completely (полная очистка кода)
- **Phase B:** SQL Engine (executor, validator, schema introspection, CodeMirror SQL extension)
- **Phase C:** Charts library (BarChart, LineChart, Heatmap, Histogram, Scatter, Donut — Recharts wrappers с design system styling)
- **Phase D:** 6 Pre-built Investigation Views (Slow Queries / Locks Timeline / Process Roles / Duration Histogram / Errors Feed / Activity Heatmap)
- **Phase E:** Cross-filtering между всеми views (главная архитектурная фича)
- **Phase F:** SQL Templates library (15-20 шт)
- **Phase G:** Multi-archive Comparison (киллер-фича для портфолио)
- **Phase H:** Export (CSV/XLSX/JSON)
- **Phase I:** Sidebar update — enable Sprint 2 views
- **Phase J:** Onboarding & UX polish (Welcome screen, empty/loading/error states)
- **Phase K:** Real-data acceptance gate + demo recording

После Sprint 2 — **commercially viable product** готовый к demo на собеседовании + применению в найме.

---

## 6. Sprint 3 (preliminary scope, не блокирует Sprint 2)

После Sprint 2 (если необходимо):
- Production .msi installer
- Onboarding tour
- Help documentation embedded
- Demo videos / case studies
- Возможный public release / лicense decision

Sprint 3 — **optional**, зависит от того, нужен ли публичный launch для employment strategy. Если работа найдена и tool применяется внутри компании — Sprint 3 может быть отложен.

---

## 7. Maintenance стратегия

После Sprint 2 (и опционально Sprint 3) проект становится:
- **Active product** (не paused)
- **Maintained as primary career asset**
- **Bug fixes prioritized**
- **Feature additions** — по запросу реальных пользователей (после employment + first customers)
- **Performance optimization** — приоритетно если applied к production кластерам у работодателя

---

## 8. README update (после Sprint 2 closure)

`README.md` будет обновлён в Sprint 2 closure commit. Status section меняется с:

```
⏸️ Active development paused (2026-05-18). Project в maintenance mode.
```

на:

```
🚀 Active development. Module 1 продакшен-готов; Sprint 2+ расширяет product до full investigation workbench.

Установка / Demo / Quick Start — см. docs/INSTALLATION.md (Sprint 3 deliverable)
```

---

## 9. Финальное

Это **не Capitulation от closure decision**, это **disciplined re-evaluation на новых данных**:

- В момент closure (Sprint 1 finalization) у нас была **гипотеза** что AI Product Analytics — лучший путь
- После cold founder-level analysis выяснилось: **гипотеза была wrong для текущей жизненной ситуации Сергея** (короткий горизонт планирования, отсутствие detrminированного дохода, narrow validation polygon)
- Новая стратегия учитывает **реальные данные**: employment realistic ($3000-3500), accumulated work has value as portfolio, distribution через работодателя — единственный realistic channel для solo founder в этой нише

Это **smart founder decision**, не failure. Pivot обратно к Module 1 — **сильный сигнал зрелости**: не привязываемся эмоционально к предыдущим решениям, переоцениваем на новых данных.

---

**Approved by:** Сергей (owner) + Claude Opus 4.7 (architect)
**Date:** 2026-05-18
