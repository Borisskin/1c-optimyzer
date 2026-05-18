"""Распаковка zip-архива ТЖ в temp-директорию."""

from __future__ import annotations

import os
import tempfile
import uuid
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedFile:
    relative_path: str
    abs_path: Path
    size_bytes: int


@dataclass
class ExtractResult:
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
    """Распаковать zip с ТЖ. Возвращает список извлечённых файлов и id архива."""
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
