"""Тесты log_detector — safety net поверх regex по имени файла."""

from __future__ import annotations

from pathlib import Path

import pytest

from optimyzer_backend.ingest.log_detector import is_tj_log_file


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_accepts_valid_tj_event(tmp_path: Path) -> None:
    # Sample из LOGS_INSPECTION.md (rmngr CALL)
    body = (
        b"47:02.139004-1,CALL,1,level=INFO,process=rmngr,OSThread=23464\n"
        b"47:02.139007-1,CALL,1,level=INFO,process=rmngr,OSThread=23464\n"
    )
    p = _write(tmp_path / "26051813.log", body)
    assert is_tj_log_file(p) is True


def test_accepts_short_microseconds(tmp_path: Path) -> None:
    # Discovery показал 1cv8s_1688/26051813.log с usec=728001 (6 цифр), а также короткие
    p = _write(tmp_path / "26051813.log", b"48:59.7-19046999,PROC,0,level=INFO\n")
    assert is_tj_log_file(p) is True


def test_rejects_random_text(tmp_path: Path) -> None:
    p = _write(tmp_path / "26051813.log", b"Hello world\nLine 2\nThis is not TJ\n")
    assert is_tj_log_file(p) is False


def test_rejects_empty_file(tmp_path: Path) -> None:
    p = _write(tmp_path / "26051813.log", b"")
    assert is_tj_log_file(p) is False


def test_handles_utf8_bom(tmp_path: Path) -> None:
    body = b"\xef\xbb\xbf47:02.139004-1,CALL,1,level=INFO,process=rmngr\n"
    p = _write(tmp_path / "26051813.log", body)
    assert is_tj_log_file(p) is True


def test_handles_only_whitespace_then_event(tmp_path: Path) -> None:
    body = b"\r\n  \n\t\n47:02.139004-1,CALL,1,level=INFO\n"
    p = _write(tmp_path / "26051813.log", body)
    assert is_tj_log_file(p) is True


def test_handles_io_error(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.log"
    assert is_tj_log_file(missing) is False


def test_truncated_sample_is_enough(tmp_path: Path) -> None:
    body = b"47:02.139004-1,CALL,1,level=INFO\n" + (b"a" * 100_000)
    p = _write(tmp_path / "26051813.log", body)
    assert is_tj_log_file(p, max_check_bytes=64) is True


@pytest.mark.parametrize(
    "first_line",
    [
        b"32:14.402023-8124000,DBMSSQL,5,process=rphost",
        b"00:01.100000-2000,CALL,3,process=rphost",
        b"09:33.371005-1,HASP,3,level=INFO,process=1CV8C",
    ],
)
def test_accepts_various_event_types(tmp_path: Path, first_line: bytes) -> None:
    p = _write(tmp_path / "26051813.log", first_line + b"\n")
    assert is_tj_log_file(p) is True
