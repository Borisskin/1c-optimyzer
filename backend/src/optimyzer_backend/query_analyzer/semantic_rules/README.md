# Semantic Rules — Sprint 5

Семантические правила Query Analyzer. В отличие от синтаксических
(Sprint 4: 13 правил в `query_analyzer_rules/`), эти проверяют запрос
**против реальной структуры подключённой конфигурации 1С**.

## Активация

Каждое semantic rule имеет в frontmatter:

```yaml
category: semantic
requires: [configuration_metadata]
check_name: <имя_функции_чекера>
```

`requires: [configuration_metadata]` означает что rule **запускается только
если подключена XML-выгрузка конфигурации** (через
`configuration.connect` RPC). Если выгрузка не подключена — rule
**silent**: ни findings, ни warning «не могу проверить» на каждом
запросе. Только глобальный badge в UI показывает статус.

`check_name` указывает на функцию-чекер в
`semantic_checks.SEMANTIC_CHECKS`. Чекер получает `(query_text, rule,
config_store)` и возвращает list[Finding]. Чекер сам извлекает токены
из запроса через `sdbl_tokenizer` и сверяет их с структурой.

## Плейсхолдеры в markdown body

Чекеры подставляют `{{key}}` → value в body перед возвратом finding.
Доступные placeholders зависят от чекера. Типичные:

- `{{object_full_name}}` — `Справочник.Контрагенты`
- `{{similar_objects}}` — markdown list похожих имён (Levenshtein)
- `{{field_name}}`, `{{attribute_name}}` — имя проблемного поля
- `{{available_dimensions}}`, `{{available_attributes}}` — что доступно
- `{{virtual_table}}` — `Остатки`, `Обороты`, и т.п.
- `{{valid_virtual_tables}}` — какие vtable допустимы

## Какие правила есть (Sprint 5)

| Файл | Чекер | Когда срабатывает |
|---|---|---|
| `object_not_exists.md` | `object_not_exists` | `ИЗ Справочник.Х` где Х нет в конфигурации |
| `virtual_table_not_supported.md` | `virtual_table_not_supported` | `РегистрНакопления.Х.СрезПоследних` (vtable для регистров сведений) |
| `vyrazit_type_not_exists.md` | `vyrazit_type_not_exists` | `ВЫРАЗИТЬ(... КАК Документ.Y)` где Y нет |
| `register_dimension_or_field_missing.md` | `register_dimension_or_field_missing` | `РегистрНакопления.Х.Остатки(, Поле = ...)` где Поле — не измерение |
| `enum_value_not_exists.md` | `enum_value_not_exists` | `Перечисление.Х.НесуществующееЗначение` |
| `attribute_not_exists_in_from_alias.md` | `attribute_not_exists_in_from_alias` | `FROM Справочник.Контрагенты КАК К ... К.НесуществующийРеквизит` |
| `register_resource_used_as_dimension.md` | `register_resource_used_as_dimension` | `РегНак.Х.Остатки(, Ресурс = ...)` (фильтр по ресурсу, не измерению) |
| `constant_used_with_dot.md` | `constant_used_with_dot` | `Константа.Х.Поле` (у констант полей нет) |

## Что НЕ делает Sprint 5

- Не парсит модули `.bsl` (это Sprint 6 — поиск SDBL по DBMSSQL.Context)
- Не работает с базой 1С напрямую (только XML выгрузка)
- Не делает полный SDBL парсер — regex tokenizer достаточен для
  семантической валидации в первом приближении

## Pivot rule (ADR-031)

Если на real запросах regex-based tokenizer даёт <70% точность —
рассмотреть pyparsing tokenizer или BSL Language Server. Sprint 5
baseline: regex.
