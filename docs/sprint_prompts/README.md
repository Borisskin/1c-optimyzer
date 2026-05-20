# Sprint Prompts & Methodology

Архив **исходных промптов** от архитектора Opus 4.7 и методических материалов проекта 1C-Optimyzer. Размещены в репо для прозрачности — Opus и команда могут проследить эволюцию задач и решений по спринтам.

## Содержание

### Sprint prompts (постановки задач от архитектора)

| Файл | Что это |
|---|---|
| [SPRINT_0_PROMPT_OPTIMYZER.md](SPRINT_0_PROMPT_OPTIMYZER.md) | Sprint 0 — фундамент (Tauri + Python sidecar, базовый парсер ТЖ, smoke test) |
| [SPRINT_1_PROMPT_OPTIMYZER.md](SPRINT_1_PROMPT_OPTIMYZER.md) | Sprint 1 — folder ingestion + ru-RU UI + Big Data DuckDB Appender |
| [SPRINT_3_PROMPT_OPTIMYZER.md](SPRINT_3_PROMPT_OPTIMYZER.md) | Sprint 3 — Business Anatomy Views + AI Explainer + Deadlock Anatomy |

> **Sprint 2 и финальный Sprint 3 prompt** живут в [../SPRINT_2_PROMPT_OPTIMYZER.md](../SPRINT_2_PROMPT_OPTIMYZER.md) и [../SPRINT_3_PROMPT.md](../SPRINT_3_PROMPT.md) — это финальные, актуальные версии (в `docs/`). Файлы здесь — workspace-копии с предыдущих итераций, оставлены для истории.

### Методология и handoff'ы

| Файл | Что это |
|---|---|
| [development_methodology.md](development_methodology.md) | Общая методология разработки проекта (~38 KB) — стандарты PRD, sprint loop, sandboxing |
| [PROMPT_AUTHORING_STANDARD.md](../PROMPT_AUTHORING_STANDARD.md) | Стандарт оформления sprint-промптов (актуальная версия — в `docs/`) |
| [HANDOFF_CONTEXT.md](HANDOFF_CONTEXT.md) | Контекст передачи между фазами проекта |
| [CLAUDE_CODE_PREPROMPT_OPTIMYZER.md](CLAUDE_CODE_PREPROMPT_OPTIMYZER.md) | Базовый pre-prompt для Claude Code на этом проекте |
| [CLOSURE_INSTRUCTIONS_FOR_CLAUDE_CODE.md](CLOSURE_INSTRUCTIONS_FOR_CLAUDE_CODE.md) | Инструкции по закрытию спринта/модуля |

## Зачем эти файлы в git

До Sprint 3.5 они лежали **вне репо** — в workspace-папке Сергея (`D:\1C-Optimyzer\`), которая была родительской для `D:\1C-Optimyzer\1c-optimyzer\` (сам репо). Архитектор Opus, открывая репо на GitHub, **не видел эти материалы** — только код продукта.

В Sprint 3.5 репо подняли на уровень выше (`D:\1C-Optimyzer\` стал корнем git). Промпты перенесли сюда, чтобы Opus и любой ревьюер видел всю проектную картину через GitHub.

## Что НЕ переносили в репо (осталось локально)

- **PDF методики ЦУП «Корпоративный инструментальный пакет»** — материалы из ИТС 1С, copyright. В `.gitignore`.
- **Design_NonProduct/** — HTML-мокапы других продуктов Сергея (Agenter, GosLog, Konvey). К 1C-Optimyzer не относятся. В `.gitignore`.
- **.claude/** — локальные настройки Claude Code и skills. Не часть продукта. В `.gitignore`.
