"""Извлечение process_role + pid из имени родительской папки лог-файла."""

from __future__ import annotations

import re
from typing import cast

from .source import ProcessRole

# Case-insensitive — discovery 2026-05-18 показал mixed-case (1CV8C_12044 рядом с 1cv8c_23100).
PROCESS_ROLE_RE = re.compile(
    r"^(1cv8c|1cv8s|1cv8|ragent|rmngr|rphost)_(\d+)$",
    re.IGNORECASE,
)


def extract_process_role(folder_name: str) -> tuple[ProcessRole, int | None]:
    """Парсит имя папки вида ``rphost_28220`` → ``("rphost", 28220)``.

    Регистр любой; результат — всегда lowercase. Если не матчит — ``("unknown", None)``.
    """
    match = PROCESS_ROLE_RE.match(folder_name.strip())
    if not match:
        return ("unknown", None)
    role = match.group(1).lower()
    try:
        pid = int(match.group(2))
    except ValueError:
        return ("unknown", None)
    return (cast(ProcessRole, role), pid)
