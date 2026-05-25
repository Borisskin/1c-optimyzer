"""Sprint 9 Phase A — Сбор real-world fixtures.

Запуск (из корня репо):
    python tools/sprint9_collect/extract_fixtures.py

Что делает:
1. Извлекает PG queries + planSQLText из pg_tj_samples/dbpostgrs_sample.log
2. Генерирует 30+ синтетических MSSQL запросов в формате sp_executesql
3. Копирует 10 repr. .sqlplan файлов из research/
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = ROOT / "backend" / "tests" / "fixtures" / "real_world"
PG_LOG = ROOT / "tools" / "sprint8_discovery" / "pg_tj_samples" / "dbpostgrs_sample.log"


# ---------------------------------------------------------------------------
# A.2 — PG queries
# ---------------------------------------------------------------------------

def extract_pg_queries() -> list[str]:
    """Извлекаем SQL= из DBPOSTGRS лога (реальные запросы 1С к pgBase)."""
    out_dir = FIXTURES_DIR / "pg_queries"
    out_dir.mkdir(parents=True, exist_ok=True)

    content = PG_LOG.read_text(encoding="utf-8-sig", errors="replace")

    # Ищем Sql='...' и Sql="..." (обе кавычки используются)
    # Паттерн: ,Sql='...',  или ,Sql="..."
    # Запросы могут быть многострочными, но обрываются на следующем field
    patterns = [
        re.compile(r',Sql=\'((?:[^\']|\'\')*?)\',(?:planSQLText=|RowsAffected=|Result=)', re.DOTALL),
        re.compile(r',Sql="((?:[^"]|"")*?)",(?:planSQLText=|RowsAffected=|Result=)', re.DOTALL),
    ]

    queries: list[str] = []
    for pat in patterns:
        for m in pat.finditer(content):
            sql = m.group(1).strip()
            if sql and not sql.lower().startswith(("set ", "show ", "alter ", "explain")):
                queries.append(sql)

    # Уникальные, по первым 100 символам
    seen: dict[str, str] = {}
    for q in queries:
        key = q[:100].lower()
        if key not in seen:
            seen[key] = q

    unique = list(seen.values())[:50]  # берём до 50
    (out_dir / "queries.json").write_text(
        json.dumps(unique, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[A.2] PG queries: {len(unique)} extracted -> {out_dir/'queries.json'}")
    return unique


# ---------------------------------------------------------------------------
# A.4 — PG plan texts
# ---------------------------------------------------------------------------

def extract_pg_plan_texts() -> list[str]:
    """Извлекаем planSQLText="..." блоки из лога."""
    out_dir = FIXTURES_DIR / "pg_plans_text"
    out_dir.mkdir(parents=True, exist_ok=True)

    content = PG_LOG.read_text(encoding="utf-8-sig", errors="replace")

    # planSQLText='...' или planSQLText="..."
    patterns = [
        re.compile(r',planSQLText=\'((?:[^\']|\'\')*?)\',(?:RowsAffected=|Result=)', re.DOTALL),
        re.compile(r',planSQLText="((?:[^"]|"")*?)",(?:RowsAffected=|Result=)', re.DOTALL),
    ]

    plans: list[str] = []
    for pat in patterns:
        for m in pat.finditer(content):
            plan = m.group(1).strip()
            if plan and len(plan) > 30:  # минимум что-то значимое
                plans.append(plan)

    # Уникальные по первым 80 символам
    seen: dict[str, str] = {}
    for p in plans:
        key = p[:80].lower()
        if key not in seen:
            seen[key] = p

    unique = list(seen.values())[:30]

    for i, plan in enumerate(unique):
        (out_dir / f"plan_{i:02d}.txt").write_text(plan, encoding="utf-8")

    print(f"[A.4] PG plan texts: {len(unique)} extracted -> {out_dir}")
    return unique


# ---------------------------------------------------------------------------
# A.1 — Синтетические MSSQL sp_executesql queries (30+)
# ---------------------------------------------------------------------------

# Реалистичные 1С T-SQL запросы в правильном формате sp_executesql
SYNTHETIC_MSSQL_QUERIES = [
    # 1. Справочник — простой SELECT
    {
        "sql": "exec sp_executesql N'SELECT TOP 1000 T1._IDRRef, T1._Code, T1._Description, T1._Fld1234RRef, T1._Fld1235 FROM dbo._Reference15 T1 (NOLOCK) WHERE T1._Fld1236 = @P1 ORDER BY T1._Description', N'@P1 nvarchar(128)', N'ACTIVE'",
        "duration_us": 450000,
        "comment": "Выборка из справочника Контрагенты с фильтром по статусу"
    },
    # 2. JOIN справочник + регистр
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Code, T2._Fld5001 FROM dbo._Reference15 T1 INNER JOIN dbo._InfoRg5000 T2 ON T1._IDRRef = T2._Fld5000RRef WHERE T1._Marked = 0x00 AND T2._Fld5002 = @P1', N'@P1 numeric(10)', 1",
        "duration_us": 1200000,
        "comment": "JOIN справочника с регистром сведений"
    },
    # 3. Документ с подзапросом
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Date_Time, T1._Number, T1._Fld7001RRef FROM dbo._Document70 T1 WHERE T1._Date_Time BETWEEN @P1 AND @P2 AND T1._Fld7002 IN (SELECT T2._IDRRef FROM dbo._Reference23 T2 WHERE T2._Code = @P3)', N'@P1 datetime, @P2 datetime, @P3 nvarchar(9)', '20250101 00:00:00', '20250131 23:59:59', '000001234'",
        "duration_us": 3500000,
        "comment": "Документы реализации за период с IN (subquery)"
    },
    # 4. SELECT * (антипаттерн)
    {
        "sql": "exec sp_executesql N'SELECT * FROM dbo._Document70 T1 WHERE T1._Posted = 0x01 AND T1._Date_Time >= @P1', N'@P1 datetime', '20250101 00:00:00'",
        "duration_us": 5000000,
        "comment": "SELECT * — антипаттерн"
    },
    # 5. NOT IN с подзапросом (антипаттерн)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef FROM dbo._Reference15 T1 WHERE T1._IDRRef NOT IN (SELECT T2._Fld7001RRef FROM dbo._Document70 T2 WHERE T2._Posted = 0x01) AND T1._Marked = 0x00', N''",
        "duration_us": 8000000,
        "comment": "NOT IN with subquery — антипаттерн"
    },
    # 6. LIKE с ведущим wildcard (антипаттерн)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Code, T1._Description FROM dbo._Reference15 T1 WHERE T1._Description LIKE @P1', N'@P1 nvarchar(200)', N'%ООО%'",
        "duration_us": 2300000,
        "comment": "LIKE с ведущим % — антипаттерн"
    },
    # 7. Функция в WHERE (антипаттерн)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, YEAR(T1._Date_Time) AS Год, MONTH(T1._Date_Time) AS Месяц, SUM(T1._Fld7010) AS Сумма FROM dbo._Document70 T1 WHERE YEAR(T1._Date_Time) = @P1 GROUP BY T1._IDRRef, YEAR(T1._Date_Time), MONTH(T1._Date_Time)', N'@P1 int', 2025",
        "duration_us": 12000000,
        "comment": "Функция YEAR() в WHERE — антипаттерн"
    },
    # 8. Регистр накопления — остатки
    {
        "sql": "exec sp_executesql N'SELECT T1._Fld10001RRef, SUM(T1._Fld10002) AS Остаток FROM dbo._AccumRg10000 T1 WHERE T1._Period = @P1 GROUP BY T1._Fld10001RRef', N'@P1 datetime', '20250101 00:00:00'",
        "duration_us": 890000,
        "comment": "Регистр накопления — агрегация остатков"
    },
    # 9. Топ медленных документов
    {
        "sql": "exec sp_executesql N'SELECT TOP 100 T1._IDRRef, T1._Number, T1._Date_Time, T2._Description AS Контрагент FROM dbo._Document70 T1 LEFT JOIN dbo._Reference15 T2 ON T1._Fld7001RRef = T2._IDRRef WHERE T1._Date_Time >= @P1 ORDER BY T1._Date_Time DESC', N'@P1 datetime', '20250101 00:00:00'",
        "duration_us": 670000,
        "comment": "Список документов с LEFT JOIN контрагента"
    },
    # 10. Временная таблица — INSERT SELECT
    {
        "sql": "exec sp_executesql N'INSERT INTO #T1 (_IDRRef, _Code, _Fld1234RRef) SELECT T1._IDRRef, T1._Code, T1._Fld1234RRef FROM dbo._Reference15 T1 WHERE T1._Marked = 0x00 AND T1._Fld1235 = @P1', N'@P1 bit', 0x01",
        "duration_us": 340000,
        "comment": "INSERT в temp table"
    },
    # 11. CTE + JOIN
    {
        "sql": "exec sp_executesql N'WITH CTE AS (SELECT T1._IDRRef, SUM(T1._Fld10002) AS Total FROM dbo._AccumRg10000 T1 GROUP BY T1._Fld10001RRef) SELECT T2._Code, T2._Description, C.Total FROM CTE C INNER JOIN dbo._Reference15 T2 ON C._IDRRef = T2._IDRRef WHERE C.Total > @P1', N'@P1 numeric(15,2)', 1000.00",
        "duration_us": 1800000,
        "comment": "CTE с агрегацией и JOIN"
    },
    # 12. ODBC формат {call sp_executesql}
    {
        "sql": "{call sp_executesql(N'SELECT T1._IDRRef, T1._Description FROM dbo._Reference37 T1 WHERE T1._Fld3700 = @P1 AND T1._Marked = 0x00', N'@P1 nvarchar(128)', N'MAIN_GROUP')}",
        "duration_us": 210000,
        "comment": "ODBC формат вызова sp_executesql"
    },
    # 13. Без параметров — константы в SQL
    {
        "sql": "exec sp_executesql N'SELECT COUNT(*) FROM dbo._Document70 T1 WHERE T1._Posted = 0x01'",
        "duration_us": 430000,
        "comment": "COUNT без параметров"
    },
    # 14. UPDATE
    {
        "sql": "exec sp_executesql N'UPDATE dbo._Reference15 SET _Fld1235 = @P1, _Fld1236 = @P2 WHERE _IDRRef = @P3', N'@P3 binary(16), @P1 bit, @P2 nvarchar(128)', 0x00, N'ARCHIVED', 0xA1B2C3D4E5F60718293A4B5C6D7E8F90",
        "duration_us": 150000,
        "comment": "UPDATE одной записи справочника"
    },
    # 15. Сложный JOIN (5 таблиц)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Number, T1._Date_Time, T2._Description AS Org, T3._Description AS Контрагент, T4._Description AS Договор, T5._Description AS Склад FROM dbo._Document70 T1 LEFT JOIN dbo._Reference10 T2 ON T1._Fld7003RRef = T2._IDRRef LEFT JOIN dbo._Reference15 T3 ON T1._Fld7001RRef = T3._IDRRef LEFT JOIN dbo._Reference25 T4 ON T1._Fld7004RRef = T4._IDRRef LEFT JOIN dbo._Reference19 T5 ON T1._Fld7005RRef = T5._IDRRef WHERE T1._Posted = 0x01 AND T1._Date_Time >= @P1 AND T1._Date_Time < @P2 ORDER BY T1._Date_Time DESC', N'@P1 datetime, @P2 datetime', '20250101 00:00:00', '20250201 00:00:00'",
        "duration_us": 4500000,
        "comment": "5-таближный JOIN для отчёта"
    },
    # 16. Регистр бухгалтерии
    {
        "sql": "exec sp_executesql N'SELECT T1._Period, T1._AccountRRef, T1._Fld30001RRef, SUM(T1._Fld30002Dt) - SUM(T1._Fld30002Ct) AS Сальдо FROM dbo._AccumRgT30000 T1 WHERE T1._Period >= @P1 AND T1._Fld30001RRef = @P2 GROUP BY T1._Period, T1._AccountRRef, T1._Fld30001RRef', N'@P1 datetime, @P2 binary(16)', '20250101 00:00:00', 0xAB12CD34EF561234567890ABCDEF1234",
        "duration_us": 2100000,
        "comment": "Регистр бухгалтерии — обороты"
    },
    # 17. ISNULL функция в WHERE (антипаттерн)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Description FROM dbo._Reference15 T1 WHERE ISNULL(T1._Fld1234RRef, 0x0) = @P1 AND T1._Marked = 0x00', N'@P1 binary(16)', 0x0",
        "duration_us": 1600000,
        "comment": "ISNULL() в WHERE — антипаттерн implicit convert"
    },
    # 18. EXISTS вместо IN (хороший паттерн)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Number FROM dbo._Document70 T1 WHERE EXISTS (SELECT 1 FROM dbo._Reference15 T2 WHERE T2._IDRRef = T1._Fld7001RRef AND T2._Fld1236 = @P1) AND T1._Date_Time >= @P2', N'@P1 nvarchar(128), @P2 datetime', N'VIP', '20250101 00:00:00'",
        "duration_us": 980000,
        "comment": "EXISTS — хороший паттерн"
    },
    # 19. DELETE с JOIN
    {
        "sql": "exec sp_executesql N'DELETE T1 FROM dbo._AccumRg10000 T1 WHERE T1._Period < @P1 AND T1._Fld10001RRef IN (SELECT _IDRRef FROM dbo._Reference15 WHERE _Marked = 0x01)', N'@P1 datetime', '20240101 00:00:00'",
        "duration_us": 5600000,
        "comment": "DELETE устаревших записей"
    },
    # 20. Merge (UPSERT)
    {
        "sql": "exec sp_executesql N'MERGE dbo._Reference15 AS target USING (SELECT @P1 AS _IDRRef, @P2 AS _Code, @P3 AS _Description) AS source ON (target._IDRRef = source._IDRRef) WHEN MATCHED THEN UPDATE SET target._Code = source._Code, target._Description = source._Description WHEN NOT MATCHED THEN INSERT (_IDRRef, _Code, _Description) VALUES (source._IDRRef, source._Code, source._Description);', N'@P1 binary(16), @P2 nvarchar(9), @P3 nvarchar(150)', 0xA1B2C3D4E5F60718293A4B5C6D7E8F91, N'000012345', N'ООО Ромашка'",
        "duration_us": 320000,
        "comment": "MERGE для справочника"
    },
    # 21. Периодический регистр
    {
        "sql": "exec sp_executesql N'SELECT TOP 1 T1._Fld8001, T1._Period FROM dbo._InfoRg8000 T1 WHERE T1._Fld8002RRef = @P1 AND T1._Period <= @P2 ORDER BY T1._Period DESC', N'@P1 binary(16), @P2 datetime', 0xB1C2D3E4F506172839405060708090A0, '20250115 00:00:00'",
        "duration_us": 120000,
        "comment": "Срез последних периодического регистра"
    },
    # 22. Полнотекстовый поиск через LIKE (антипаттерн)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Code, T1._Description, T1._Fld1240 FROM dbo._Reference15 T1 WHERE (T1._Description LIKE @P1 OR T1._Code LIKE @P1 OR T1._Fld1240 LIKE @P1) AND T1._Marked = 0x00', N'@P1 nvarchar(200)', N'%Иванов%'",
        "duration_us": 7800000,
        "comment": "Поиск по нескольким полям через LIKE % — антипаттерн"
    },
    # 23. DISTINCT в подзапросе
    {
        "sql": "exec sp_executesql N'SELECT DISTINCT T1._Fld7001RRef FROM dbo._Document70 T1 INNER JOIN dbo._Document70_VT7100 T2 ON T1._IDRRef = T2._Document70_IDRRef WHERE T1._Date_Time >= @P1 AND T2._Fld7101 > @P2', N'@P1 datetime, @P2 numeric(15,2)', '20250101 00:00:00', 0.00",
        "duration_us": 2400000,
        "comment": "DISTINCT с JOIN табличной части"
    },
    # 24. Запрос с UNION (антипаттерн — надо UNION ALL)
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Description, ''Клиент'' AS Тип FROM dbo._Reference15 T1 WHERE T1._Fld1236 = @P1 UNION SELECT T2._IDRRef, T2._Description, ''Поставщик'' AS Тип FROM dbo._Reference15 T2 WHERE T2._Fld1237 = @P1', N'@P1 bit', 0x01",
        "duration_us": 3100000,
        "comment": "UNION вместо UNION ALL — антипаттерн"
    },
    # 25. Запрос плана по хэшу
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Code, T1._Fld1234RRef FROM dbo._Reference15 T1 WHERE T1._IDRRef = @P1', N'@P1 binary(16)', 0xA1B2C3D4E5F60718293A4B5C6D7E8F90",
        "duration_us": 15000,
        "comment": "Point lookup по первичному ключу"
    },
    # 26. Агрегация без индекса
    {
        "sql": "exec sp_executesql N'SELECT T1._Fld10001RRef, T1._Fld10003RRef, SUM(T1._Fld10004) AS Количество, SUM(T1._Fld10005) AS Сумма FROM dbo._AccumRg10000 T1 WHERE T1._Period BETWEEN @P1 AND @P2 AND T1._Fld10006 = @P3 GROUP BY T1._Fld10001RRef, T1._Fld10003RRef HAVING SUM(T1._Fld10004) > @P4 ORDER BY Сумма DESC', N'@P1 datetime, @P2 datetime, @P3 binary(16), @P4 numeric(15,2)', '20250101 00:00:00', '20250131 23:59:59', 0xBEEFCAFED00DABCDEF1234567890ABCD, 100.00",
        "duration_us": 15000000,
        "comment": "Сложная агрегация регистра за период"
    },
    # 27. Вставка строк табличной части
    {
        "sql": "exec sp_executesql N'INSERT INTO dbo._Document70_VT7100 (_Document70_IDRRef, _KeyField, _Fld7101, _Fld7102RRef, _Fld7103) VALUES (@P1, @P2, @P3, @P4, @P5)', N'@P1 binary(16), @P2 binary(16), @P3 numeric(15,2), @P4 binary(16), @P5 nvarchar(150)', 0xDEADBEEFCAFED00DABCDEF1234567890, 0xCAFEBABED00D4B1D00ABCDEF12345678, 5000.00, 0xBEEFCAFED00DABCDEF1234567890ABCD, N'Ноутбук Dell XPS 15'",
        "duration_us": 80000,
        "comment": "Вставка строки в табличную часть документа"
    },
    # 28. Многострочный UPDATE с подзапросом
    {
        "sql": "exec sp_executesql N'UPDATE T1 SET T1._Fld1235 = @P1 FROM dbo._Reference15 T1 WHERE T1._IDRRef IN (SELECT DISTINCT T2._Fld7001RRef FROM dbo._Document70 T2 WHERE T2._Posted = 0x01 AND T2._Date_Time >= @P2 AND T2._Date_Time < @P3)', N'@P1 bit, @P2 datetime, @P3 datetime', 0x01, '20250101 00:00:00', '20250201 00:00:00'",
        "duration_us": 2700000,
        "comment": "UPDATE с подзапросом"
    },
    # 29. Запрос справочника + составной тип
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Code, T1._Description, T1._Fld1240_TYPE, T1._Fld1240_RRef, T1._Fld1240_RTRef FROM dbo._Reference15 T1 WHERE T1._Fld1236 = @P1 AND T1._Marked = 0x00 ORDER BY T1._Code', N'@P1 nvarchar(128)', N'GROUP_A'",
        "duration_us": 560000,
        "comment": "Справочник с составным типом (TYPE+RRef+RTRef)"
    },
    # 30. Implicit conversion через nvarchar vs binary
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef FROM dbo._Reference15 T1 WHERE CAST(T1._IDRRef AS nvarchar(36)) = @P1', N'@P1 nvarchar(36)', N'A1B2C3D4-E5F6-0718-2930-4B5C6D7E8F90'",
        "duration_us": 9000000,
        "comment": "CAST в WHERE — implicit conversion антипаттерн"
    },
    # 31. Запрос к журналу регистрации
    {
        "sql": "exec sp_executesql N'SELECT T1._RegistrationTime, T1._UserRRef, T1._EventCode, T1._Session, T1._Fld2001 FROM dbo._SystemLog T1 WHERE T1._RegistrationTime >= @P1 AND T1._EventCode = @P2 ORDER BY T1._RegistrationTime DESC', N'@P1 datetime, @P2 int', '20250120 00:00:00', 15",
        "duration_us": 1100000,
        "comment": "Запрос к журналу регистрации"
    },
    # 32. CASE WHEN в SELECT
    {
        "sql": "exec sp_executesql N'SELECT T1._IDRRef, T1._Number, T1._Date_Time, CASE WHEN T1._Fld7010 > @P1 THEN N''Высокий'' WHEN T1._Fld7010 > @P2 THEN N''Средний'' ELSE N''Низкий'' END AS Приоритет FROM dbo._Document70 T1 WHERE T1._Posted = 0x01 AND T1._Date_Time >= @P3', N'@P1 numeric(15,2), @P2 numeric(15,2), @P3 datetime', 100000.00, 10000.00, '20250101 00:00:00'",
        "duration_us": 780000,
        "comment": "CASE WHEN в SELECT — нормальный паттерн"
    },
]

def create_mssql_fixtures() -> None:
    out_dir = FIXTURES_DIR / "mssql_sp_executesql"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "queries.json").write_text(
        json.dumps(SYNTHETIC_MSSQL_QUERIES, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[A.1] MSSQL queries: {len(SYNTHETIC_MSSQL_QUERIES)} generated -> {out_dir/'queries.json'}")


# ---------------------------------------------------------------------------
# A.3 — Копируем .sqlplan файлы
# ---------------------------------------------------------------------------

SQLPLAN_SOURCES = {
    # filename: source path (relative to ROOT)
    "key_lookup.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/key_lookup_plan.sqlplan",
    "implicit_convert.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/implicit_convert_seek_plan.sqlplan",
    "exchange_spill.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/exchange_spill_plan.sqlplan",
    "memory_grant_wait.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/memory_grant_wait_plan.sqlplan",
    "param_sniffing.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/param-sniffing-posttypeid2.sqlplan",
    "missing_join_predicate.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/missing-join-predicate.sqlplan",
    "compile_memory_exceeded.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/compile_memory_exceeded_plan.sqlplan",
    "case_predicate.sqlplan": "research/PerformanceStudio/tests/PlanViewer.Core.Tests/Plans/case_predicate_plan.sqlplan",
    "1c_sys_tables.sqlplan": "tools/sprint7_discovery/sqlplans/test01_sys_tables.sqlplan",
    "1c_like_wildcard.sqlplan": "tools/sprint7_discovery/sqlplans/test02_like_wildcard.sqlplan",
    "1c_join_group_by.sqlplan": "tools/sprint7_discovery/sqlplans/test03_join_group_by.sqlplan",
    "1c_not_in_subquery.sqlplan": "tools/sprint7_discovery/sqlplans/test04_not_in_subquery.sqlplan",
    "1c_function_on_column.sqlplan": "tools/sprint7_discovery/sqlplans/test05_function_on_column.sqlplan",
}

def copy_sqlplan_fixtures() -> None:
    out_dir = FIXTURES_DIR / "mssql_plans"
    out_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for dest_name, src_rel in SQLPLAN_SOURCES.items():
        src = ROOT / src_rel
        if src.exists():
            shutil.copy2(src, out_dir / dest_name)
            copied += 1
        else:
            print(f"  [WARN] Not found: {src}")
    print(f"[A.3] MSSQL .sqlplan: {copied} copied -> {out_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    create_mssql_fixtures()
    extract_pg_queries()
    extract_pg_plan_texts()
    copy_sqlplan_fixtures()
    print("\n[Done] Fixtures collected.")
