"""Legacy alias на ingest.zip_source — Sprint 0 backwards compatibility.

Старые импорты ``from optimyzer_backend.archive.extractor import extract_archive``
продолжают работать. Новый код должен импортировать из ``optimyzer_backend.ingest``.
"""

from __future__ import annotations

from optimyzer_backend.ingest.zip_source import (
    ExtractedFile,
    ExtractResult,
    extract_archive,
    iter_log_files,
    temp_root,
)

__all__ = [
    "ExtractedFile",
    "ExtractResult",
    "extract_archive",
    "iter_log_files",
    "temp_root",
]
