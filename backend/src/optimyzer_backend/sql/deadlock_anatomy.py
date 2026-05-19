"""Sprint 3 Phase D — Deadlock Anatomy.

Parser для TDEADLOCK событий по ИТС-спецификации технологического журнала.
Реализует анализ полей `extra` JSON:

  - Regions: список ресурсов (область блокировки), формат
    "Документ.РеализацияТоваровУслуг.Записи Exclusive" (имя_объекта режим)
  - WaitConnections: список ID соединений ждущих этого ресурса
  - DeadlockConnectionIntersections: пары "кто кого ждал", формат
    "<conn_a>->Имя.Объекта.Имя | <conn_b>->Имя.Другого.Объекта"
  - Locks: альтернативное имя поля в некоторых версиях платформы 8.3.x
  - usr: пользователь сессии (если известен)

Source: ИТС → Технологический журнал → События → TDEADLOCK
Эта схема стабильна с платформы 8.3.10+, проверена в синтетических
fixtures по типам ЦУП 2.12.3.2 (повышение уровня блокировки) и 2.12.3.3
(захват в разном порядке).

Note: в production-архиве Сергея (Phase 0 discovery) обнаружено 0 TDEADLOCK
events — logcfg.xml не имеет соответствующего filter. Real-data validation
Phase D отложена в OPUS_HANDOVER follow-up.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from optimyzer_backend.sql.executor import SQLExecutor


def _execute(archive_id: str, sql: str, params: list[Any], max_rows: int = 10_000) -> dict[str, Any]:
    with SQLExecutor(archive_id) as ex:
        return ex.execute(sql, params=params, max_rows=max_rows)


# ---------- Parsers for TDEADLOCK extra JSON ----------


@dataclass
class LockResource:
    """Одна заблокированная область — "Документ.X.Записи Exclusive"."""

    raw: str
    object_name: str  # "Документ.РеализацияТоваровУслуг.Записи"
    mode: str | None  # "Exclusive", "Shared", "U", "X" — зависит от версии


@dataclass
class DeadlockEdge:
    """Один edge в lock graph: connection A waits on resource that connection B holds."""

    waiter: str  # connection id or session reference
    blocker: str  # connection id или ресурс
    resource: str  # имя объекта блокировки


_REGION_RE = re.compile(r"^(.*?)\s+(\S+)$")
# DeadlockConnectionIntersections формат: "12345->Документ.X | 67890->Документ.Y"
_INTERSECTION_PAIR_RE = re.compile(r"(\S+)->([^|]+)")


def parse_regions(raw: str | None) -> list[LockResource]:
    """Парсит поле Regions / Locks.

    Формат на платформе 8.3.x:
        "Документ.РеализацияТоваровУслуг.Записи Exclusive,
         РегистрНакопления.ТоварыНаСкладах.Записи Shared"

    Разделители — запятая, переносы строк, либо `;`. Mode может отсутствовать.
    """
    if not raw:
        return []
    result: list[LockResource] = []
    parts = re.split(r"[,;\n]", raw)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = _REGION_RE.match(p)
        if m:
            obj_name, mode = m.group(1).strip(), m.group(2).strip()
            result.append(LockResource(raw=p, object_name=obj_name, mode=mode))
        else:
            result.append(LockResource(raw=p, object_name=p, mode=None))
    return result


def parse_deadlock_intersections(raw: str | None) -> list[DeadlockEdge]:
    """Парсит DeadlockConnectionIntersections — edges lock graph.

    Формат на платформе 8.3.x:
        "12345->Документ.X | 67890->Документ.Y"

    Каждая пара `id->resource` показывает: connection id ждал resource.
    Последовательные пары — это участники одного дедлок-цикла; cycle
    закрывается тем, что последний waiter == первый blocker.
    """
    if not raw:
        return []
    edges: list[DeadlockEdge] = []
    matches = list(_INTERSECTION_PAIR_RE.finditer(raw))
    if not matches:
        return []
    # Каждая пара (waiter, resource) — это «кто кого ждал»; blocker — это
    # следующая запись (хозяин этого ресурса).
    for i, m in enumerate(matches):
        waiter = m.group(1).strip()
        resource = m.group(2).strip()
        next_match = matches[(i + 1) % len(matches)]
        blocker = next_match.group(1).strip()
        edges.append(DeadlockEdge(waiter=waiter, blocker=blocker, resource=resource))
    return edges


def parse_wait_connections(raw: str | None) -> list[str]:
    """WaitConnections — список ID, разделённых запятой."""
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def parse_deadlock_extra(extra_raw: str | dict | None) -> dict[str, Any]:
    """Парсит весь extra JSON TDEADLOCK события в structured dict."""
    if extra_raw is None:
        return {}
    if isinstance(extra_raw, dict):
        extra = extra_raw
    else:
        try:
            extra = json.loads(extra_raw) if extra_raw else {}
        except (json.JSONDecodeError, TypeError):
            return {"_parse_error": True, "raw": str(extra_raw)[:200]}
    if not isinstance(extra, dict):
        return {"_parse_error": True, "raw": str(extra_raw)[:200]}

    # Возможные имена полей по разным версиям платформы (per ITS docs as of 2026-05)
    regions_raw = extra.get("Regions") or extra.get("Locks")
    waits_raw = extra.get("WaitConnections")
    edges_raw = (
        extra.get("DeadlockConnectionIntersections")
        or extra.get("DeadlockIntersections")
    )

    return {
        "regions": [
            {"raw": r.raw, "object_name": r.object_name, "mode": r.mode}
            for r in parse_regions(regions_raw)
        ],
        "wait_connections": parse_wait_connections(waits_raw),
        "edges": [
            {"waiter": e.waiter, "blocker": e.blocker, "resource": e.resource}
            for e in parse_deadlock_intersections(edges_raw)
        ],
        "raw_extra": extra,
    }


# ---------- Public API ----------


def list_deadlocks(archive_id: str, *, limit: int = 200) -> dict[str, Any]:
    """Список всех TDEADLOCK events для выбора в drill-down."""
    sql = """
        SELECT
            id,
            ts,
            session_id,
            process_role,
            process_pid,
            context_normalized,
            duration_us / 1000.0 AS duration_ms,
            extra
        FROM events
        WHERE event_type = 'TDEADLOCK'
        ORDER BY ts DESC
        LIMIT ?
    """
    return _execute(archive_id, sql, [limit])


def get_deadlock_anatomy(
    archive_id: str,
    event_id: int,
    *,
    window_seconds: int = 30,
    surrounding_limit: int = 200,
) -> dict[str, Any]:
    """Полный разбор одного TDEADLOCK события.

    Возвращает:
      - the_event: само TDEADLOCK событие
      - parsed_extra: структурированный extra (regions, wait_connections, edges)
      - participants: какие session_id / process_pid были задействованы
      - surrounding: ±window_seconds events вокруг (для context)
    """
    # 1. Сам event
    event_sql = """
        SELECT
            id, ts, session_id, user_name, process_role, process_pid,
            context, context_normalized, duration_us / 1000.0 AS duration_ms,
            extra::VARCHAR AS extra_str
        FROM events
        WHERE id = ? AND event_type = 'TDEADLOCK'
    """
    event_result = _execute(archive_id, event_sql, [event_id])
    if not event_result.get("rows"):
        return {"found": False, "event_id": event_id}
    row = event_result["rows"][0]
    cols = [c["name"] for c in event_result["columns"]]
    event_dict = dict(zip(cols, row))
    extra_raw = event_dict.pop("extra_str", None)
    parsed_extra = parse_deadlock_extra(extra_raw)

    # 2. Participants — все участники из wait_connections + сам session_id
    participant_ids: set[str] = set()
    if event_dict.get("session_id") is not None:
        participant_ids.add(str(event_dict["session_id"]))
    for w in parsed_extra.get("wait_connections", []):
        participant_ids.add(str(w))
    for e in parsed_extra.get("edges", []):
        participant_ids.add(str(e["waiter"]))
        participant_ids.add(str(e["blocker"]))

    # 3. Surrounding events ±N seconds
    surrounding_sql = """
        SELECT
            id, ts, event_type, session_id, process_role, process_pid,
            duration_us / 1000.0 AS duration_ms,
            context_normalized
        FROM events
        WHERE ts BETWEEN
            (SELECT ts FROM events WHERE id = ?) - INTERVAL '%d seconds'
            AND (SELECT ts FROM events WHERE id = ?) + INTERVAL '%d seconds'
          AND id <> ?
        ORDER BY ts
        LIMIT ?
    """ % (window_seconds, window_seconds)
    surrounding = _execute(
        archive_id,
        surrounding_sql,
        [event_id, event_id, event_id, surrounding_limit],
    )

    return {
        "found": True,
        "event": event_dict,
        "parsed_extra": parsed_extra,
        "participants": sorted(participant_ids),
        "surrounding": {
            "columns": surrounding["columns"],
            "rows": surrounding["rows"],
            "row_count": surrounding["row_count"],
            "window_seconds": window_seconds,
        },
    }
