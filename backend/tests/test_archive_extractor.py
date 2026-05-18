"""Тесты для zip extractor."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from optimyzer_backend.archive.extractor import extract_archive


@pytest.fixture
def small_zip(tmp_path: Path) -> Path:
    z = tmp_path / "sample.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("rphost_1234/26051718.log", "00:01.000000-1000,CALL,3,key=val\n")
        zf.writestr("rphost_1234/26051719.log", "00:02.000000-2000,DBMSSQL,5,Sql='SELECT 1'\n")
        zf.writestr("rphost_5678/26051718.log", "00:01.500000-500,EXCP,2,Exception='X'\n")
    return z


def test_extract_archive_basic(small_zip: Path):
    result = extract_archive(small_zip)
    assert len(result.files) == 3
    assert len(result.log_files) == 3
    for f in result.log_files:
        assert f.abs_path.exists()
        assert f.abs_path.read_text(encoding="utf-8").strip() != ""


def test_extract_rejects_non_zip(tmp_path: Path):
    bad = tmp_path / "notazip.zip"
    bad.write_text("not a zip")
    with pytest.raises(ValueError):
        extract_archive(bad)


def test_extract_rejects_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        extract_archive(tmp_path / "missing.zip")


def test_extract_rejects_zipslip(tmp_path: Path):
    """Архив с `..` в путях не должен распаковываться вне target dir."""
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../../escape.log", "data")
        zf.writestr("/absolute.log", "data")
        zf.writestr("good/00010101.log", "00:01.000000-1000,CALL,3\n")
    result = extract_archive(z)
    rel_paths = [f.relative_path for f in result.files]
    assert "good/00010101.log" in rel_paths
    assert all(".." not in p.split("/") for p in rel_paths)
    assert not any(p.startswith("/") for p in rel_paths)
