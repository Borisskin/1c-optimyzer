#!/usr/bin/env python
"""S12 углублённый аудит: граничные случаи + негативные пути + безопасность.

Проверяет что продукт корректно (без падений и без порчи данных) реагирует на:
  - битый/пустой/несуществующий ввод (ingest)
  - несуществующие archive_id / event_id / session_id / preset (RPC)
  - read-only защиту SQL-консоли (DROP/DELETE/UPDATE должны блокироваться)
  - разные фильтры/сортировки view
ПРИВАТНОСТЬ: печатает только агрегаты/статусы, без значений полей.
Деструктивы — только безвредные (WHERE 1=0 / IF EXISTS).
"""
from __future__ import annotations

import sys
import tempfile
import traceback

PASS, FAIL, CRASH = "PASS", "FAIL", "CRASH"
results: list[tuple[str, str, str]] = []


def check(name: str, fn, predicate, note: str = "") -> None:
    """predicate(result)->bool. Если fn кидает — ловим; expect_raises обрабатывается отдельно."""
    try:
        r = fn()
        ok = predicate(r)
        results.append((name, PASS if ok else FAIL, note if not ok else ""))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + note) if not ok else ''}")
    except Exception as ex:  # noqa: BLE001
        results.append((name, CRASH, f"{type(ex).__name__}: {ex}"))
        print(f"[CRASH] {name}: {type(ex).__name__}: {ex}")


def check_raises(name: str, fn, exc_types) -> None:
    """Ожидаем что fn кинет исключение из exc_types (корректная валидация ввода)."""
    try:
        fn()
        results.append((name, FAIL, "ожидалось исключение, но его не было"))
        print(f"[FAIL] {name}: ожидалось исключение, не было")
    except exc_types as ex:
        results.append((name, PASS, ""))
        print(f"[PASS] {name}: корректно отклонено ({type(ex).__name__})")
    except Exception as ex:  # noqa: BLE001
        results.append((name, FAIL, f"неожиданный тип: {type(ex).__name__}"))
        print(f"[FAIL] {name}: неожиданный тип исключения {type(ex).__name__}: {ex}")


