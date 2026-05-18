"""Synthetic TJ log generator (Sprint 1, Phase K).

CLI:
    python -m backend.tests.fixtures.synthetic.generate_tj_logs \
        --output /tmp/synthetic-logs --size 100MB

Внутри тестов используется через ``build_folder(path, total_bytes)``.
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

ROLES: tuple[str, ...] = ("rphost", "rmngr", "ragent", "1cv8c", "1cv8s")
EVENT_TYPES: tuple[str, ...] = (
    "CALL",
    "SCALL",
    "DBMSSQL",
    "EXCP",
    "TLOCK",
    "TDEADLOCK",
    "MEM",
)


def generate_event(ts: datetime, *, rng: random.Random | None = None) -> str:
    """Возвращает одну строку синтетического TJ-события (без trailing newline)."""
    rng = rng or random
    event_type = rng.choice(EVENT_TYPES)
    duration = rng.randint(1, 50_000)
    process = rng.choice(("rphost", "rmngr", "1cv8c", "1cv8s"))
    os_thread = rng.randint(1_000, 30_000)

    base = (
        f"{ts.minute:02d}:{ts.second:02d}.{ts.microsecond:06d}-{duration},"
        f"{event_type},{rng.randint(1, 5)},"
        f"process={process},OSThread={os_thread}"
    )

    if event_type == "DBMSSQL":
        sql = "SELECT * FROM _AccumRgT5634 WHERE _Period >= ? LIMIT 100"
        base += f",Sql='{sql}',Rows={rng.randint(0, 10_000)}"
    elif event_type == "CALL":
        base += ",Context='Документ.Реализация.Модуль.ОбработкаПроведения'"
    elif event_type == "EXCP":
        base += ",Exception='SystemError',Descr='Synthetic test exception'"
    elif event_type in ("TLOCK", "TDEADLOCK"):
        base += ",Wait=0,Regions='RegisterFoo'"

    return base


def build_folder(
    output: Path,
    total_bytes: int,
    *,
    subfolder_count: int = 5,
    seed: int = 42,
    encoding: str = "utf-8-sig",
) -> Path:
    """Создаёт корневую папку с подпапками вида ``<role>_<pid>/YYMMDDHH.log``.

    Файлы пишутся UTF-8 with BOM по умолчанию (default из discovery).
    """
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    subfolders: list[Path] = []
    for _ in range(subfolder_count):
        role = rng.choice(ROLES)
        pid = rng.randint(10_000, 99_999)
        sub = output / f"{role}_{pid}"
        sub.mkdir(exist_ok=True)
        subfolders.append(sub)

    bytes_written = 0
    base_ts = datetime(2026, 5, 18, 13, 0, 0)

    open_files: dict[Path, "object"] = {}
    try:
        while bytes_written < total_bytes:
            sub = rng.choice(subfolders)
            hour_offset = rng.randint(0, 23)
            ts_base = base_ts + timedelta(hours=hour_offset)
            filename = f"{ts_base.strftime('%y%m%d%H')}.log"
            filepath = sub / filename

            fh = open_files.get(filepath)
            if fh is None:
                fh = filepath.open("a", encoding=encoding)
                open_files[filepath] = fh

            n_events = rng.randint(50, 500)
            for _ in range(n_events):
                event_ts = ts_base + timedelta(microseconds=rng.randint(0, 3_500_000_000))
                event = generate_event(event_ts, rng=rng)
                line = event + "\n"
                fh.write(line)
                bytes_written += len(line.encode("utf-8"))
                if bytes_written >= total_bytes:
                    break
    finally:
        for fh in open_files.values():
            fh.close()

    return output


def _parse_size(spec: str) -> int:
    spec = spec.strip().upper()
    units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "B": 1}
    for suffix, multiplier in units.items():
        if spec.endswith(suffix):
            try:
                return int(float(spec[: -len(suffix)]) * multiplier)
            except ValueError:
                break
    return int(spec)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Synthetic TJ log generator")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", default="10MB", help="Total bytes, e.g. 100MB, 1GB")
    parser.add_argument("--subfolders", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    total = _parse_size(args.size)
    build_folder(args.output, total, subfolder_count=args.subfolders, seed=args.seed)
    print(f"Generated ~{total:,} bytes in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
