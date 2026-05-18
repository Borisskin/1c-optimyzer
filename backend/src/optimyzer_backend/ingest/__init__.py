"""Ingest layer — обнаружение и чтение источников логов ТЖ.

Sprint 1 entry points:
- FolderSource (primary) — рекурсивный обход папки с .log файлами.
- ZipSource (legacy) — backwards compat с тестовыми fixtures Sprint 0.
"""

from .source import IngestPhase, IngestProgress, LogFile, LogSource, ProcessRole
from .folder_source import FolderSource
from .log_detector import is_tj_log_file
from .process_role_extractor import extract_process_role
from .encoding_detector import detect_encoding
from .zip_source import ZipSource

__all__ = [
    "IngestPhase",
    "IngestProgress",
    "LogFile",
    "LogSource",
    "ProcessRole",
    "FolderSource",
    "ZipSource",
    "is_tj_log_file",
    "extract_process_role",
    "detect_encoding",
]
