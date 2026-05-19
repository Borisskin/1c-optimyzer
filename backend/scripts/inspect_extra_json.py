"""Phase 0 discovery — реальная схема `extra` JSON в production TJ архивах.

Скрипт читает уже загруженный DuckDB-архив (per-archive .duckdb file) и
собирает:

  1. Распределение events по event_type (count, %)
  2. Для top-N event_types — какие поля встречаются в `extra` JSON,
     частота каждого поля, 2-3 примера значений
  3. Для TDEADLOCK / TLOCK / EXCP — полная schema всех ключей с типами
     и frequency, плюс распределение по Exception type / Descr / lock mode

Output:
  - docs/EXTRA_JSON_FIELD_STUDY.md (markdown отчёт для архитектора)
  - stdout summary (event distribution, top fields per type)

Запуск (из 1c-optimyzer/):
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\inspect_extra_json.py \\
        --db "%APPDATA%\\1c-optimyzer\\duckdb\\<archive>.duckdb"

Опции:
    --db PATH                путь к .duckdb (обязательно если не задано в env)
    --top-types N            сколько event_types раскрывать детально (default: 10)
    --sample-values N        сколько примеров значений на каждое поле (default: 3)
    --max-events-per-type N  лимит events для sampling extra JSON (default: 50000)
    --out PATH               output markdown (default: docs/EXTRA_JSON_FIELD_STUDY.md)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb не установлен. Запусти через backend/.venv/Scripts/python.exe", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", help="Путь к .duckdb архиву")
    ap.add_argument("--top-types", type=int, default=10)
    ap.add_argument("--sample-values", type=int, default=3)
    ap.add_argument("--max-events-per-type", type=int, default=50_000)
    ap.add_argument("--out", default=str(REPO_ROOT / "docs" / "EXTRA_JSON_FIELD_STUDY.md"))
    return ap.parse_args()


def resolve_db_path(arg_db: str | None) -> Path:
    if arg_db:
        p = Path(arg_db).expanduser()
        if not p.is_file():
            raise SystemExit(f"DB not found: {p}")
        return p
    appdata = os.environ.get("APPDATA")
    if appdata:
        ddir = Path(appdata) / "1c-optimyzer" / "duckdb"
        if ddir.is_dir():
            files = sorted(
                ddir.glob("*.duckdb"),
                key=lambda f: f.stat().st_size,
                reverse=True,
            )
            if files:
                print(f"Auto-detected largest .duckdb: {files[0]} ({files[0].stat().st_size / 1024**2:.1f} MB)")
                return files[0]
    raise SystemExit("Передай --db или установи APPDATA с .duckdb архивами")


def fetch_event_distribution(conn: duckdb.DuckDBPyConnection) -> list[tuple[str, int, float]]:
    rows = conn.execute(
        """
        SELECT event_type, COUNT(*) AS cnt
        FROM events
        GROUP BY event_type
        ORDER BY cnt DESC
        """
    ).fetchall()
    total = sum(r[1] for r in rows) or 1
    return [(et, cnt, 100.0 * cnt / total) for et, cnt in rows]


def fetch_extra_samples(
    conn: duckdb.DuckDBPyConnection,
    event_type: str,
    limit: int,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT extra::VARCHAR
        FROM events
        WHERE event_type = ? AND extra IS NOT NULL
        LIMIT ?
        """,
        [event_type, limit],
    ).fetchall()
    return [r[0] for r in rows if r[0]]


def analyse_extra(
    samples: list[str],
    max_value_examples: int = 3,
) -> dict[str, dict]:
    """Aggregate JSON keys → {count, types, sample_values}."""
    fields: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "types": Counter(), "samples": []}
    )
    parsed_total = 0
    for raw in samples:
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        parsed_total += 1
        for k, v in obj.items():
            f = fields[k]
            f["count"] += 1
            f["types"][type(v).__name__] += 1
            if len(f["samples"]) < max_value_examples:
                preview = str(v)
                if len(preview) > 200:
                    preview = preview[:200] + "…"
                if preview not in f["samples"]:
                    f["samples"].append(preview)
    return {"parsed_total": parsed_total, "fields": dict(fields)}


