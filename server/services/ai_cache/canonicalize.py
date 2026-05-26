"""Sprint 11 — canonicalization для cache key computation.

Цель — два логически идентичных входа (отличающиеся только runtime stats /
форматированием / порядком атрибутов) → одинаковый cache key. Иначе кеш
почти всегда даёт миссы из-за тривиальных различий.

Стратегия по типам:
  - MSSQL XML: парсим через stdlib ElementTree, удаляем runtime атрибуты
    (Actual*), серилизуем через c14n (canonical XML 1.0).
  - MSSQL TEXT: нормализуем whitespace; удаляем номера строк если есть.
  - PG TEXT: удаляем `(actual time=... rows=... loops=...)`, `Buffers:`,
    `Planning Time:`, `Execution Time:`, нормализуем whitespace.
  - PG JSON: парсим, рекурсивно удаляем runtime-ключи, sort_keys=True.
  - SDBL: удаляем комментарии, нормализуем whitespace.
  - Logcfg description: lowercase + strip punctuation + collapse whitespace.

ВАЖНО: канонизация защищает от тривиальных вариаций, но НЕ должна терять
семантическую информацию. Например, для MSSQL XML мы НЕ убираем
EstimatedRows (оптимизатор использует их при выборе плана), только Actual*.
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET


# ---------- MSSQL XML ----------

# Runtime-only атрибуты SHOWPLAN_XML — они появляются только в actual plan
# (после выполнения) и НЕ влияют на структуру/решения оптимизатора.
# Список из MSDN: https://learn.microsoft.com/en-us/sql/relational-databases/system-catalog-views/showplan-xml-schema
_MSSQL_RUNTIME_ATTRS = frozenset(
    [
        "ActualRows",
        "ActualRowsRead",
        "ActualExecutions",
        "ActualEndOfScans",
        "ActualExecutionMode",
        "ActualLogicalReads",
        "ActualPhysicalReads",
        "ActualReadAheads",
        "ActualLobLogicalReads",
        "ActualLobPhysicalReads",
        "ActualLobReadAheads",
        "ActualScans",
        "ActualElapsedms",
        "ActualCPUms",
        "Brick",  # NUMA-локальная информация
        "Thread",
        "TaskAddr",
    ]
)


def canonicalize_plan_mssql_xml(plan_xml: str) -> str:
    """Удалить runtime-only атрибуты и канонизировать XML.

    Если plan_xml не валиден как XML — возвращаем normalize_whitespace(plan_xml)
    как fallback (cache key всё равно будет стабильным).
    """
    try:
        root = ET.fromstring(plan_xml)
    except ET.ParseError:
        # Fallback: невалидный XML → нормализуем как text
        return _collapse_whitespace(plan_xml)

    # Рекурсивно удаляем runtime атрибуты
    for elem in root.iter():
        for attr in list(elem.attrib):
            if attr in _MSSQL_RUNTIME_ATTRS:
                del elem.attrib[attr]
            # Атрибуты с namespace prefix `{ns}Actual...` тоже
            elif "}" in attr:
                local = attr.split("}", 1)[1]
                if local in _MSSQL_RUNTIME_ATTRS:
                    del elem.attrib[attr]

    # Канонизация через stdlib (Python 3.8+): сортирует атрибуты,
    # нормализует whitespace, убирает comments/PIs. with out=None возвращает str.
    return ET.canonicalize(
        xml_data=ET.tostring(root, encoding="utf-8"),
        with_comments=False,
    )


# ---------- MSSQL TEXT ----------

# Строки вида "Estimated I/O Cost = 0.123456" варьируются от запуска к запуску
# на пару знаков после запятой → убираем точность до 3 знаков.
_MSSQL_FLOAT_PATTERN = re.compile(r"\b(\d+\.\d{4,})\b")
# Префиксы вида "1>", "2>" из SQLCMD output
_LINE_NUMBER_PATTERN = re.compile(r"^\s*\d+>\s*", re.MULTILINE)


def canonicalize_plan_mssql_text(plan_text: str) -> str:
    """Нормализовать SHOWPLAN_TEXT из 1С planSQLText."""
    canonical = _LINE_NUMBER_PATTERN.sub("", plan_text)
    canonical = _MSSQL_FLOAT_PATTERN.sub(
        lambda m: f"{float(m.group(1)):.3f}",
        canonical,
    )
    return _collapse_whitespace(canonical)


# ---------- PG TEXT ----------

# `(actual time=0.123..0.456 rows=789 loops=1)` — после EXPLAIN ANALYZE
_PG_ACTUAL_TIME = re.compile(
    r"\(actual\s+time=[\d.]+\.\.[\d.]+\s+rows=[\d.]+\s+loops=\d+\)"
)
# Buffers: shared hit=12 read=34 dirtied=0 written=0
_PG_BUFFERS = re.compile(r"^\s*Buffers:.*$", re.MULTILINE)
# Planning Time: 0.123 ms / Execution Time: 4.567 ms
_PG_TIMING = re.compile(
    r"^\s*(Planning|Execution|JIT|Functions|Inlining|Optimization|Emission|Generation|Settings|Trigger|Timing)\s*[:\s].*$",
    re.MULTILINE,
)
# I/O Timings: shared/local read=...
_PG_IO_TIMINGS = re.compile(r"^\s*I/O Timings:.*$", re.MULTILINE)


def canonicalize_plan_pg_text(plan_text: str) -> str:
    """Нормализовать PG EXPLAIN [ANALYZE] TEXT output."""
    canonical = _PG_ACTUAL_TIME.sub("", plan_text)
    canonical = _PG_BUFFERS.sub("", canonical)
    canonical = _PG_TIMING.sub("", canonical)
    canonical = _PG_IO_TIMINGS.sub("", canonical)
    return _collapse_whitespace(canonical)


# ---------- PG JSON ----------

_PG_RUNTIME_KEYS = frozenset(
    [
        # Runtime measurements (execution-time only)
        "Actual Rows",
        "Actual Total Time",
        "Actual Startup Time",
        "Actual Loops",
        "Actual Inner Loops",
        "Buffers",
        "Shared Hit Blocks",
        "Shared Read Blocks",
        "Shared Dirtied Blocks",
        "Shared Written Blocks",
        "Local Hit Blocks",
        "Local Read Blocks",
        "Local Dirtied Blocks",
        "Local Written Blocks",
        "Temp Read Blocks",
        "Temp Written Blocks",
        "I/O Read Time",
        "I/O Write Time",
        "Shared I/O Read Time",
        "Shared I/O Write Time",
        "Local I/O Read Time",
        "Local I/O Write Time",
        "Temp I/O Read Time",
        "Temp I/O Write Time",
        "Planning Time",
        "Execution Time",
        "Triggers",
        "JIT",
        "Settings",
        "Workers Launched",
        "Workers Planned",  # PG включает их в plan но реальное число варьируется
        "Workers",
    ]
)


def _strip_pg_runtime_recursive(obj):
    """Рекурсивно удалить runtime-ключи из PG JSON plan."""
    if isinstance(obj, dict):
        return {
            k: _strip_pg_runtime_recursive(v)
            for k, v in obj.items()
            if k not in _PG_RUNTIME_KEYS
        }
    if isinstance(obj, list):
        return [_strip_pg_runtime_recursive(item) for item in obj]
    return obj


def canonicalize_plan_pg_json(plan_json_str: str) -> str:
    """Нормализовать PG EXPLAIN FORMAT JSON output.

    На invalid JSON возвращаем как text fallback.
    """
    try:
        plan = json.loads(plan_json_str)
    except json.JSONDecodeError:
        return _collapse_whitespace(plan_json_str)
    cleaned = _strip_pg_runtime_recursive(plan)
    return json.dumps(cleaned, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# ---------- SDBL ----------

_SDBL_LINE_COMMENT = re.compile(r"//.*?$", re.MULTILINE)
_SDBL_BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")


def canonicalize_sdbl(sdbl: str) -> str:
    """Нормализовать SDBL запрос."""
    canonical = _SDBL_LINE_COMMENT.sub("", sdbl)
    canonical = _SDBL_BLOCK_COMMENT.sub("", canonical)
    return _collapse_whitespace(canonical)


# ---------- Logcfg description ----------

_LOGCFG_PUNCT = re.compile(r"[.,!?;:()\[\]{}\"'«»\-—]+")


def canonicalize_logcfg_description(description: str) -> str:
    """Нормализовать описание проблемы для Logcfg AI Wizard."""
    canonical = description.lower().strip()
    canonical = _LOGCFG_PUNCT.sub(" ", canonical)
    return _collapse_whitespace(canonical)


# ---------- Common helpers ----------

_WHITESPACE = re.compile(r"\s+")


def _collapse_whitespace(s: str) -> str:
    """Свернуть любые whitespace последовательности в один пробел."""
    return _WHITESPACE.sub(" ", s).strip()


# ---------- Cache key computation ----------


def compute_cache_key(
    canonical_input: str,
    cache_type: str,
    prompt_version: str,
    model: str,
) -> str:
    """Финальный sha256 cache key.

    Args:
        canonical_input: уже канонизированный текст (через одну из
            canonicalize_* функций).
        cache_type: имя из CacheType (например, "plan_mssql_xml").
        prompt_version: версия system prompt — bumping invalidates cache.
        model: имя модели — разные модели дают разные ответы.

    Returns:
        Hex-encoded sha256 hash (64 chars).
    """
    composite = (
        f"{canonical_input}|type_{cache_type}|prompt_{prompt_version}|model_{model}"
    )
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()
