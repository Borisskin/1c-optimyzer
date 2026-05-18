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
