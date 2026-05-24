# Sprint 7 Phase D — Known Issue: planSQLText не пишется в ТЖ (1С 8.3.27 + MSSQL)

**Дата:** 2026-05-25
**Sprint:** 7 (Plan Analyzer)
**Phase:** D — Auto-extract DBMSSQL.Plan из ТЖ
**Статус:** ❌ NOT REPRODUCIBLE на тестовом стенде → tech debt в Sprint 8

## Контекст

Phase D задумывалась как третий путь импорта планов в Plan Analyzer (помимо
`.sqlplan` файла и paste XML): автоматическое извлечение `planSQLText` из
DBMSSQL событий технологического журнала 1С.

**Код Phase D готов и закоммичен** (commits `195c22a` Phase D, `1119cc1` Phase E,
`6ce38a2` Phase F):
- `tj_parser.py` — извлекает поле `planSQLText` в `ParsedEvent.plan_text`
- `duckdb_store.py` — schema + миграция `_migrate_plan_text`
- UI tab «Из архива ТЖ» в `PlanAnalyzer.tsx`
- `PlanTextView` для отображения text-формата плана
- `ai_explainer.py` — AI prompt с поддержкой text/xml формата
- 50+ unit tests + regression на 82 .sqlplan

**Что НЕ воспроизводится:** наполнение поля `planSQLText` в .log файлах ТЖ
на тестовом стенде Сергея.

## Конфигурация тестового стенда

- **1С платформа:** 8.3.27.1859 (x86-64, сервер + клиент)
- **БД:** Microsoft SQL Server, инстанс `localhost:2541`
- **База:** `Test1CProf` (типовая БП 3.0)
- **ОС:** Windows 10 Pro 22H2 (build 19045)
- **Пользователь SQL:** интегрированная авторизация Windows (под `USR1CV8`)
- **logcfg.xml:** `C:\Program Files\1cv8\conf\logcfg.xml`, location `C:\1C-TechLog`

## Что пробовали

Шесть синтаксических вариантов logcfg.xml, ragent перезапускался после каждого,
запускался tj-simulator кнопка 5 (20 неэффективных запросов > 200мс). Каждый
раз получали ~150-350 свежих DBMSSQL событий, но **ни в одном** не появлялось
поле с `plan` в имени.

| # | Синтаксис | Результат |
|---|---|---|
| 1 | `<plan/>` (пустой, без фильтра) | DBMSSQL пишется, planSQLText нет |
| 2 | `<plan><event><eq property="name" value="DBMSSQL"/><gt property="duration" value="10"/></event></plan>` | DBMSSQL пишется, planSQLText нет |
| 3 | `<plansql/>` (пустой) | DBMSSQL пишется, planSQLText нет |
| 4 | `<plansql/>` + `<property name="plansqltext"/>` (lowercase) | DBMSSQL пишется, planSQLText нет |
| 5 | `<plansql/>` + `<property name="planSQLText"/>` (camelCase) | DBMSSQL пишется, planSQLText нет |
| 6 | Shotgun: `<plan/>` + `<plansql/>` + `<property name="planSQLText"/>` + `<property name="plansqltext"/>` + `<property name="Plan"/>` + `<property name="plan"/>` все вместе | DBMSSQL пишется, planSQLText нет |

Проверка проводилась через:
```bash
find C:/1C-TechLog/ -name "*.log" -newer logcfg.xml -exec grep -l "plan" {} \;
# 0 файлов
grep -oE "[A-Za-z][A-Za-z0-9:_]*=" rphost_*/.log | sort -u | grep -i plan
# пусто
```

`<property name="all"/>` присутствует в logcfg — все остальные DBMSSQL-поля
(`Sql`, `Rows`, `Context`, `Usr`, etc.) пишутся корректно. Только `plan`
не появляется ни в каком виде.

## Гипотезы (для Sprint 8 investigation)

### H1: SHOWPLAN permissions для USR1CV8

SQL Server по умолчанию требует право `SHOWPLAN` на уровне базы данных, чтобы
запросы могли возвращать execution plan. Если у служебного пользователя 1С
этого права нет — план тихо не возвращается.

Проверить:
```sql
SELECT name, type_desc FROM sys.database_permissions
WHERE permission_name = 'SHOWPLAN' AND grantee_principal_id = USER_ID('USR1CV8');

GRANT SHOWPLAN TO USR1CV8;
```

### H2: Изменение синтаксиса в 8.3.27

В новых версиях платформы (8.3.20+) синтаксис `<plan>` мог быть переименован,
заменён, или вынесен в отдельную подсистему. Документация ИТС, которую мы
нашли через web search, относится к более старым версиям.

Проверить:
- Свежую ИТС-статью «Структура logcfg.xml» для 8.3.27
- Release notes 8.3.20...8.3.27 на предмет изменений ТЖ
- Поддержку 1С (это тестовая лицензия — есть доступ)

### H3: Performance Studio Extension от 1С

Возможно в 8.3.27 функционал записи планов перенесён в отдельное расширение
платформы — «Performance Studio» (не путать с Erik Darling). Это коммерческая
дополнительная подсистема.

Проверить:
- Документация 1С Performance Studio
- Установлено ли это на тестовом стенде

### H4: Версия SQL Server не поддерживает SHOWPLAN_XML

Платформа может пытаться запросить план, но SQL Server возвращает ошибку —
тихо в логи 1С это не пишется. Проверить через `sp_executesql` с явным
SHOWPLAN_TEXT в SSMS.

## Workaround для пользователей сейчас

Три остальных пути импорта в Plan Analyzer **работают полноценно**:
1. **Импорт `.sqlplan` файла** — экспорт из SSMS «Save Execution Plan As...»
2. **Paste XML** — копи-паст plan XML из SSMS Plan Viewer
3. **PerformanceStudio CLI + AI** — анализ + объяснение работают на любом из вышеуказанных

UI вкладки «Из архива ТЖ» показывает корректное empty-state с инструкцией
«В архиве нет планов запросов. Чтобы включить — см. enable-dbmssql-plans.md».

## Что закоммичено

- `scripts/patch-logcfg-for-plans.ps1` v2 — добавляет `<plansql/>` +
  `<property name="plansqltext"/>` в logcfg. **Помечен как experimental** —
  фактически на 8.3.27 + MSSQL не активирует запись планов. См. этот документ.
- `docs/onboarding/enable-dbmssql-plans.md` — пользовательская инструкция.
  Содержит предупреждение что на 8.3.27 функция требует investigation.

## Следующие шаги Sprint 8

1. **Investigation 1-2 дня:** проверить H1-H4 на тестовом стенде
2. Если нашли причину — обновить `patch-logcfg-for-plans.ps1` + docs
3. Если нет — открыть тикет в 1С support, оставить feature как opt-in:
   «работает только при правильно настроенной ТЖ — см. инструкцию»
4. Альтернатива: integration с **Performance Studio от 1С** (если есть)

## Логи попыток

В этой сессии создано **8 backup'ов** `logcfg.xml.backup.YYYYMMDD-HHMMSS`
в `C:\Program Files\1cv8\conf\`. Содержат варианты #1-6 + откаты. Оригинал
без изменений = `logcfg.xml.backup.20260525-000914` (mtime 2026-05-19, 5850 байт).
