"""Sprint 3 Phase D — Deadlock Anatomy tests.

Использует синтетический fixture с 3 TDEADLOCK events по типам ЦУП 2.12.3.
Real-data validation отложена в OPUS_HANDOVER (production-архив содержит
0 TDEADLOCK из-за logcfg.xml без соответствующего filter).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optimyzer_backend.sql.deadlock_anatomy import (
    DeadlockEdge,
    LockResource,
    get_deadlock_anatomy,
    list_deadlocks,
    parse_deadlock_extra,
    parse_deadlock_intersections,
    parse_regions,
    parse_wait_connections,
)
from tests.fixtures.synthetic_tdeadlock_archive import (
    SYNTHETIC_ARCHIVE_ID,
    create_synthetic_tdeadlock_archive,
    deadlock_event_ids,
)


# ---------- Unit tests: parsers ----------


def test_parse_regions_single() -> None:
    out = parse_regions("Документ.Реализация.Записи Exclusive")
    assert len(out) == 1
    assert out[0].object_name == "Документ.Реализация.Записи"
    assert out[0].mode == "Exclusive"


def test_parse_regions_multiple_with_commas() -> None:
    raw = "Документ.А.Записи Exclusive, РегистрНакопления.Б.Записи Shared"
    out = parse_regions(raw)
    assert len(out) == 2
    assert out[0].mode == "Exclusive"
    assert out[1].mode == "Shared"


def test_parse_regions_no_mode() -> None:
    out = parse_regions("Документ.А.Записи")
    assert len(out) == 1
    assert out[0].mode is None
    assert out[0].object_name == "Документ.А.Записи"


def test_parse_regions_empty() -> None:
    assert parse_regions(None) == []
    assert parse_regions("") == []


def test_parse_wait_connections() -> None:
    assert parse_wait_connections("12345,67890") == ["12345", "67890"]
    assert parse_wait_connections("") == []
    assert parse_wait_connections(None) == []


def test_parse_intersections_two_party() -> None:
    raw = "1001->Документ.Реал.Записи | 1002->Документ.Пост.Записи"
    edges = parse_deadlock_intersections(raw)
    assert len(edges) == 2
    # Cycle closure: waiter[0]'s blocker = waiter[1]; waiter[1]'s blocker = waiter[0]
    assert edges[0].waiter == "1001"
    assert edges[0].blocker == "1002"
    assert edges[0].resource == "Документ.Реал.Записи"
    assert edges[1].waiter == "1002"
    assert edges[1].blocker == "1001"


def test_parse_intersections_empty() -> None:
    assert parse_deadlock_intersections(None) == []
    assert parse_deadlock_intersections("") == []


def test_parse_extra_full_payload() -> None:
    import json as _json

    payload = _json.dumps({
        "Regions": "Документ.А Exclusive, РегистрНакопления.Б Shared",
        "WaitConnections": "1001,1002",
        "DeadlockConnectionIntersections": "1001->Документ.А | 1002->РегистрНакопления.Б",
        "usr": "ИвановИИ",
    })
    parsed = parse_deadlock_extra(payload)
    assert len(parsed["regions"]) == 2
    assert parsed["wait_connections"] == ["1001", "1002"]
    assert len(parsed["edges"]) == 2
    assert parsed["raw_extra"]["usr"] == "ИвановИИ"


def test_parse_extra_handles_dict_directly() -> None:
    parsed = parse_deadlock_extra({"Regions": "Док.А Exclusive"})
    assert parsed["regions"][0]["object_name"] == "Док.А"


def test_parse_extra_alt_field_name_locks() -> None:
    """Некоторые версии 1С пишут поле как 'Locks' вместо 'Regions'."""
    parsed = parse_deadlock_extra({"Locks": "Док.А Exclusive"})
    assert len(parsed["regions"]) == 1
    assert parsed["regions"][0]["object_name"] == "Док.А"


def test_parse_extra_garbage() -> None:
    parsed = parse_deadlock_extra("not-a-json")
    assert parsed.get("_parse_error") is True


# ---------- Integration tests: synthetic archive ----------


@pytest.fixture
def synthetic_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_dir = tmp_path / "duckdb"
    db_dir.mkdir()
    db_path = db_dir / f"{SYNTHETIC_ARCHIVE_ID}.duckdb"
    create_synthetic_tdeadlock_archive(db_path)
    monkeypatch.setattr(
        "optimyzer_backend.sql.executor.default_db_dir", lambda: db_dir
    )
    return SYNTHETIC_ARCHIVE_ID


def test_list_deadlocks_returns_3_events(synthetic_archive: str) -> None:
    result = list_deadlocks(synthetic_archive)
    assert result["row_count"] == 3


def test_get_deadlock_anatomy_dl1_higher_lock_pattern(synthetic_archive: str) -> None:
    """ЦУП 2.12.3.2 — повышение уровня блокировки."""
    result = get_deadlock_anatomy(synthetic_archive, 104)
    assert result["found"] is True
    parsed = result["parsed_extra"]
    # Одна и та же область — РегистрНакопления.ПартииТоваровНаСкладах
    assert len(parsed["regions"]) == 1
    assert parsed["regions"][0]["object_name"] == "РегистрНакопления.ПартииТоваровНаСкладах.Записи"
    assert parsed["regions"][0]["mode"] == "Exclusive"
    assert "1001" in parsed["wait_connections"]
    assert "1002" in parsed["wait_connections"]
    # Edges: waiter↔blocker по cycle closure
    assert len(parsed["edges"]) == 2


def test_get_deadlock_anatomy_dl2_different_order_pattern(synthetic_archive: str) -> None:
    """ЦУП 2.12.3.3 — захват в разном порядке."""
    result = get_deadlock_anatomy(synthetic_archive, 203)
    assert result["found"] is True
    parsed = result["parsed_extra"]
    # Два разных ресурса
    assert len(parsed["regions"]) == 2
    object_names = {r["object_name"] for r in parsed["regions"]}
    assert "Документ.РеализацияТоваровУслуг.Записи" in object_names
    assert "РегистрНакопления.ТоварыНаСкладах.Записи" in object_names


def test_get_deadlock_anatomy_dl3_single_resource_pattern(synthetic_archive: str) -> None:
    """Один-ресурс между двумя процессами."""
    result = get_deadlock_anatomy(synthetic_archive, 302)
    assert result["found"] is True
    parsed = result["parsed_extra"]
    assert len(parsed["regions"]) == 1
    assert "Контрагенты" in parsed["regions"][0]["object_name"]


def test_get_deadlock_anatomy_participants_extracted(synthetic_archive: str) -> None:
    result = get_deadlock_anatomy(synthetic_archive, 104)
    parts = set(result["participants"])
    # session_id 1001 + WaitConnections "1001,1002"
    assert {"1001", "1002"}.issubset(parts)


def test_get_deadlock_anatomy_includes_surrounding_events(synthetic_archive: str) -> None:
    result = get_deadlock_anatomy(synthetic_archive, 104, window_seconds=60)
    # Surrounding events: 101, 102, 103 (TLOCK) — все в окне ±60s от dl 104
    s = result["surrounding"]
    assert s["row_count"] >= 3


def test_get_deadlock_anatomy_unknown_event(synthetic_archive: str) -> None:
    result = get_deadlock_anatomy(synthetic_archive, 99999)
    assert result["found"] is False


def test_synthetic_fixture_has_3_distinct_deadlock_types(synthetic_archive: str) -> None:
    """Acceptance: synthetic fixture покрывает 3 типа deadlock паттернов
    из ЦУП 2.12.3 (one-resource conflict, lock escalation, order mismatch)."""
    ids = deadlock_event_ids()
    assert len(ids) == 3
    for eid in ids:
        result = get_deadlock_anatomy(synthetic_archive, eid)
        assert result["found"] is True
        # Each deadlock должен иметь parsed regions + edges
        assert len(result["parsed_extra"]["regions"]) >= 1


# Re-export for clarity in tests
_ = DeadlockEdge
_ = LockResource
