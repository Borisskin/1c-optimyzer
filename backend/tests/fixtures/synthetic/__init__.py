"""Synthetic TJ log generator (Sprint 1, Phase K).

Используется в unit-тестах, где не нужна 12 GiB зависимость от
``OPTIMYZER_REAL_FOLDER_PATH`` корпуса.
"""

from .generate_tj_logs import build_folder, generate_event

__all__ = ["build_folder", "generate_event"]