def main() -> int:
    from optimyzer_backend.rpc import handlers as H
    from optimyzer_backend.rpc import plan_analyzer_rpc as P
    from optimyzer_backend.rpc import sql_antipatterns_rpc as A
    from optimyzer_backend.rpc import sql_rpc
    from optimyzer_backend.rpc import views_rpc as V

    tj = sys.argv[1] if len(sys.argv) > 1 else r"C:\1C-TechLog"

    print("=== INGEST EDGE CASES ===")
    check_raises("ingest: несуществующий путь", lambda: H.load_directory(r"C:\__nope_xyz_123"),
                 (FileNotFoundError, NotADirectoryError))
    # пустая папка -> ingest со status=error («лог-файлы не найдены»)
    empty = tempfile.mkdtemp(prefix="s12_empty_")
    st = H.load_directory(empty)
    fin = H.wait_for_archive(st["archive_id"], timeout_sec=30)
    check("ingest: пустая папка -> status=error", lambda: fin,
          lambda r: r.get("status") == "error", "ожидался status=error при отсутствии .log")

    # битый .log (мусор без валидных событий) -> не падает, events_parsed=0
    bad = tempfile.mkdtemp(prefix="s12_bad_")
    import os
    with open(os.path.join(bad, "26052810.log"), "w", encoding="utf-8") as f:
        f.write("это не технологический журнал\nпросто мусор\x00\x01\n")
    stb = H.load_directory(bad)
    finb = H.wait_for_archive(stb["archive_id"], timeout_sec=30)
    check("ingest: битый файл -> не падает", lambda: finb,
          lambda r: r.get("status") in ("ready", "error"), "не должен падать на мусоре")

    print("\n=== загрузка боевого архива ===")
    real = H.load_directory(tj)
    aid = real["archive_id"]
    fr = H.wait_for_archive(aid, timeout_sec=900)
    if fr.get("status") != "ready":
        print(f"[CRASH] боевой архив не готов: {fr.get('status')}")
        return 1
    con = H._ARCHIVES[aid]["store"].open()
    print(f"  ready: events={fr.get('events_parsed')}")

    print("\n=== НЕГАТИВНЫЕ ПУТИ RPC ===")
    check("view_slow_queries(несущ. archive)", lambda: V.view_slow_queries("bad-archive-id"),
          lambda r: r.get("ok") is False, "ожидался ok=False")
    check("get_tj_plan(несущ. event_id)", lambda: P.get_tj_plan_rpc(aid, 999_999_999),
          lambda r: r.get("ok") is False, "ожидался ok=False event_not_found")
    check("deadlock_anatomy(несущ. event_id)", lambda: V.view_deadlock_anatomy(aid, 999_999_999),
          lambda r: (r.get("ok") is False) or (r.get("found") is False),
          "ожидался ok=False или found=False")
    check_raises("preset(неизвестный)", lambda: H._ARCHIVES[aid]["store"].run_preset("nope_preset"),
                 (ValueError,))
    check("operation_anatomy(несущ. операция)", lambda: V.view_operation_anatomy(aid, "Нет.Такой.Операции"),
          lambda r: r.get("ok") is True, "не должен падать, ok=True с пустыми данными")

    print("\n=== SQL-КОНСОЛЬ: read-only защита (безвредные деструктивы) ===")
    # Записывающие операции должны блокироваться (ok=False / error), не выполняться.
    check("execute_sql: SELECT работает", lambda: sql_rpc.execute_sql(aid, "SELECT COUNT(*) AS n FROM events"),
          lambda r: r.get("ok") is True and r.get("rows"), "SELECT должен работать")
    check("execute_sql: DELETE заблокирован", lambda: sql_rpc.execute_sql(aid, "DELETE FROM events WHERE 1=0"),
          lambda r: r.get("ok") is False, "запись должна блокироваться (read-only)")
    check("execute_sql: UPDATE заблокирован", lambda: sql_rpc.execute_sql(aid, "UPDATE events SET id=id WHERE 1=0"),
          lambda r: r.get("ok") is False, "запись должна блокироваться (read-only)")
    check("execute_sql: DROP заблокирован", lambda: sql_rpc.execute_sql(aid, "DROP TABLE IF EXISTS _s12_audit_nope"),
          lambda r: r.get("ok") is False, "DDL должен блокироваться (read-only)")
    check("execute_sql: битый SQL -> ok=False", lambda: sql_rpc.execute_sql(aid, "SELZECT FROM nowhere ((("),
          lambda r: r.get("ok") is False, "битый SQL — мягкая ошибка, не краш")
    check("validate_sql: валидный", lambda: sql_rpc.validate_sql_rpc("SELECT 1 AS x"),
          lambda r: isinstance(r, dict))
    check("get_schema", lambda: sql_rpc.get_schema_rpc(aid),
          lambda r: isinstance(r, dict))

    print("\n=== АНТИПАТТЕРНЫ: edge ===")
    check("antipatterns: пустой SQL", lambda: A.detect_rpc("", "mssql"),
          lambda r: r.get("ok") is True)
    check("antipatterns: PG-режим без PG-данных", lambda: A.detect_rpc("SELECT 1", "postgres"),
          lambda r: r.get("ok") is True)
    check("antipatterns: невалидный engine", lambda: A.detect_rpc("SELECT 1", "oracle"),
          lambda r: r.get("ok") is False, "невалидный engine -> ok=False")
    check("antipatterns: parse_failed флаг присутствует", lambda: A.detect_rpc("SELECT FROM ((", "mssql"),
          lambda r: "parse_failed" in r, "ответ должен содержать parse_failed")

    print("\n=== ФИЛЬТРЫ / СОРТИРОВКИ ===")
    for sb in ("total_duration", "avg_duration", "max_duration", "count"):
        check(f"slow_queries sort_by={sb}", lambda sb=sb: V.view_slow_queries(aid, sort_by=sb),
              lambda r: r.get("ok") is True)
    for sb in ("total_duration_ms", "calls", "max_duration_ms"):
        check(f"top_operations sort_by={sb}", lambda sb=sb: V.view_top_business_operations(aid, sort_by=sb),
              lambda r: r.get("ok") is True)
    check("errors_feed event_types=[EXCP]", lambda: V.view_errors_feed(aid, event_types=["EXCP"]),
          lambda r: r.get("ok") is True)
    check("heatmap metric=error_count", lambda: V.view_activity_heatmap(aid, metric="error_count"),
          lambda r: r.get("ok") is True)

    print("\n=== ИТОГ АУДИТА ===")
    npass = sum(1 for _, s, _ in results if s == PASS)
    nfail = [(n, note) for n, s, note in results if s == FAIL]
    ncrash = [(n, note) for n, s, note in results if s == CRASH]
    print(f"PASS {npass}/{len(results)}")
    if nfail:
        print("FAIL:")
        for n, note in nfail:
            print(f"  - {n}: {note}")
    if ncrash:
        print("CRASH:")
        for n, note in ncrash:
            print(f"  - {n}: {note}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # cp1251-консоль не тянет не-ASCII
    except Exception:  # noqa: BLE001
        pass
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
