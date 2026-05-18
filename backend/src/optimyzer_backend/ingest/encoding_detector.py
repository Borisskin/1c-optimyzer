"""Подбор кодировки лог-файла. utf-8-sig — default по результатам discovery."""

from __future__ import annotations

from pathlib import Path

# Порядок важен: utf-8-sig первый (наш случай из discovery 2026-05-18),
# затем plain utf-8, затем legacy Windows/DOS кодировки.
ENCODINGS_TO_TRY: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1251", "cp866")


def detect_encoding(path: Path, sample_size: int = 65536) -> str:
    """Возвращает первую кодировку, в которой sample декодируется без ошибок.

    Если все кандидаты падают (повреждённый файл, что-то странное) — возвращает
    ``"utf-8"``; читатель должен использовать ``errors="replace"`` для устойчивости.
    """
    try:
        with path.open("rb") as f:
            sample = f.read(sample_size)
    except OSError:
        return "utf-8"

    for enc in ENCODINGS_TO_TRY:
        try:
            sample.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue

    return "utf-8"
