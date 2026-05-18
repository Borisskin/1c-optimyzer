"""Discovery-скрипт для обследования реальной папки с логами ТЖ 1С.

Запуск (из корня репозитория):
    backend\.venv\Scripts\python.exe backend\scripts\inspect_logs.py <path-to-logs>

Скрипт собирает metadata без парсинга событий и пишет отчёт в
docs/LOGS_INSPECTION.md для архитектора Sprint 1.
"""

from __future__ import annotations

import argparse
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Кодировки, которые имеет смысл пробовать для логов ТЖ.
ENCODING_CANDIDATES = ["utf-8-sig", "utf-8", "cp1251", "cp866", "utf-16-le", "utf-16-be"]

CYRILLIC_RE = re.compile(r"[А-яЁё]")


def detect_encoding(sample: bytes) -> tuple[str, str]:
    """Подбирает первую кодировку, в которой sample декодируется без ошибок.

    Возвращает (encoding, note). note описывает, что повлияло на выбор
    (наличие BOM, наличие кириллицы).
    """
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", "BOM utf-8 detected"
    if sample.startswith(b"\xff\xfe"):
        return "utf-16-le", "BOM utf-16-le detected"
    if sample.startswith(b"\xfe\xff"):
        return "utf-16-be", "BOM utf-16-be detected"

    for enc in ENCODING_CANDIDATES:
        try:
            decoded = sample.decode(enc)
        except UnicodeDecodeError:
            continue
        if CYRILLIC_RE.search(decoded):
            return enc, "decoded + cyrillic present"
        # Запоминаем первый успешно декодированный вариант.
        return enc, "decoded, no cyrillic in sample"
    return "unknown", "all candidates failed"


def classify_folder_name(name: str) -> str:
    """Извлекает префикс подпапки (часть до последнего `_цифры`)."""
    match = re.match(r"^(.+)_(\d+)$", name)
    if match:
        return match.group(1).lower()
    return name.lower()


def classify_file_name(name: str) -> str:
    """Классифицирует pattern имени .log файла."""
    stem = Path(name).stem
    if re.fullmatch(r"\d{8}", stem):
        return "YYMMDDHH (8 digits)"
    if re.fullmatch(r"\d{10}", stem):
        return "YYMMDDHHMM (10 digits)"
    if re.fullmatch(r"\d{6}", stem):
        return "YYMMDD (6 digits)"
    if re.fullmatch(r"\d{12,}", stem):
        return f"long digits ({len(stem)})"
    return f"non-numeric: {stem!r}"


def parse_yymmddhh(stem: str) -> str | None:
    if not re.fullmatch(r"\d{8}", stem):
        return None
    try:
        yy = int(stem[0:2])
        mm = int(stem[2:4])
        dd = int(stem[4:6])
        hh = int(stem[6:8])
        year = 2000 + yy
        return datetime(year, mm, dd, hh).isoformat()
    except ValueError:
        return None


