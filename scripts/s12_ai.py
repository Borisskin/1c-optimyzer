#!/usr/bin/env python
"""S12 AI-прогон через cloud-сервер (:8001) на боевых данных.

Прогоняет /v1/ai/explain_plan на реальных планах из ТЖ + /v1/ai/generate_logcfg
на описаниях проблем. Полные AI-ответы (вместе с боевым SQL/планом) пишутся в
ЛОКАЛЬНЫЙ файл .s12_ai_out/ai_review.md — НЕ коммитить (приватные данные).
В stdout — только метрики (код, counts, model), без содержимого.

Запуск: backend\\.venv\\Scripts\\python.exe scripts\\s12_ai.py  (сервер :8001 должен быть поднят)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"


def post(path: str, payload: dict, timeout: int = 95):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            return e.code, {"error": "http_error"}
    except Exception as e:  # noqa: BLE001
        return None, {"error": str(e)}


def main() -> int:
    from optimyzer_backend.rpc import handlers as H

    tj = sys.argv[1] if len(sys.argv) > 1 else r"C:\1C-TechLog"
    st = H.load_directory(tj)
    aid = st["archive_id"]
    H.wait_for_archive(aid, timeout_sec=900)
    store = H._ARCHIVES[aid]["store"]
    con = store.open()

    plans = con.execute(
        "SELECT id, sql_text, plan_text, duration_us FROM events "
        "WHERE plan_text IS NOT NULL AND plan_text <> '' "
        "ORDER BY duration_us DESC NULLS LAST LIMIT 5"
    ).fetchall()

    outdir = Path(r"D:\1C-Optimyzer\.s12_ai_out")
    outdir.mkdir(exist_ok=True)
    md: list[str] = [
        "# S12 AI review (ЛОКАЛЬНО — содержит боевой SQL/планы, НЕ коммитить)\n",
        "Оценка эксперта: врёт ли AI, выдумывает ли несуществующее, верны ли советы по 1С.\n",
    ]

    print(f"[ai] explain_plan на {len(plans)} боевых планах из ТЖ")
    for i, (eid, sql, plan, dur) in enumerate(plans, 1):
        payload = {
            "sql_text": (sql or "(no sql)")[:50000],
            "plan_xml": plan[:500000],
            "plan_format": "text",
            "engine": "mssql",
        }
        code, resp = post("/v1/ai/explain_plan", payload)
        ok = code == 200
        hs = resp.get("hotspots", []) if ok else []
        rec = resp.get("recommendations", []) if ok else []
        idx = resp.get("suggested_indexes", []) if ok else []
        model = resp.get("model_used", "?") if ok else "?"
        print(
            f"  [plan {i}] code={code} ok={ok} dur_us={dur} model={model} "
            f"sev={resp.get('overall_severity') if ok else '-'} "
            f"hotspots={len(hs)} recs={len(rec)} idx={len(idx)} cached={resp.get('was_cached') if ok else '-'}"
        )
        md.append(f"\n---\n## План {i} — event_id={eid}, duration={dur} мкс\n")
        md.append(f"### SQL\n```sql\n{sql}\n```\n")
        md.append(f"### План (SHOWPLAN_TEXT)\n```\n{plan}\n```\n")
        if not ok:
            md.append(f"### AI: ОШИБКА code={code}\n```\n{json.dumps(resp, ensure_ascii=False, indent=2)}\n```\n")
            continue
        md.append(f"### AI summary\n{resp.get('summary','')}\n")
        md.append(f"overall_severity: {resp.get('overall_severity')} · model: {model}\n")
        md.append(f"\n### Hotspots ({len(hs)})\n")
        for h in hs:
            md.append(
                f"- **[{h.get('severity')}] {h.get('operator_type')}**\n"
                f"  - что: {h.get('what')}\n  - почему: {h.get('why')}\n  - делать: {h.get('what_to_do')}\n"
            )
        md.append(f"\n### Рекомендации ({len(rec)})\n")
        for r in rec:
            md.append(f"- [{r.get('impact_estimate')}] {r.get('category')}: **{r.get('title')}** — {r.get('description')}\n")
        md.append(f"\n### Предложенные индексы ({len(idx)})\n")
        for x in idx:
            md.append(
                f"- `{x.get('table')}({', '.join(x.get('columns', []))})"
                f"{' INCLUDE(' + ', '.join(x.get('include', [])) + ')' if x.get('include') else ''}` "
                f"[{x.get('impact_estimate')}]: {x.get('rationale')}\n"
            )

    print("\n[ai] generate_logcfg на описаниях проблем")
    for desc in [
        "Тормозит проведение документа Реализация товаров и услуг, длительные запросы к базе",
        "Долгое формирование отчёта по продажам, подозрение на блокировки и взаимоблокировки",
    ]:
        code, resp = post("/v1/ai/generate_logcfg", {"problem_description": desc, "dbms": "mssql"})
        ok = code == 200
        er = resp.get("events_rationale", []) if ok else []
        print(f"  [logcfg] code={code} ok={ok} model={resp.get('model_used') if ok else '-'} events={len(er)} cached={resp.get('was_cached') if ok else '-'}")
        md.append(f"\n---\n## logcfg AI: «{desc}»\n")
        if not ok:
            md.append(f"ОШИБКА code={code}: {json.dumps(resp, ensure_ascii=False)}\n")
            continue
        cfg = resp.get("config", {})
        md.append(f"explanation: {resp.get('explanation')}\n")
        md.append(f"capture_plans: {cfg.get('capture_plans')} · history_hours: {cfg.get('history_hours')}\n")
        md.append(f"events: `{json.dumps(cfg.get('events', {}), ensure_ascii=False)}`\n")
        for e in er:
            md.append(f"- {e.get('event')} @ {e.get('threshold')}: {e.get('why')}\n")

    review = outdir / "ai_review.md"
    review.write_text("".join(md), encoding="utf-8")
    print(f"\n[ai] полный обзор записан: {review}  (ЛОКАЛЬНО, не коммитится)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
