"""End-to-end тест: synthetic zip → extract → parse → DuckDB → preset query."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from optimyzer_backend.archive.extractor import extract_archive
from optimyzer_backend.parsers.tj_parser import parse_file
from optimyzer_backend.storage.duckdb_store import DuckDBStore


@pytest.fixture
def synthetic_archive(tmp_path: Path) -> Path:
    z = tmp_path / "sample.zip"
    content_1 = (
        "32:14.402023-8124000,DBMSSQL,5,process=rphost,OSThread=12340,t:clientID=14,"
        "Sql='SELECT * FROM T1 WHERE x = 1',Rows=234,"
        "Context='Документ.РеализацияТоваровУслуг'\n"
        "32:15.000000-100000,CALL,3,process=rphost,OSThread=12340\n"
        "32:16.500000-50000,TDEADLOCK,4,process=rphost\n"
    )
    content_2 = (
        "00:01.000000-500000,DBMSSQL,5,process=rphost,Sql='SELECT 2',Rows=10\n"
        "00:02.000000-1000,EXCP,2,Exception='TestException'\n"
    )
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("rphost_1234/26051718.log", content_1)
        zf.writestr("rphost_5678/26051719.log", content_2)
    return z


def test_full_pipeline(synthetic_archive: Path, tmp_path: Path):
    # 1. Extract
    result = extract_archive(synthetic_archive)
    assert len(result.log_files) == 2

    # 2. Parse
    store = DuckDBStore("e2e-test", db_path=tmp_path / "e2e.duckdb")
    store.open()
    next_id = 1
    total = 0
    for lf in result.log_files:
        events = list(parse_file(lf.abs_path))
        store.bulk_insert(events, start_id=next_id)
        next_id += len(events)
        total += len(events)
    store.create_indexes()

    # 3. Verify counts
    assert total == 5
    assert store.count_events() == 5

    # 4. Run preset queries
    _, first = store.run_preset("first_100")
    assert len(first) == 5

    _, longest = store.run_preset("longest")
    durations = [r[2] for r in longest if r[2] is not None]
    assert durations == sorted(durations, reverse=True)
    # Самое долгое событие — 8_124_000 us
    assert durations[0] == 8_124_000

    _, deadlocks = store.run_preset("deadlocks")
    assert len(deadlocks) == 1

    store.close()


@pytest.mark.skip(reason="requires owner-provided real TJ archive — Q1 in docs/QUESTIONS.md")
def test_real_archive_acceptance(fixtures_dir: Path):
    """Acceptance gate из Sprint 0 DoD #19. Активируется когда Сергей предоставит fixture."""
    archive = fixtures_dir / "real-archive" / "tj.zip"
    assert archive.exists(), "Provide real TJ archive at " + str(archive)

    result = extract_archive(archive)
    total = 0
    errors = 0
    for lf in result.log_files:
        try:
            events = list(parse_file(lf.abs_path))
            total += len(events)
        except Exception:
            errors += 1
    assert total > 0, "Парсер не извлёк ни одного события"
    error_rate = errors / max(len(result.log_files), 1)
    assert error_rate < 0.05, f"Error rate {error_rate:.1%} превышает 5% (acceptance gate)"
