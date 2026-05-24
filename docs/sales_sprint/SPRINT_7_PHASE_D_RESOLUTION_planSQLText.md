# Sprint 7 Phase D — planSQLText в ТЖ: РЕШЕНО ✅

**Дата:** 2026-05-25
**Sprint:** 7 Phase D (Plan Analyzer — auto-extract из ТЖ)
**Статус:** ✅ RESOLVED — фича работает на 1С 8.3.27.1859 + MSSQL

## Root cause

`<plansql/>` обязан находиться **на уровне `<config>` как sibling от `<log>`**,
а **НЕ внутри `<log>`**. В прежней версии скрипта мы помещали его внутрь
`<log>`, поэтому платформа тихо его игнорировала.

Дополнительно `<property name="plansqltext"/>` идёт **внутри `<log>`** как
обычное свойство события — это явная декларация что поле должно записываться,
безопаснее чем полагаться на `<property name="all"/>`.

Источник: официальная документация 1С — [kb.1ci.com 3.23.2.1](https://kb.1ci.com/1C_Enterprise_Platform/Guides/Administrator_Guides/1C_Enterprise_8.3.24_Administrator_Guide/Appendix_3._Description_and_location_of_internal_files/3.23._logcfg.xml/3.23.2._Configuration_file_structure/),
подтверждено живым тестом на стенде Сергея.

## Правильная структура logcfg.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<config xmlns="http://v8.1c.ru/v8/tech-log">

    <log location="C:\1C-TechLog" history="72">
        <!-- ... events ... -->
        <event>
            <eq property="name" value="DBMSSQL" />
            <gt property="duration" value="10" />
        </event>

        <!-- ... остальные events ... -->

        <property name="all" />
        <property name="plansqltext" />   <!-- ← ВНУТРИ <log> -->
    </log>

    <plansql />                            <!-- ← НА УРОВНЕ <config>, sibling <log>! -->
</config>
```

## Подтверждение работы

После применения patch'a и rest ragent на тестовом стенде (1С 8.3.27.1859,
Test1CProf на MSSQL):

```
$ find C:/1C-TechLog/ -name "*.log" -mmin -5 -exec grep -c "planSQLText" {} \;
506   ← полтыщи событий с планами за 5 минут обычной работы
```

Пример реального события (стартовый SQL платформы):
```
Sql="SELECT 1 WHERE OBJECT_ID('FORMAT_NUMBER', 'FN') IS NOT NULL"
planSQLText="
0, 0, 1, 0, 1E-007, 11, 1.94E-006, 1,   |--Compute Scalar(DEFINE:([Expr1000]=(1)))
1, 1, 1, 0, 6.8E-007, 9, 1.84E-006, 1,        |--Filter(WHERE:(...))
1, 1, 1, 0, 1.16E-006, 9, 1.16E-006, 1,             |--Constant Scan
"
```

Реальный SQL запрос платформы:
```
Sql="select count(*) from sysobjects where name IN (N'Config', N'ConfigSave', ...)"
planSQLText="
0, ..., 0.017, 1,   |--Compute Scalar(DEFINE:([Expr1022]=CONVERT_IMPLICIT(int,[Expr1025],0)))
1, ..., 0.017, 1,        |--Stream Aggregate(DEFINE:([Expr1025]=Count(*)))
5, ..., 0.017, 1,             |--Nested Loops(Inner Join, OUTER REFERENCES:(...))
5, ..., 0.00329, 1,                  |--Filter(WHERE:(has_access(...)))
..."
```

Format: SHOWPLAN_TEXT с дополнительными колонками cost/cpu/io/rows перед
operator tree (формат 1С платформы, не стандартный SHOWPLAN_TEXT).

## История попыток (что НЕ работало и почему)

| # | Структура | Результат | Объяснение |
|---|---|---|---|
| 1 | `<plan/>` (без всего, внутри `<log>`) | DBMSSQL пишется, plan нет | Неправильное имя тега + неправильный уровень |
| 2 | `<plan><event>...DBMSSQL...</event></plan>` (внутри `<log>`) | DBMSSQL пишется, plan нет | Неправильное имя тега + неправильный уровень |
| 3 | `<plansql/>` (внутри `<log>`) | DBMSSQL пишется, plan нет | **Неправильный уровень** — должен быть в `<config>` |
| 4 | `<plansql/>` + `<property name="plansqltext"/>` (оба внутри `<log>`) | DBMSSQL пишется, plan нет | Та же ошибка: `<plansql/>` не в `<config>` |
| 5 | Shotgun (все 6 вариантов вместе, внутри `<log>`) | DBMSSQL пишется, plan нет | Всё на неправильном уровне |
| 6 | **`<plansql/>` в `<config>` + `<property name="plansqltext"/>` в `<log>`** | ✅ **506 planSQLText events за 5 мин** | По официальной доке |

## Patch скрипт

`scripts/patch-logcfg-for-plans.ps1` обновлён до правильной структуры:
- self-elevation через UAC
- backup перед изменением
- idempotent (cleanup старых неправильных размещений)
- restart 1C Server Agent
- preserve whitespace и комментарии

```powershell
.\scripts\patch-logcfg-for-plans.ps1
# UAC → Yes → patch + restart за ~7 секунд
```

## Документация для пользователей

`docs/onboarding/enable-dbmssql-plans.md` обновлён согласно новой проверенной
структуре.

## Связанные коммиты

- `195c22a` — Phase D код (parser plan_text, UI «Из архива ТЖ», PlanTextView, AI prompt)
- `1119cc1` — Phase E тесты
- `6ce38a2` — Phase F closure docs
- (этот коммит) — patch скрипт + резолюция

## Источники

- [Официальная 1С документация — logcfg.xml structure (1ci.com)](https://kb.1ci.com/1C_Enterprise_Platform/Guides/Administrator_Guides/1C_Enterprise_8.3.24_Administrator_Guide/Appendix_3._Description_and_location_of_internal_files/3.23._logcfg.xml/3.23.2._Configuration_file_structure/)
- [Примеры настроек ТЖ — infostart.ru/articles/2020498](https://infostart.ru/1c/articles/2020498/)
