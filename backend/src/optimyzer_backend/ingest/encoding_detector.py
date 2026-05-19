"""Подбор кодировки лог-файла ТЖ.

Изменение vs Sprint 1: раньше брали первую кодировку которая не падает с
UnicodeDecodeError. Проблема: для файлов в cp1251 с русским текстом
plain `utf-8` тоже **успешно** декодируется в некоторых случаях
(когда байты случайно попадают в valid utf-8 sequences) → mojibake.

Новая логика:
  1. BOM check (utf-8-sig / utf-16-le / utf-16-be / utf-32).
  2. Среди кандидатов которые декодируются без ошибок —
     предпочитаем тот, где в результате найдена кириллица. Это и есть
     признак «правильной» кодировки для русского ТЖ.
  3. Если кириллицы нет нигде — берём первого кандидата (это норма
     для логов без context — там только ASCII).
"""

from __future__ import annotations

import re
from pathlib import Path

ENCODINGS_TO_TRY: tuple[str, ...] = (
    "utf-8",  # самое распространённое
    "cp1251",  # legacy Windows на русских стендах
    "cp866",  # совсем legacy DOS
    "utf-16-le",  # бывает на некоторых конфигурациях
    "utf-16-be",
)

_CYRILLIC_RE = re.compile(r"[А-яЁё]")


def detect_encoding(path: Path, sample_size: int = 65536) -> str:
    """Возвращает кодировку для чтения файла.

    Алгоритм:
    1. Если есть BOM — точно знаем кодировку (возвращаем сразу).
    2. Пробуем все кандидаты; собираем те которые декодируются без error.
    3. Если есть с кириллицей — возвращаем первый такой.
    4. Иначе — первый успешно-декодируемый.
    5. Если все упали — `utf-8` (читатель должен использовать errors="replace").
    """
    try:
        with path.open("rb") as f:
            sample = f.read(sample_size)
    except OSError:
        return "utf-8"

    # 1. BOM detection — самый надёжный сигнал.
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample.startswith(b"\xff\xfe\x00\x00"):
        return "utf-32-le"
    if sample.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32-be"
    if sample.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if sample.startswith(b"\xfe\xff"):
        return "utf-16-be"

    # 2-4. Пробуем кандидаты, оцениваем по наличию кириллицы.
    cyrillic_match: str | None = None
    first_ok: str | None = None
    for enc in ENCODINGS_TO_TRY:
        try:
            decoded = sample.decode(enc)
        except UnicodeDecodeError:
            continue
        if first_ok is None:
            first_ok = enc
        if _CYRILLIC_RE.search(decoded):
            # Дополнительная проверка: декодированный текст не должен содержать
            # подозрительных control chars в большом количестве (признак mojibake
            # для utf-16 → single-byte decoding).
            if _looks_sane(decoded):
                cyrillic_match = enc
                break

    return cyrillic_match or first_ok or "utf-8"


def _looks_sane(text: str) -> bool:
    """Проверка что декодированный текст похож на normal log content.

    Реальный TJ-event начинается с `<min>:<sec>.<usec>-<duration>,<TYPE>,...`
    и состоит в основном из printable ASCII + кириллицы. Если >20% символов
    sample — это control characters (не \\n/\\r/\\t), это скорее всего
    mojibake от неверной кодировки.
    """
    if not text:
        return False
    sample = text[:2000]
    bad = sum(
        1
        for ch in sample
        if ord(ch) < 32 and ch not in ("\n", "\r", "\t")
    )
    return bad / len(sample) < 0.2
