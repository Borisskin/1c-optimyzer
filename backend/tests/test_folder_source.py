"""Тесты FolderSource — primary способ загрузки в Module 1."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from optimyzer_backend.ingest.folder_source import FolderSource
from optimyzer_backend.ingest.source import LogFile


SAMPLE_EVENT = b"47:02.139004-1,CALL,1,level=INFO,process=rmngr,OSThread=23464\n"


def _make_log(path: Path, body: bytes = SAMPLE_EVENT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def test_folder_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FolderSource(tmp_path / "missing")


def test_folder_not_a_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("hello")
    with pytest.raises(NotADirectoryError):
        FolderSource(file_path)


def test_folder_discovers_flat_logs(tmp_path: Path) -> None:
    _make_log(tmp_path / "26051813.log")
    _make_log(tmp_path / "26051814.log")
    source = FolderSource(tmp_path)
    files = source.discover()
    assert len(files) == 2
    names = sorted(lf.path.name for lf in files)
    assert names == ["26051813.log", "26051814.log"]


def test_folder_discovers_standard_structure(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_28220" / "26051813.log")
    _make_log(tmp_path / "rphost_28220" / "26051814.log")
    _make_log(tmp_path / "rmngr_24128" / "26051813.log")
    files = FolderSource(tmp_path).discover()
    assert len(files) == 3
    roles = sorted(lf.process_role for lf in files)
    assert roles == ["rmngr", "rphost", "rphost"]


def test_folder_discovers_mixed_case_prefixes(tmp_path: Path) -> None:
    _make_log(tmp_path / "1CV8C_12044" / "26051813.log")
    _make_log(tmp_path / "1cv8c_23100" / "26051813.log")
    files = FolderSource(tmp_path).discover()
    assert len(files) == 2
    # role всегда lowercase независимо от регистра имени папки
    assert all(lf.process_role == "1cv8c" for lf in files)
    pids = sorted(lf.process_pid or 0 for lf in files)
    assert pids == [12044, 23100]


def test_folder_discovers_all_six_role_types(tmp_path: Path) -> None:
    for role, pid in [
        ("rphost", 28220),
        ("rmngr", 24128),
        ("ragent", 28284),
        ("1cv8c", 12044),
        ("1cv8s", 1688),
        ("1cv8", 24120),
    ]:
        _make_log(tmp_path / f"{role}_{pid}" / "26051813.log")
    files = FolderSource(tmp_path).discover()
    assert len(files) == 6
    roles = {lf.process_role for lf in files}
    assert roles == {"rphost", "rmngr", "ragent", "1cv8c", "1cv8s", "1cv8"}


def test_folder_filters_non_log_files(tmp_path: Path) -> None:
    _make_log(tmp_path / "26051813.log")
    (tmp_path / "readme.txt").write_text("ignore me")
    (tmp_path / "snapshot.xml").write_text("<x/>")
    (tmp_path / "session.lck").write_text("")
    files = FolderSource(tmp_path).discover()
    assert len(files) == 1
    assert files[0].path.name == "26051813.log"


def test_folder_filters_bad_content_log(tmp_path: Path) -> None:
    # Файл с правильным именем YYMMDDHH.log, но не TJ-content → safety net фильтрует
    _make_log(tmp_path / "26051813.log", body=b"Hello world\nNot a TJ log\n")
    files = FolderSource(tmp_path).discover()
    assert files == []


def test_folder_filters_non_matching_filenames(tmp_path: Path) -> None:
    # 7 цифр — не match (нужно ровно 8)
    _make_log(tmp_path / "2605181.log", body=SAMPLE_EVENT)
    # 10 цифр — не match
    _make_log(tmp_path / "2605181300.log", body=SAMPLE_EVENT)
    # non-numeric — не match
    _make_log(tmp_path / "service.log", body=SAMPLE_EVENT)
    files = FolderSource(tmp_path).discover()
    assert files == []


def test_folder_handles_broken_symlink(tmp_path: Path) -> None:
    _make_log(tmp_path / "26051813.log")
    # broken symlink → graceful skip
    broken_target = tmp_path / "does_not_exist_target.log"
    broken_link = tmp_path / "26051899.log"
    try:
        os.symlink(broken_target, broken_link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available on this platform/user")
    files = FolderSource(tmp_path).discover()
    # broken link не должен крашить и не должен попасть в результат
    assert any(lf.path.name == "26051813.log" for lf in files)


def test_folder_sort_order_ascending_by_size(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_1" / "26051813.log", body=SAMPLE_EVENT * 1000)
    _make_log(tmp_path / "rphost_2" / "26051813.log", body=SAMPLE_EVENT * 1)
    _make_log(tmp_path / "rphost_3" / "26051813.log", body=SAMPLE_EVENT * 100)
    files = FolderSource(tmp_path).discover()
    sizes = [lf.size_bytes for lf in files]
    assert sizes == sorted(sizes)
    # Маленькие первыми (fast feedback в progress)
    assert files[0].size_bytes < files[-1].size_bytes


def test_folder_process_role_extracted(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_28220" / "26051813.log")
    [lf] = FolderSource(tmp_path).discover()
    assert lf.process_role == "rphost"
    assert lf.process_pid == 28220
    assert lf.timestamp_from_name == "26051813"


def test_folder_open_streams_lines(tmp_path: Path) -> None:
    body = (
        SAMPLE_EVENT
        + b"47:02.139007-1,CALL,1,level=INFO,process=rmngr\n"
        + b"47:02.139010-1,CALL,1,level=INFO,process=rmngr\n"
    )
    _make_log(tmp_path / "26051813.log", body=body)
    source = FolderSource(tmp_path)
    [lf] = source.discover()
    lines = list(source.open(lf, encoding="utf-8-sig"))
    assert len(lines) == 3
    assert lines[0].startswith("47:02.139004")


def test_folder_relative_path_is_under_root(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_28220" / "26051813.log")
    [lf] = FolderSource(tmp_path).discover()
    # relative_path не должен содержать root
    assert not lf.relative_path.startswith(str(tmp_path))
    assert "rphost_28220" in lf.relative_path


def test_folder_unknown_role_for_flat_logs(tmp_path: Path) -> None:
    # Файлы прямо в root (parent.name == basename корня) → unknown
    _make_log(tmp_path / "26051813.log")
    [lf] = FolderSource(tmp_path).discover()
    assert lf.process_role == "unknown"
    assert lf.process_pid is None


def _make_log_isinstance_check() -> None:
    pass


def test_folder_log_file_type(tmp_path: Path) -> None:
    _make_log(tmp_path / "26051813.log")
    [lf] = FolderSource(tmp_path).discover()
    assert isinstance(lf, LogFile)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission denied test")
def test_folder_handles_permission_denied(tmp_path: Path) -> None:
    secret_dir = tmp_path / "no_access"
    secret_dir.mkdir()
    _make_log(secret_dir / "26051813.log")
    accessible = _make_log(tmp_path / "26051814.log")
    try:
        os.chmod(secret_dir, 0)
        files = FolderSource(tmp_path).discover()
        # accessible должен попасть в результат, no_access — silently skipped
        assert any(lf.path == accessible for lf in files)
    finally:
        os.chmod(secret_dir, stat.S_IRWXU)


# --- Пустые логи ТЖ (Инфостарт, июль 2026) -----------------------------------
# Кейс из прода: logcfg настроен на события (долгие запросы к СУБД), которых за
# период не было. ТЖ создаёт папки процессов и файлы ГГММДДЧЧ.log нулевого
# размера. Файлы отбраковываются, discovery пуст, и пользователь видел
# «Лог-файлы не найдены» — думал, что сломалось приложение, и переустанавливал.


def test_empty_log_files_counted_in_scan_stats(tmp_path: Path) -> None:
    _make_log(tmp_path / "rphost_1234" / "26071510.log", b"")
    _make_log(tmp_path / "rphost_1234" / "26071511.log", b"")

    source = FolderSource(tmp_path)
    assert source.discover() == []
    assert source.scan_stats["name_matched"] == 2
    assert source.scan_stats["empty"] == 2
    assert source.scan_stats["not_tj"] == 0


def test_empty_logs_produce_explanatory_message(tmp_path: Path) -> None:
    from optimyzer_backend.rpc.handlers import _no_logs_message

    _make_log(tmp_path / "rphost_1234" / "26071510.log", b"")
    source = FolderSource(tmp_path)
    source.discover()

    message = _no_logs_message(source)
    assert "пустые" in message
    assert "logcfg" in message
    # Старая формулировка вводила в заблуждение — её быть не должно.
    assert message != "Лог-файлы не найдены в указанной папке"


def test_non_tj_files_counted_separately(tmp_path: Path) -> None:
    _make_log(tmp_path / "app" / "26071510.log", b"nginx access log line\n")

    source = FolderSource(tmp_path)
    assert source.discover() == []
    assert source.scan_stats["not_tj"] == 1
    assert source.scan_stats["empty"] == 0
