# Golden Test Suite — Sprint 5 Phase E

Regression baseline для Query Analyzer. Каждый кейс — отдельная папка с двумя файлами:

```
positive/01_subquery_in_join/
├── query.sdbl          # текст SDBL запроса (UTF-8)
└── expected.json       # ожидаемые findings
```

## Категории

| Папка | Назначение | Минимум |
|---|---|---|
| `positive/` | Запросы с **явными** проблемами — каждое ожидаемое rule должно найтись | 10 |
| `negative/` | «Чистые» запросы — ожидается 0 findings уровня critical/warning | 10 |
| `edge_cases/` | Граничные случаи — пустой, только комментарии, очень вложенные, длинные | 10 |
| `semantic/` | Требуют подключённой `configuration_metadata` — синтетическая Test1CProf-подобная выгрузка | 5+ |

## Формат `expected.json`

```json
{
  "findings": [
    {
      "rule_id": "subquery_in_join",
      "severity": "warning",
      "line_range": [3, 4]
    }
  ],
  "requires_configuration": false,
  "notes": "Опционально: краткое описание сути кейса"
}
```

- `findings` — массив **ожидаемых** rule_id (точный либо подмножество).
  Runner проверяет что КАЖДЫЙ ожидаемый rule_id присутствует в actual findings.
  Если actual содержит дополнительные findings — это OK для positive (другие rules
  тоже могут срабатывать), но проверяется отсутствие critical/warning для negative.
- `line_range` — опциональный hint, не валидируется строго (1-based).
- `requires_configuration` — если `true`, runner подгружает test_configuration_store fixture.
- `notes` — комментарий для людей, не используется автоматически.

## Runner

`backend/tests/test_golden_suite.py` собирает все папки `positive/`, `negative/`,
`edge_cases/`, `semantic/` через `pytest.mark.parametrize`. Один pytest вызов — все
golden cases.

## Расширение

Чтобы добавить новый кейс:
1. Создайте папку в нужной категории: `positive/NN_короткое_имя/`
2. Положите `query.sdbl` с реальным SDBL текстом
3. Создайте `expected.json` с ожидаемыми findings
4. Прогоните `pytest tests/test_golden_suite.py -v` — должен пройти

## Phase F (real-world) — Sprint 6

Папка `real_world/` зарезервирована под Phase F (10 запросов извлечённых из
реальных DBMSSQL событий с stack trace). Sprint 5 эту фазу скипает по решению
Сергея — она переезжает в Sprint 6 где будет автоматический поиск SDBL по
Context (не manual extraction).
