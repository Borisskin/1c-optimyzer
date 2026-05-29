#!/usr/bin/env python
"""S12 headless-драйвер систематического прогона на реальном ТЖ-архиве.

Запуск (из backend venv, чтобы был установлен optimyzer_backend):
    D:\\1C-Optimyzer\\backend\\.venv\\Scripts\\python.exe scripts\\s12_run.py "C:\\1C-TechLog"

Что делает: load_directory -> wait_for_archive -> get_storage_stats, затем прогоняет
пресеты и все view_* (Module 1), вызывая зарегистрированные RPC-хендлеры in-process.

ПРИВАТНОСТЬ by-design: печатает ТОЛЬКО агрегаты (числа, ok/fail, имена ключей ответа,
длины списков). НИКОГДА не печатает значения полей событий (SQL, контексты, имена
пользователей, тексты исключений) — поэтому вывод безопасно класть в отчёт прогона.
"""
from __future__ import annotations

import sys
import time
import traceback
from typing import Any, Callable


def _summarize(r: Any) -> str:
    """Безопасная сводка ответа: структура + объёмы, без значений полей."""
    if isinstance(r, dict):
        parts: list[str] = []
        for k, v in r.items():
            if k == "ok":
                continue
            if isinstance(v, list):
                parts.append(f"{k}=[{len(v)}]")
            elif isinstance(v, dict):
                parts.append(f"{k}={{{len(v)}k}}")
            elif isinstance(v, bool):
                parts.append(f"{k}={v}")
            elif isinstance(v, (int, float)):
                parts.append(f"{k}={v}")
            elif v is None:
                parts.append(f"{k}=None")
            else:  # строка — длину, не значение
                parts.append(f"{k}=<str:{len(str(v))}>")
        return ", ".join(parts) if parts else "(empty)"
    if isinstance(r, list):
        return f"[list:{len(r)}]"
    return f"<{type(r).__name__}>"