def collect(root: Path) -> dict:
    """Обходит дерево и собирает все нужные метаданные."""
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")

    subdirs: list[Path] = []
    files: list[Path] = []
    for p in root.rglob("*"):
        try:
            if p.is_dir():
                subdirs.append(p)
            elif p.is_file():
                files.append(p)
        except OSError:
            continue

    folder_prefixes: Counter[str] = Counter()
    folder_examples: defaultdict[str, list[str]] = defaultdict(list)
    for d in subdirs:
        rel = d.relative_to(root)
        # Берём только подпапки первого уровня для определения "ролей".
        if len(rel.parts) == 1:
            prefix = classify_folder_name(rel.parts[0])
            folder_prefixes[prefix] += 1
            if len(folder_examples[prefix]) < 5:
                folder_examples[prefix].append(rel.parts[0])

    ext_counts: Counter[str] = Counter()
    for f in files:
        ext_counts[f.suffix.lower()] += 1

    log_files = [f for f in files if f.suffix.lower() == ".log"]
    non_log_files = [f for f in files if f.suffix.lower() != ".log"]
    non_log_samples = [str(f.relative_to(root)) for f in non_log_files[:20]]

    sizes = [f.stat().st_size for f in log_files]
    size_stats = {}
    if sizes:
        size_stats = {
            "count": len(sizes),
            "total_bytes": sum(sizes),
            "total_gb": sum(sizes) / (1024**3),
            "min_bytes": min(sizes),
            "max_bytes": max(sizes),
            "median_bytes": int(statistics.median(sizes)),
            "mean_bytes": int(statistics.mean(sizes)),
        }

    file_pattern_counts: Counter[str] = Counter()
    file_pattern_examples: defaultdict[str, list[str]] = defaultdict(list)
    files_by_subdir: defaultdict[str, list[Path]] = defaultdict(list)
    for f in log_files:
        rel = f.relative_to(root)
        sub = rel.parts[0] if len(rel.parts) > 1 else "<root>"
        files_by_subdir[sub].append(f)
        pattern = classify_file_name(f.name)
        file_pattern_counts[pattern] += 1
        if len(file_pattern_examples[pattern]) < 8:
            file_pattern_examples[pattern].append(str(rel))

    # Выбор 5 случайных файлов из РАЗНЫХ подпапок (если возможно).
    sampled_paths: list[Path] = []
    subdirs_keys = list(files_by_subdir.keys())
    random.seed(42)
    random.shuffle(subdirs_keys)
    for sub in subdirs_keys:
        if len(sampled_paths) >= 5:
            break
        chosen = random.choice(files_by_subdir[sub])
        sampled_paths.append(chosen)
    # Если подпапок меньше 5 — добиваем из всех логов.
    if len(sampled_paths) < 5 and log_files:
        remaining = [f for f in log_files if f not in sampled_paths]
        random.shuffle(remaining)
        sampled_paths.extend(remaining[: 5 - len(sampled_paths)])

    samples = []
    for f in sampled_paths:
        try:
            with open(f, "rb") as fh:
                raw = fh.read(4096)
        except OSError as e:
            samples.append({"path": str(f.relative_to(root)), "error": str(e)})
            continue
        encoding, note = detect_encoding(raw)
        decoded = None
        first_lines: list[str] = []
        if encoding != "unknown":
            try:
                decoded = raw.decode(encoding, errors="replace")
            except (LookupError, UnicodeDecodeError):
                decoded = None
        if decoded:
            for line in decoded.splitlines():
                if line.strip():
                    first_lines.append(line)
                if len(first_lines) >= 3:
                    break
        samples.append(
            {
                "path": str(f.relative_to(root)),
                "size_bytes": f.stat().st_size,
                "encoding": encoding,
                "encoding_note": note,
                "first_lines": first_lines,
            }
        )

    # Tree first 2 levels.
    tree_lines: list[str] = []
    top_dirs = sorted([d for d in root.iterdir() if d.is_dir()])
    top_files = sorted([f for f in root.iterdir() if f.is_file()])
    tree_lines.append(f"{root}/")
    for d in top_dirs:
        tree_lines.append(f"├── {d.name}/")
        try:
            children = sorted(d.iterdir())
        except OSError:
            children = []
        for i, c in enumerate(children[:10]):
            prefix = "└──" if i == len(children[:10]) - 1 else "├──"
            suffix = "/" if c.is_dir() else ""
            tree_lines.append(f"│   {prefix} {c.name}{suffix}")
        if len(children) > 10:
            tree_lines.append(f"│   └── ... ({len(children) - 10} more)")
    for f in top_files:
        tree_lines.append(f"├── {f.name}")

    # Date range from YYMMDDHH stems.
    parsed_dates: list[str] = []
    for f in log_files:
        d = parse_yymmddhh(Path(f.name).stem)
        if d:
            parsed_dates.append(d)
    parsed_dates.sort()

    return {
        "root": str(root),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "tree": tree_lines,
        "folder_prefixes": dict(folder_prefixes),
        "folder_examples": {k: v for k, v in folder_examples.items()},
        "ext_counts": dict(ext_counts),
        "non_log_count": len(non_log_files),
        "non_log_samples": non_log_samples,
        "log_size_stats": size_stats,
        "file_patterns": dict(file_pattern_counts),
        "file_pattern_examples": {k: v for k, v in file_pattern_examples.items()},
        "samples": samples,
        "date_range": {
            "min": parsed_dates[0] if parsed_dates else None,
            "max": parsed_dates[-1] if parsed_dates else None,
            "parsed_count": len(parsed_dates),
        },
    }


