"""Sprint 11 Phase E — Operation matching между двумя архивами.

Fingerprint = (operation_name, context_signature). Context_signature берётся
из первой строки `context` поля события + нормализация (убираем session IDs,
timestamps, user-specific stuff).

Two operations match если их fingerprints равны.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# Регулярки для нормализации context — runtime values которые не должны
# влиять на matching между запусками.
_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\b")
_DATE_TIME_DOT = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}\b")
_TIME_ONLY = re.compile(r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b")
_USER = re.compile(r"\bПользователь\s*=\s*[\w.\-\s]+?(?=[,;]|$)")
_SESSION = re.compile(r"\bСеанс\s*=\s*\d+\b")
_CONNECTION = re.compile(r"\bСоединение\s*=\s*\d+\b")
_UUID = re.compile(
    r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
    re.IGNORECASE,
)
_DOC_NUMBER = re.compile(r"№\s*[\w-]+")
_NUMERIC_ID = re.compile(r"\bId=\d+\b")


@dataclass
class OperationFingerprint:
    """Stable identifier для operation matching."""

    name: str  # operation_name из context_normalized (например "Документ.Реализация.Записать")
    context_signature: str  # first line of context, normalized

    def signature(self) -> str:
        return f"{self.name}|{self.context_signature}"


@dataclass
class OperationData:
    """Сводка по одной операции в одном архиве."""

    name: str
    context: str  # raw context (first line)
    samples_count: int
    p50_duration_ms: float
    p95_duration_ms: float
    fingerprint: Optional[OperationFingerprint] = None


@dataclass
class OperationMatch:
    """Результат matching одной операции между двумя архивами."""

    match_type: str  # "matched" | "new" | "disappeared"
    baseline: Optional[OperationData] = None
    current: Optional[OperationData] = None
    fingerprint: OperationFingerprint = field(
        default_factory=lambda: OperationFingerprint(name="", context_signature="")
    )


def compute_fingerprint(operation_name: str, context: str) -> OperationFingerprint:
    """Compute stable fingerprint для operation matching."""
    name = (operation_name or "").strip()

    # Первая строка context (если есть)
    first_line = ""
    if context:
        first_line = context.split("\n", 1)[0]
        first_line = first_line.split("\\n", 1)[0]  # also handle \\n escape

    # Нормализация — убираем runtime-specific
    normalized = first_line
    normalized = _TIMESTAMP.sub("[TS]", normalized)
    normalized = _DATE_TIME_DOT.sub("[TS]", normalized)
    normalized = _TIME_ONLY.sub("[T]", normalized)
    normalized = _USER.sub("Пользователь=[U]", normalized)
    normalized = _SESSION.sub("Сеанс=[S]", normalized)
    normalized = _CONNECTION.sub("Соединение=[C]", normalized)
    normalized = _UUID.sub("[UUID]", normalized)
    normalized = _DOC_NUMBER.sub("№[N]", normalized)
    normalized = _NUMERIC_ID.sub("Id=[N]", normalized)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Cap длину чтобы fingerprint оставался компактным
    if len(normalized) > 200:
        normalized = normalized[:200]

    return OperationFingerprint(name=name, context_signature=normalized)


def match_operations(
    baseline_ops: list[OperationData], current_ops: list[OperationData]
) -> list[OperationMatch]:
    """Match operations by fingerprint.

    Returns единый список всех результатов с match_type:
    - "matched" — в обоих
    - "new" — только в current
    - "disappeared" — только в baseline

    Эффективное матчинг через dict indexes на signature().
    """
    # Compute fingerprints, build indexes
    baseline_idx: dict[str, OperationData] = {}
    for op in baseline_ops:
        if op.fingerprint is None:
            op.fingerprint = compute_fingerprint(op.name, op.context)
        baseline_idx[op.fingerprint.signature()] = op

    current_idx: dict[str, OperationData] = {}
    for op in current_ops:
        if op.fingerprint is None:
            op.fingerprint = compute_fingerprint(op.name, op.context)
        current_idx[op.fingerprint.signature()] = op

    results: list[OperationMatch] = []

    # Matched (в обоих) — итерируем baseline keys + проверяем наличие в current
    for sig, baseline_op in baseline_idx.items():
        if sig in current_idx:
            results.append(
                OperationMatch(
                    match_type="matched",
                    baseline=baseline_op,
                    current=current_idx[sig],
                    fingerprint=baseline_op.fingerprint,
                )
            )

    # New — только в current
    for sig, current_op in current_idx.items():
        if sig not in baseline_idx:
            results.append(
                OperationMatch(
                    match_type="new",
                    baseline=None,
                    current=current_op,
                    fingerprint=current_op.fingerprint,
                )
            )

    # Disappeared — только в baseline
    for sig, baseline_op in baseline_idx.items():
        if sig not in current_idx:
            results.append(
                OperationMatch(
                    match_type="disappeared",
                    baseline=baseline_op,
                    current=None,
                    fingerprint=baseline_op.fingerprint,
                )
            )

    return results
