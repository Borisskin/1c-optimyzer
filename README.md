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