def main() -> int:
    tj = sys.argv[1] if len(sys.argv) > 1 else r"C:\1C-TechLog"

    from optimyzer_backend.rpc import handlers as H
    from optimyzer_backend.rpc import views_rpc as V

    print(f"[S12] === headless run ===")
    print(f"[S12] TJ: {tj}")

    t0 = time.time()
    state = H.load_directory(tj)
    aid = state["archive_id"]
    print(f"[S12] archive_id={aid} initial_status={state['status']}")

    final = H.wait_for_archive(aid, timeout_sec=900)
    dt = time.time() - t0
    print(
        f"[S12] ingest: status={final['status']} files={final.get('file_count')} "
        f"events={final.get('events_parsed')} errors={len(final.get('errors', []))} in {dt:.1f}s"
    )
    for e in final.get("errors", [])[:10]:
        print(f"   parse-error: {str(e)[:160]}")
    if final.get("status") != "ready":
        print("[S12] ABORT — archive not ready")
        return 1

    stats = H.get_storage_stats(aid)
    print(
        f"[S12] stats: events={stats['events_count']} "
        f"db={stats['db_size_bytes'] / 1e6:.1f}MB eps={stats['parsing_speed_eps']:.0f}"
    )

    results: dict[str, str] = {}

    def run(name: str, fn: Callable[[], Any]) -> None:
        try:
            r = fn()
            ok = r.get("ok", True) if isinstance(r, dict) else True
            tag = "OK " if ok else "ERR"
            print(f"[{tag}] {name}: {_summarize(r)}")
            results[name] = tag.strip()
        except Exception as ex:  # noqa: BLE001
            print(f"[CRASH] {name}: {type(ex).__name__}: {ex}")
            traceback.print_exc()
            results[name] = "CRASH"

    # ---- Presets (агрегаты, без значений строк) ----
    def preset_summary(preset: str) -> dict[str, Any]:
        cols, rows = H._ARCHIVES[aid]["store"].run_preset(preset, limit=100)
        out: dict[str, Any] = {"ok": True, "rows": len(rows), "columns": len(cols)}
        if preset == "longest" and rows:
            # колонка duration_us — индекс 2 в SELECT (ts, event_type, duration_us, ...)
            durs = [r[2] for r in rows if r[2] is not None]
            if durs:
                out["max_duration_us"] = max(durs)
                out["min_duration_us"] = min(durs)
        return out

    for p in ("first_100", "longest", "deadlocks"):
        run(f"preset:{p}", lambda p=p: preset_summary(p))

    # ---- Module 1 views ----
    run("view_process_roles", lambda: V.view_process_roles(aid))
    run("view_duration_histogram", lambda: V.view_duration_histogram(aid))
    run("view_activity_heatmap", lambda: V.view_activity_heatmap(aid))
    run("view_errors_feed", lambda: V.view_errors_feed(aid, limit=500))
    run("view_locks_timeline", lambda: V.view_locks_timeline(aid))
    run("view_slow_queries", lambda: V.view_slow_queries(aid))
    run("view_top_business_operations[CALL]",
        lambda: V.view_top_business_operations(aid, event_types=["CALL"]))
    run("view_top_business_operations[all]",
        lambda: V.view_top_business_operations(aid))
    run("view_list_deadlocks", lambda: V.view_list_deadlocks(aid))

    # ================= FLAGSHIP (слой СУБД — на боевых DBMSSQL) =================
    from collections import Counter
    from pathlib import Path as _Path

    from optimyzer_backend.rpc import plan_analyzer_rpc as P
    from optimyzer_backend.rpc import sql_antipatterns_rpc as A

    store = H._ARCHIVES[aid]["store"]
    con = store.open()

    # Анализ плана: доступность planview + планы «Из архива ТЖ»
    run("plan_analyzer.status", lambda: P.status_rpc())
    run("plan_analyzer.list_tj_plans", lambda: P.list_tj_plans_rpc(aid, limit=50))
    pe = con.execute(
        "SELECT id FROM events WHERE plan_text IS NOT NULL AND plan_text <> '' "
        "ORDER BY duration_us DESC NULLS LAST LIMIT 1"
    ).fetchone()
    if pe:
        run("plan_analyzer.get_tj_plan[slowest]", lambda: P.get_tj_plan_rpc(aid, int(pe[0])))
    else:
        print("[skip] get_tj_plan: нет событий с plan_text")

    # SQL-антипаттерны на реальных exemplar-запросах (SQL в вывод НЕ печатается)
    try:
        sqls = [
            r[0]
            for r in con.execute(
                "SELECT ARG_MAX(sql_text, duration_us) FROM events "
                "WHERE event_type='DBMSSQL' AND sql_text IS NOT NULL "
                "GROUP BY sql_text_hash ORDER BY SUM(duration_us) DESC LIMIT 20"
            ).fetchall()
            if r[0]
        ]
        codes: Counter = Counter()
        with_finding = 0
        crashed = 0
        for s in sqls:
            try:
                res = A.detect_rpc(s, "mssql")
                fs = res.get("findings", []) if res.get("ok") else []
                if fs:
                    with_finding += 1
                for f in fs:
                    codes[f.get("code", "?")] += 1
            except Exception:  # noqa: BLE001
                crashed += 1
        tag = "OK " if crashed == 0 else "ERR"
        print(f"[{tag}] sql_antipatterns[mssql x{len(sqls)}]: with_findings="
              f"{with_finding}/{len(sqls)} crashes={crashed} codes={dict(codes)}")
        results["sql_antipatterns[mssql]"] = tag.strip()
    except Exception as ex:  # noqa: BLE001
        print(f"[CRASH] sql_antipatterns setup: {type(ex).__name__}: {ex}")
        results["sql_antipatterns[mssql]"] = "CRASH"

    # Дедлок-анатомия (в архиве есть TDEADLOCK)
    dl = con.execute(
        "SELECT id FROM events WHERE event_type='TDEADLOCK' ORDER BY ts LIMIT 1"
    ).fetchone()
    if dl:
        run("view_deadlock_anatomy[#1]", lambda: V.view_deadlock_anatomy(aid, int(dl[0])))
    else:
        print("[skip] deadlock_anatomy: нет TDEADLOCK")

    # Анатомия топ-операции (по числу событий)
    opr = con.execute(
        "SELECT context_normalized FROM events "
        "WHERE context_normalized IS NOT NULL AND context_normalized <> '' "
        "GROUP BY context_normalized ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    if opr:
        run("view_operation_anatomy[top]", lambda: V.view_operation_anatomy(aid, opr[0]))

    # .sqlplan через planview CLI (реальная фикстура из репозитория)
    fx = (
        _Path(__file__).resolve().parents[1]
        / "backend" / "tests" / "fixtures" / "real_world" / "mssql_plans" / "key_lookup.sqlplan"
    )
    if fx.is_file():
        run("plan_analyzer.analyze_file[fixture]", lambda: P.analyze_file_rpc(str(fx)))
    else:
        print(f"[skip] analyze_file: фикстура не найдена {fx}")

    # ---- Итог ----
    print("\n[S12] === summary ===")
    okc = sum(1 for v in results.values() if v == "OK")
    print(f"[S12] scenarios: {okc}/{len(results)} OK")
    bad = {k: v for k, v in results.items() if v != "OK"}
    if bad:
        print(f"[S12] NOT-OK: {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
