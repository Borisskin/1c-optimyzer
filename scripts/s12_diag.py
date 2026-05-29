#!/usr/bin/env python
"""S12 диагностика состава распарсенного архива (read-only к .duckdb).

ПРИВАТНОСТЬ: печатает только агрегаты — типы событий, counts, наличие полей,
временной диапазон. Никаких значений (SQL, контекстов, имён).

Запуск: backend\\.venv\\Scripts\\python.exe scripts\\s12_diag.py [archive_id]
Без archive_id берёт самый свежий .duckdb из %APPDATA%\\1c-optimyzer\\duckdb.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb


def main() -> int:
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    dbdir = Path(appdata) / "1c-optimyzer" / "duckdb"
    if len(sys.argv) > 1:
        db = dbdir / f"{sys.argv[1]}.duckdb"
    else:
        cands = sorted(dbdir.glob("*.duckdb"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            print(f"no .duckdb in {dbdir}")
            return 1
        db = cands[0]
    print(f"db: {db.name}  ({db.stat().st_size/1e6:.1f} MB)")

    con = duckdb.connect(str(db), read_only=True)

    print("\n== event_type distribution ==")
    print(f"{'type':<14}{'count':>10}{'with_sql':>10}{'with_plan':>11}{'with_engine':>12}")
    for row in con.execute("""
        SELECT event_type, COUNT(*) n, COUNT(sql_text) s, COUNT(plan_text) p, COUNT(engine) e
        FROM events GROUP BY event_type ORDER BY n DESC
    """).fetchall():
        print(f"{str(row[0]):<14}{row[1]:>10}{row[2]:>10}{row[3]:>11}{row[4]:>12}")

    print("\n== engine distribution ==")
    for row in con.execute("SELECT engine, COUNT(*) FROM events GROUP BY engine ORDER BY 2 DESC").fetchall():
        print(f"  engine={row[0]}  count={row[1]}")

    print("\n== time range (whole archive) ==")
    print("  ", con.execute("SELECT MIN(ts), MAX(ts) FROM events").fetchone())

    print("\n== DBMSSQL/DBPOSTGRS detail ==")
    for et in ("DBMSSQL", "DBPOSTGRS"):
        r = con.execute(
            "SELECT COUNT(*) n_total, COUNT(sql_text) n_sql, COUNT(plan_text) n_plan, "
            "COUNT(DISTINCT sql_text_hash) n_uniq, MIN(ts), MAX(ts) "
            "FROM events WHERE event_type = ?", [et]
        ).fetchone()
        print(f"  {et}: total={r[0]} with_sql={r[1]} with_plan={r[2]} uniq_hash={r[3]} first={r[4]} last={r[5]}")

    print("\n== locks / deadlocks ==")
    print("  TLOCK total:", con.execute("SELECT COUNT(*) FROM events WHERE event_type='TLOCK'").fetchone()[0])
    print("  TLOCK with WaitConnections:", con.execute(
        "SELECT COUNT(*) FROM events WHERE event_type='TLOCK' AND extra LIKE '%WaitConnections%'").fetchone()[0])
    print("  TTIMEOUT total:", con.execute("SELECT COUNT(*) FROM events WHERE event_type='TTIMEOUT'").fetchone()[0])
    print("  TDEADLOCK total:", con.execute("SELECT COUNT(*) FROM events WHERE event_type='TDEADLOCK'").fetchone()[0])

    print("\n== duration sanity (top events are which types?) ==")
    print(f"  {'type':<14}{'n_in_top200':>12}")
    for row in con.execute("""
        SELECT event_type, COUNT(*) n FROM (
            SELECT event_type FROM events WHERE duration_us IS NOT NULL
            ORDER BY duration_us DESC LIMIT 200
        ) GROUP BY event_type ORDER BY n DESC
    """).fetchall():
        print(f"  {str(row[0]):<14}{row[1]:>12}")

    print("\n== sql_antipatterns parse diagnostics (classification only — no SQL printed) ==")
    try:
        import re as _re
        from collections import Counter

        from optimyzer_backend.rpc import sql_antipatterns_rpc as A

        sqls = [
            r[0]
            for r in con.execute(
                "SELECT ARG_MAX(sql_text, duration_us) FROM events "
                "WHERE event_type='DBMSSQL' AND sql_text IS NOT NULL "
                "GROUP BY sql_text_hash ORDER BY SUM(duration_us) DESC LIMIT 50"
            ).fetchall()
            if r[0]
        ]
        verb_pe: Counter = Counter()
        verb_ok: Counter = Counter()
        feats: Counter = Counter()
        n_pe = 0
        for s in sqls:
            res = A.detect_rpc(s, "mssql")
            fs = res.get("findings", []) if res.get("ok") else []
            is_pe = any(f.get("code") == "parse_error" for f in fs)
            body = s.strip()
            # снимем ведущий sp_executesql wrap-остаток если есть
            m = _re.search(r"[A-Za-z_#]+", body)
            verb = (m.group(0).upper() if m else "?")
            if is_pe:
                n_pe += 1
                verb_pe[verb] += 1
                if "#" in body:
                    feats["#temp"] += 1
                if _re.search(r"\bINTO\b", body, _re.I):
                    feats["INTO"] += 1
                if _re.search(r"\bCAST\b", body, _re.I):
                    feats["CAST"] += 1
                if _re.search(r"\bWITH\s*\(", body, _re.I):
                    feats["WITH(hint)"] += 1
                if _re.search(r"@P\d+", body):
                    feats["@Pn-param"] += 1
                if _re.search(r"\bUPDATE\b|\bINSERT\b|\bDELETE\b", body, _re.I):
                    feats["DML"] += 1
            else:
                verb_ok[verb] += 1
        print(f"  sampled={len(sqls)}  parse_error={n_pe}")
        print(f"  parse_error first-token : {dict(verb_pe)}")
        print(f"  parse_error features    : {dict(feats)}")
        print(f"  parsed-ok first-token   : {dict(verb_ok)}")
    except Exception as ex:  # noqa: BLE001
        print("  antipattern diag failed:", type(ex).__name__, ex)

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
