"""Тесты encoding_detector — utf-8-sig default, cp1251/cp866 fallback."""

from __future__ import annotations

from pathlib import Path

from optimyzer_backend.ingest.encoding_detector import detect_encoding


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


_CYR_PHRASE = "47:02.139004-1,CALL,1,process=rmngr,Контекст=РасчётыСервер\n"


def test_detects_utf8_sig(tmp_path: Path) -> None:
    body = b"\xef\xbb\xbf" + _CYR_PHRASE.encode("utf-8")
    p = _write(tmp_path / "a.log", body)
    assert detect_encoding(p) == "utf-8-sig"


def test_detects_plain_utf8(tmp_path: Path) -> None:
    # utf-8-sig codec без BOM ведёт себя идентично utf-8, поэтому detector честно
    # возвращает 'utf-8-sig' (первый кандидат, который декодирует sample).
    # Это безопасно: utf-8-sig читалка corretly strip-ает BOM если он есть, и работает
    # как utf-8 если BOM нет. Главное — результат НЕ cp1251/cp866.
    body = _CYR_PHRASE.encode("utf-8")
    p = _write(tmp_path / "a.log", body)
    assert detect_encoding(p) in ("utf-8", "utf-8-sig")


def test_detects_cp1251(tmp_path: Path) -> None:
    # Кириллица в cp1251 содержит байты 0xC0..0xFF, многие из которых невалидны в utf-8 → fallback на cp1251
    body = _CYR_PHRASE.encode("cp1251")
    p = _write(tmp_path / "a.log", body)
    assert detect_encoding(p) == "cp1251"


def test_detects_cp866_or_cp1251_for_non_utf8(tmp_path: Path) -> None:
    # cp866 и cp1251 — оба байтоориентированные, любая последовательность декодируется.
    # Detector возвращает первую успешную → если cp1251 проходит первым, вернётся cp1251.
    # Здесь проверяем что fallback цепочка работает на содержимом которое utf-8 точно не валидно.
    body = b"\xff\xfe\xfd_not_utf8_47:02.139004-1,CALL,1\n"
    p = _write(tmp_path / "a.log", body)
    result = detect_encoding(p)
    # utf-8 точно не подойдёт (0xFF в начале — невалидный start byte).
    # cp1251 байт-ориентированный — всегда декодирует. Detector вернёт его.
    assert result == "cp1251"


def test_fallback_on_io_error(tmp_path: Path) -> None:
    # Несуществующий файл — функция не падает, возвращает default
    missing = tmp_path / "missing.log"
    assert detect_encoding(missing) == "utf-8"


def test_sample_size_limits_read(tmp_path: Path) -> None:
    # BOM (3 байта) + ASCII текст. Если читать только prefix — utf-8-sig валиден.
    # При увеличенном sample_size прочитаются \xff байты, утф-8 упадёт.
    prefix = b"\xef\xbb\xbf47:02.139004-1,CALL,1,key=v\n"
    body = prefix + b"\xff" * 1000
    p = _write(tmp_path / "a.log", body)
    # sample_size = len(prefix) → читаем ровно валидную часть
    assert detect_encoding(p, sample_size=len(prefix)) == "utf-8-sig"
    # sample_size > len(prefix) → попадаем на \xff, fallback на cp1251
    assert detect_encoding(p, sample_size=len(prefix) + 10) == "cp1251"


def test_empty_file_defaults_to_utf8(tmp_path: Path) -> None:
    p = _write(tmp_path / "empty.log", b"")
    # Все candidates "успешно" декодируют пустой sample → возвращается первый из tuple.
    assert detect_encoding(p) == "utf-8-sig"
