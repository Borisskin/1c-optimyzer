# Explainer rules

Каждый файл `*.md` — одно правило с YAML frontmatter:

```markdown
---
id: <уникальный_snake_case>
applies_to: deadlock | operation | session | lock | exception | slow_op
priority: 100      # выше — проверяется первым
patterns:
  - field: event_type
    operator: ==
    value: TDEADLOCK
  - field: participants_count
    operator: ">="
    value: 2
---

# Title (первая # строка)

Markdown body. Доступны плейсхолдеры `{{var}}`, которые заполняются из
feature-dict (тех же ключей что в patterns + дополнительных).

Операторы:
- `==`, `!=`, `>=`, `<=`, `>`, `<`
- `in` (value — list)
- `contains` (для строк/списков)
- `matches` (regex)
```

Engine читает все *.md рекурсивно из этой папки, sorted by priority DESC.
`README.md` в корне игнорируется.

Hot-reload: вызов `engine.reload_rules()` перечитывает все файлы.