def render_markdown(data: dict) -> str:
    fmt_bytes = lambda n: f"{n:,} bytes ({n / (1024**2):.2f} MiB)" if n is not None else "—"
    out: list[str] = []
    out.append("# Logs Inspection Report")
    out.append("")
    out.append(f"> Discovery-отчёт по реальной папке логов 1С для архитектора Sprint 1.")
    out.append(f"> Сгенерирован скриптом [`backend/scripts/inspect_logs.py`](../backend/scripts/inspect_logs.py).")
    out.append("")
    out.append(f"**Root:** `{data['root']}`")
    out.append(f"**Scanned at (UTC):** `{data['scanned_at']}`")
    out.append("")
    out.append("---")
    out.append("")

    out.append("## 1. Структура папок (top-2 levels)")
    out.append("")
    out.append("```")
    out.extend(data["tree"])
    out.append("```")
    out.append("")

    out.append("## 2. Patterns подпапок (первый уровень)")
    out.append("")
    out.append("| Префикс | Кол-во | Примеры |")
    out.append("|---|---:|---|")
    for prefix, count in sorted(data["folder_prefixes"].items(), key=lambda x: -x[1]):
        examples = ", ".join(f"`{e}`" for e in data["folder_examples"].get(prefix, []))
        out.append(f"| `{prefix}` | {count} | {examples} |")
    out.append("")

    out.append("## 3. Patterns имён `.log` файлов")
    out.append("")
    out.append("| Pattern | Кол-во | Примеры |")
    out.append("|---|---:|---|")
    for pattern, count in sorted(data["file_patterns"].items(), key=lambda x: -x[1]):
        examples = data["file_pattern_examples"].get(pattern, [])
        examples_str = "<br>".join(f"`{e}`" for e in examples)
        out.append(f"| {pattern} | {count} | {examples_str} |")
    out.append("")
    dr = data["date_range"]
    if dr["min"]:
        out.append(f"**Date range** (из имён YYMMDDHH): `{dr['min']}` → `{dr['max']}` ({dr['parsed_count']} файлов с парсимыми именами).")
        out.append("")

    out.append("## 4. Распределение размеров `.log` файлов")
    out.append("")
    s = data["log_size_stats"]
    if s:
        out.append(f"- **Files total:** {s['count']}")
        out.append(f"- **Total:** {fmt_bytes(s['total_bytes'])} ({s['total_gb']:.2f} GiB)")
        out.append(f"- **Min:** {fmt_bytes(s['min_bytes'])}")
        out.append(f"- **Max:** {fmt_bytes(s['max_bytes'])}")
        out.append(f"- **Median:** {fmt_bytes(s['median_bytes'])}")
        out.append(f"- **Mean:** {fmt_bytes(s['mean_bytes'])}")
    else:
        out.append("_No .log files found._")
    out.append("")

    out.append("## 5. Sample первых строк (фактический формат TJ event)")
    out.append("")
    for i, sample in enumerate(data["samples"], 1):
        out.append(f"### 5.{i}. `{sample['path']}`")
        if "error" in sample:
            out.append(f"_Read error: {sample['error']}_")
            out.append("")
            continue
        out.append(f"- **Size:** {fmt_bytes(sample['size_bytes'])}")
        out.append(f"- **Encoding:** `{sample['encoding']}` _(detection: {sample['encoding_note']})_")
        out.append("")
        out.append("```")
        for line in sample.get("first_lines", []):
            out.append(line)
        out.append("```")
        out.append("")

    out.append("## 6. Encoding по sample-файлам (сводка)")
    out.append("")
    enc_counter: Counter[str] = Counter()
    for sample in data["samples"]:
        enc_counter[sample.get("encoding", "unknown")] += 1
    out.append("| Encoding | Кол-во sample-файлов |")
    out.append("|---|---:|")
    for enc, n in enc_counter.most_common():
        out.append(f"| `{enc}` | {n} |")
    out.append("")

    out.append("## 7. Не-`.log` файлы")
    out.append("")
    out.append("| Extension | Count |")
    out.append("|---|---:|")
    for ext, n in sorted(data["ext_counts"].items(), key=lambda x: -x[1]):
        out.append(f"| `{ext or '(no ext)'}` | {n} |")
    out.append("")
    if data["non_log_samples"]:
        out.append(f"**Sample non-`.log` paths (до 20):**")
        out.append("")
        for p in data["non_log_samples"]:
            out.append(f"- `{p}`")
        out.append("")
    else:
        out.append("_Не-`.log` файлы не обнаружены._")
        out.append("")

    out.append("---")
    out.append("")
    out.append("## Recommendations для Sprint 1 (на основе фактов)")
    out.append("")
    out.append("Архитектор Opus интерпретирует фактические данные выше и финализирует Sprint 1 promt.")
    out.append("Этот отчёт — input, не decision.")
    out.append("")

    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Путь к корневой папке с логами 1С")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Куда положить отчёт. По умолчанию docs/LOGS_INSPECTION.md относительно корня репо.",
    )
    args = parser.parse_args()

    root = Path(args.path).resolve()
    repo_root = Path(__file__).resolve().parents[2]
    output = Path(args.output).resolve() if args.output else (repo_root / "docs" / "LOGS_INSPECTION.md")
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {root} ...", file=sys.stderr)
    data = collect(root)
    md = render_markdown(data)
    output.write_text(md, encoding="utf-8")
    print(f"Report written: {output}", file=sys.stderr)
    print(f"  Files scanned: {data['log_size_stats'].get('count', 0)} .log + {data['non_log_count']} non-log", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
