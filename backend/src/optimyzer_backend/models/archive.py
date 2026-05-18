"""Модели для загрузки и парсинга архива."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ArchiveStatus(str, Enum):
    LOADING = "loading"
    EXTRACTING = "extracting"
    PARSING = "parsing"
    READY = "ready"
    ERROR = "error"


class ArchiveInfo(BaseModel):
    archive_id: str
    path: str
    size_bytes: int
    file_count: int
    status: ArchiveStatus
    progress: float = 0.0
    events_parsed: int = 0
    errors: list[str] = []
    loaded_at: datetime | None = None
    parsing_time_sec: float | None = None
    extra: dict[str, Any] = {}
