"""Primary источник Module 1 — рекурсивный обход папки с .log файлами."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from .log_detector import is_tj_log_file
from .process_role_extractor import extract_process_role
from .source import LogFile, LogSource

# Discovery 2026-05-18: 100% файлов следуют YYMMDDHH.log.
LOG_NAME_RE = re.compile(r"^(\d{8})\.log$", re.IGNORECASE)

# Buffer size для streaming чтения — компромисс между syscalls и памятью.
# 1 MiB достаточно для high-throughput на rphost-файле (10 ГБ).
READ_BUFFER = 1024 * 1024


class FolderSource(LogSource):
    """Рекурсивный folder ingestion — primary способ загрузки в Module 1."""

    def __init__(self, root: Path):
        root = root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Папка не найдена: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Не папка: {root}")
        self.root = root

    def discover(self) -> list[LogFile]:
        """Обходит self.root рекурсивно, возвращает только TJ-логи.

        Filtering:
        - имя должно matchить ``^\\d{8}\\.log$`` (case-insensitive)
        - первая непустая строка должна matchить TJ event prefix (safety net)
        - permission errors / broken symlinks — silently skipped (graceful)

        Sort order: ascending by size, then by relative_path. Маленькие файлы
        первыми — даёт пользователю fast feedback (счётчик растёт раньше,
        чем приходит большой rphost-файл).
        """
        results: list[LogFile] = []

        for entry in self._iter_entries():
            name_match = LOG_NAME_RE.match(entry.name)
            if not name_match:
                continue

            timestamp = name_match.group(1)

            try:
                if not is_tj_log_file(entry):
                    continue
            except OSError:
                continue

            try:
                size = entry.stat().st_size
            except OSError:
                continue

            parent_name = entry.parent.name
            role, pid = extract_process_role(parent_name)

            results.append(
                LogFile(
                    path=entry,
                    relative_path=str(entry.relative_to(self.root)),
                    size_bytes=size,
                    timestamp_from_name=timestamp,
                    process_role=role,
                    process_pid=pid,
                )
            )

        results.sort(key=lambda lf: (lf.size_bytes, lf.relative_path))
        return results

    def _iter_entries(self) -> Iterator[Path]:
        """rglob с graceful skip ошибок прав / битых ссылок."""
        try:
            yield from (p for p in self.root.rglob("*") if self._is_safe_file(p))
        except OSError:
            return

    @staticmethod
    def _is_safe_file(p: Path) -> bool:
        try:
            return p.is_file()
        except OSError:
            return False

    def open(self, log_file: LogFile, encoding: str = "utf-8-sig") -> Iterator[str]:
        """Buffered streaming line iteration. errors='replace' для устойчивости."""
        with log_file.path.open("r", encoding=encoding, errors="replace", buffering=READ_BUFFER) as f:
            for line in f:
                yield line