def fetch_context_distribution(
    conn: duckdb.DuckDBPyConnection,
    event_types: tuple[str, ...] = ("CALL", "SCALL"),
    limit: int = 20,
) -> list[tuple[str, int]]:
    """Топ raw context'ов для CALL/SCALL — фундамент для Phase A normalization."""
    placeholders = ",".join("?" * len(event_types))
    rows = conn.execute(
        f"""
        SELECT context, COUNT(*) AS cnt
        FROM events
        WHERE event_type IN ({placeholders}) AND context IS NOT NULL AND context <> ''
        GROUP BY context
        ORDER BY cnt DESC
        LIMIT ?
        """,
        [*event_types, limit],
    ).fetchall()
    return [(c, n) for c, n in rows]


def fetch_excp_patterns(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> list[tuple[str, int]]:
    """Распределение Descr (первые 120 символов) для EXCP events."""
    rows = conn.execute(
        """
        SELECT substr(coalesce(json_extract_string(extra, '$.Descr'), ''), 1, 120) AS descr,
               COUNT(*) AS cnt
        FROM events
        WHERE event_type = 'EXCP' AND extra IS NOT NULL
        GROUP BY descr
        ORDER BY cnt DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    return [(d or "(empty)", n) for d, n in rows]


def render_markdown(
    db_path: Path,
    event_dist: list[tuple[str, int, float]],
    extra_by_type: dict[str, dict],
    top_contexts: list[tuple[str, int]],
    excp_patterns: list[tuple[str, int]],
    args: argparse.Namespace,
) -> str:
    lines: list[str] = []
    add = lines.append

    add("# Extra JSON Field Study — реальный архив (Sprint 3 Phase 0)")
    add("")
    add(f"> **Источник:** `{db_path}`  ")
    add(f"> **Размер БД:** {db_path.stat().st_size / 1024**2:.1f} MB  ")
    add(f"> **Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    add(f"> **Sample size per type:** до {args.max_events_per_type:,} events  ")
    add("")
    add("Этот документ — fact-based input для Sprint 3 Phase C (Document Anatomy) и Phase D ")
    add("(Deadlock Anatomy). Все поля и их частоты получены из реального production-архива ")
    add("Сергея, не гипотетически.")
    add("")

    # 1. Event type distribution
    add("## 1. Распределение событий по event_type")
    add("")
    add("| event_type | count | % |")
    add("|---|---:|---:|")
    total = sum(c for _, c, _ in event_dist)
    for et, cnt, pct in event_dist:
        add(f"| `{et}` | {cnt:,} | {pct:.2f}% |")
    add(f"| **TOTAL** | **{total:,}** | **100%** |")
    add("")

    # 2. Per-type extra fields
    add("## 2. Поля `extra` JSON по типу события")
    add("")
    add("Колонки таблицы:")
    add("- **field** — ключ внутри `extra` JSON")
    add("- **freq** — в скольких % sampled events этот ключ присутствует")
    add("- **types** — какие Python-типы значений встречаются")
    add("- **examples** — 1-3 примера значений (обрезано до 200 символов)")
    add("")

    for et, _, _ in event_dist[: args.top_types]:
        if et not in extra_by_type:
            continue
        info = extra_by_type[et]
        parsed = info["parsed_total"]
        fields = info["fields"]
        if parsed == 0 or not fields:
            add(f"### `{et}`")
            add("")
            add("_extra JSON отсутствует или пустой для этого типа._")
            add("")
            continue
        add(f"### `{et}` — sampled {parsed:,} events, {len(fields)} unique fields")
        add("")
        add("| field | freq | types | examples |")
        add("|---|---:|---|---|")
        sorted_fields = sorted(fields.items(), key=lambda x: x[1]["count"], reverse=True)
        for name, finfo in sorted_fields:
            freq = 100.0 * finfo["count"] / parsed
            types_str = ", ".join(f"{t}×{n}" for t, n in finfo["types"].most_common())
            examples_md = "<br>".join(
                f"`{escape_md(s)}`" for s in finfo["samples"]
            ) or "—"
            add(f"| `{name}` | {freq:.1f}% | {types_str} | {examples_md} |")
        add("")

    # 3. Top contexts (raw) for CALL/SCALL — input for normalization
    add("## 3. Top raw `context` значений (CALL / SCALL)")
    add("")
    add("Эти строки — input для Phase A normalization. Цель — извлечь `Тип.Имя.Сущность`, отбросив `: line : statement`.")
    add("")
    add("| count | raw context (первые 200 символов) |")
    add("|---:|---|")
    for ctx, cnt in top_contexts:
        preview = ctx[:200] + ("…" if len(ctx) > 200 else "")
        add(f"| {cnt:,} | `{escape_md(preview)}` |")
    add("")

    # 4. EXCP patterns
    add("## 4. Распределение `Descr` для EXCP")
    add("")
    add("| count | Descr (первые 120 символов) |")
    add("|---:|---|")
    for descr, cnt in excp_patterns:
        add(f"| {cnt:,} | `{escape_md(descr)}` |")
    add("")

    # 5. Summary
    add("## 5. Implications для Sprint 3")
    add("")

    tdeadlock = extra_by_type.get("TDEADLOCK")
    if tdeadlock and tdeadlock["parsed_total"]:
        add(f"- **TDEADLOCK:** {tdeadlock['parsed_total']:,} sampled, {len(tdeadlock['fields'])} полей в `extra`.")
        top5 = sorted(tdeadlock["fields"].items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        add(f"  Топ-5 полей: {', '.join(f'`{n}`' for n, _ in top5)}.")
        add("  Используем эти поля в Phase D Deadlock Anatomy.")
    else:
        add("- **TDEADLOCK:** в архиве не найдено или extra пустой → Phase D нужны дополнительные архивы")

    tlock = extra_by_type.get("TLOCK")
    if tlock and tlock["parsed_total"]:
        add(f"- **TLOCK:** {tlock['parsed_total']:,} sampled, {len(tlock['fields'])} полей.")
        top5 = sorted(tlock["fields"].items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        add(f"  Топ-5 полей: {', '.join(f'`{n}`' for n, _ in top5)}.")
    else:
        add("- **TLOCK:** не найдено или extra пустой")

    excp = extra_by_type.get("EXCP")
    if excp and excp["parsed_total"]:
        add(f"- **EXCP:** {excp['parsed_total']:,} sampled, {len(excp['fields'])} полей.")
    else:
        add("- **EXCP:** не найдено или extra пустой")

    add("")
    add("Полные таблицы выше → используем при designe explainer rules (Phase E).")
    add("")
    add("---")
    add("")
    add(f"_Сгенерировано `backend/scripts/inspect_extra_json.py` {datetime.now().strftime('%Y-%m-%d %H:%M')}_")

    return "\n".join(lines) + "\n"


def escape_md(s: str) -> str:
    return s.replace("\\", "\\\\").replace("`", "\\`").replace("|", "\\|").replace("\n", " ").replace("\r", "")


def main() -> int:
    args = parse_args()
    db_path = resolve_db_path(args.db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening: {db_path}")
    conn = duckdb.connect(str(db_path), read_only=True)

    print("Fetching event distribution…")
    event_dist = fetch_event_distribution(conn)
    print(f"  {len(event_dist)} distinct event_types, top: {event_dist[0] if event_dist else 'none'}")

    print(f"Sampling extra JSON for top-{args.top_types} types (max {args.max_events_per_type:,} per type)…")
    extra_by_type: dict[str, dict] = {}
    for et, cnt, _ in event_dist[: args.top_types]:
        samples = fetch_extra_samples(conn, et, args.max_events_per_type)
        info = analyse_extra(samples, args.sample_values)
        extra_by_type[et] = info
        print(f"  {et}: total {cnt:,}, sampled {len(samples):,}, parsed {info['parsed_total']:,}, fields {len(info['fields'])}")

    print("Fetching top raw contexts (CALL/SCALL)…")
    top_contexts = fetch_context_distribution(conn)

    print("Fetching EXCP Descr distribution…")
    excp_patterns = fetch_excp_patterns(conn)

    conn.close()

    print(f"Rendering markdown -> {out_path}")
    md = render_markdown(db_path, event_dist, extra_by_type, top_contexts, excp_patterns, args)
    out_path.write_text(md, encoding="utf-8")
    print(f"OK: {out_path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
