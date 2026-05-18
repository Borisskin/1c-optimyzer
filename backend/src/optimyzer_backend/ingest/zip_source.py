"""Legacy ZipSource — backwards compat с Sprint 0 fixtures и тестами.

Не используется в UI Module 1 (ADR-010). Сохраняется для:
- backend/tests/fixtures/synthetic-archive.zip и подобных fixtures,
- импорта от техподдержки 1С (если в будущем появится UI-вход).

Под капотом extract в temp + delegate discover() to FolderSource.
"""

from __future__ import annotations

import os
import tempfile
import uuid
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .folder_source import FolderSource
from .source import LogFile, LogSource


@dataclass
class ExtractedFile:
    """Совместимость с тестами Sprint 0, которые читают ExtractResult напрямую."""

    relative_path: str
    abs_path: Path
    size_bytes: int


@dataclass
class ExtractResult:
    """Совместимость с тестами Sprint 0."""

    archive_id: str
    extract_dir: Path
    files: list[ExtractedFile]

    @property
    def log_files(self) -> list[ExtractedFile]:
        return [f for f in self.files if f.relative_path.lower().endswith(".log")]


def temp_root() -> Path:
    root = Path(tempfile.gettempdir()) / "1c-optimyzer" / "archives"
    root.mkdir(parents=True, exist_ok=True)
    return root


def extract_archive(zip_path: str | Path, archive_id: str | None = None) -> ExtractResult:
    """Распаковывает zip с ТЖ. Совместимо с тестами Sprint 0."""
    zp = Path(zip_path)
    if not zp.exists():
        raise FileNotFoundError(zp)
    if not zipfile.is_zipfile(zp):
        raise ValueError(f"Not a valid zip: {zp}")

    aid = archive_id or uuid.uuid4().hex
    target = temp_root() / aid
    target.mkdir(parents=True, exist_ok=True)

    files: list[ExtractedFile] = []
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            safe_name = _sanitize_member(info.filename)
            if safe_name is None:
                continue
            dest = target / safe_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                while chunk := src.read(64 * 1024):
                    out.write(chunk)
            files.append(
                ExtractedFile(
                    relative_path=safe_name,
                    abs_path=dest,
                    size_bytes=info.file_size,
                )
            )

    return ExtractResult(archive_id=aid, extract_dir=target, files=files)


def iter_log_files(result: ExtractResult) -> Iterator[ExtractedFile]:
    for f in result.log_files:
        yield f


def _sanitize_member(name: str) -> str | None:
    """Защита от zip-slip — отбрасываем абсолютные пути и `..`."""
    normalized = name.replace("\\", "/").strip()
    if not normalized:
        return None
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return None
    if os.path.isabs(normalized):
        return None
    return normalized


class ZipSource(LogSource):
    """LogSource adapter поверх zip — extract → FolderSource(extract_dir).

    Используется ТОЛЬКО в тестовых fixtures и legacy RPC ``load_archive``,
    не в UI Module 1 (ADR-010).
    """

    def __init__(self, zip_path: str | Path, archive_id: str | None = None):
        self.result = extract_archive(zip_path, archive_id=archive_id)
        self._folder_source = FolderSource(self.result.extract_dir)

    @property
    def archive_id(self) -> str:
        return self.result.archive_id

    @property
    def extract_dir(self) -> Path:
        return self.result.extract_dir

    def discover(self) -> list[LogFile]:
        return self._folder_source.discover()

    def open(self, log_file: LogFile, encoding: str = "utf-8-sig") -> Iterator[str]:
        return self._folder_source.open(log_file, encoding=encoding)
