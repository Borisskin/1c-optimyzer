"""Safety net: проверка что файл выглядит как TJ-лог (имя — не гарантия).

Используется в дополнение к regex по имени файла на случай нестандартных
файлов (`*.log` от других систем, копии в backup-папках и т.д.).
"""

from __future__ import annotations

import re
from pathlib import Path

# Префикс TJ-события: MM:SS.UUUUUU-<duration>
# UUUUUU обычно 6 цифр, но в реальных логах встречается 1-6 (см. discovery sample 1cv8s).
TJ_EVENT_PREFIX_RE = re.compile(rb"^\d{1,2}:\d{2}\.\d{1,6}-")

UTF8_BOM = b"\xef\xbb\xbf"


def is_tj_log_file(path: Path, max_check_bytes: int = 4096) -> bool:
    """Возвращает True, если первая непустая строка matches TJ event prefix."""
    try:
        with path.open("rb") as f:
            chunk = f.read(max_check_bytes)
    except OSError:
        return False

    if chunk.startswith(UTF8_BOM):
        chunk = chunk[len(UTF8_BOM) :]

    for line in chunk.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return bool(TJ_EVENT_PREFIX_RE.match(stripped))

    return False
