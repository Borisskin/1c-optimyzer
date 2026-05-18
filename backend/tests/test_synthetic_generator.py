"""Тесты synthetic generator + ingest на synthetic folder (Sprint 1, Phase K)."""

from __future__ import annotations

from pathlib import Path

from optimyzer_backend.ingest import FolderSource
from optimyzer_backend.parsers.tj_parser import parse_log_file_streaming
from optimyzer_backend.storage.duckdb_store import DuckDBStore

from tests.fixtures.synthetic import build_folder


def test_build_folder_creates_structure(tmp_path: Path) -> None:
    folder = build_folder(tmp_path / "synth", total_bytes=64_000)
    assert folder.is_dir()
    subdirs = [p for p in folder.iterdir() if p.is_dir()]
    assert len(subdirs) > 0
    log_files = list(folder.rglob("*.log"))
    assert len(log_files) > 0


def test_build_folder_files_are_parseable(tmp_path: Path) -> None:
    folder = build_folder(tmp_path / "synth", total_bytes=200_000)
    source = FolderSource(folder)
    files = source.discover()
    assert len(files) > 0
    total_events = 0
    for lf in files:
        events = list(parse_log_file_streaming(source, lf))
        total_events += len(events)
    assert total_events > 0


def test_synthetic_folder_ingests_into_duckdb(tmp_path: Path) -> None:
    folder = build_folder(tmp_path / "synth", total_bytes=500_000)
    store = DuckDBStore("synthetic-test", db_path=tmp_path / "test.duckdb")
    store.open()

    source = FolderSource(folder)
    log_files = source.discover()
    assert len(log_files) > 0

    with store.appender() as appender:
        for lf in log_files:
            for event in parse_log_file_streaming(source, lf):
                appender.append_event(event)

    store.create_indexes()
    assert store.count_events() > 0

    # Process roles из имён папок попадают в DB
    roles = store.open().execute(
        "SELECT DISTINCT process_role FROM events WHERE process_role <> 'unknown'"
    ).fetchall()
    assert len(roles) > 0
    role_names = {r[0] for r in roles}
    valid_roles = {"rphost", "rmngr", "ragent", "1cv8c", "1cv8s", "1cv8"}
    assert role_names <= valid_roles

    store.close()


def test_generator_deterministic_with_seed(tmp_path: Path) -> None:
    folder_a = build_folder(tmp_path / "a", total_bytes=50_000, seed=123)
    folder_b = build_folder(tmp_path / "b", total_bytes=50_000, seed=123)

    files_a = sorted(p.relative_to(folder_a) for p in folder_a.rglob("*.log"))
    files_b = sorted(p.relative_to(folder_b) for p in folder_b.rglob("*.log"))
    assert files_a == files_b
