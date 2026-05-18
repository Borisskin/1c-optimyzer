"""Абстракции источников ингеста — LogFile, LogSource, IngestProgress."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ProcessRole = Literal[
    "rphost",
    "rmngr",
    "ragent",
    "1cv8c",
    "1cv8s",
    "1cv8",
    "unknown",
]

IngestPhase = Literal["discovering", "parsing", "indexing", "done", "error"]


@dataclass
class LogFile:
    """Один лог-файл с metadata, нужной для ingestion и progress reporting."""

    path: Path
    relative_path: str
    size_bytes: int
    timestamp_from_name: str  # YYMMDDHH из имени файла; "" если нестандартное имя
    process_role: ProcessRole
    process_pid: int | None


@dataclass
class IngestProgress:
    """Срез прогресса для notification frontend."""

    phase: IngestPhase
    files_done: int
    files_total: int
    bytes_done: int
    bytes_total: int
    events_inserted: int
    current_file: str | None
    error_message: str | None = None


class LogSource(ABC):
    """Базовый интерфейс источника логов."""

    @abstractmethod
    def discover(self) -> list[LogFile]:
        """Найти все лог-файлы в источнике."""

    @abstractmethod
    def open(self, log_file: LogFile, encoding: str) -> Iterator[str]:
        """Открыть лог-файл и вернуть итератор строк."""
