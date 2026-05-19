"""Sprint 3 Phase A — нормализация поля Context.

Нормализация выделяет 'Тип.Имя.Сущность' префикс до первого ':',
отбрасывая '<line> : <statement>' хвост. Это семантический ключ
для group by в Top Business Operations view.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import duckdb
import pytest

from optimyzer_backend.parsers.tj_parser import (
    ParsedEvent,
    interpret,
    iter_raw_events,
    normalize_context,
)
from optimyzer_backend.storage.duckdb_store import DuckDBStore


# ---------- normalize_context unit tests ----------


def test_normalize_context_none() -> None:
    assert normalize_context(None) is None


def test_normalize_context_empty() -> None:
    assert normalize_context("") is None
    assert normalize_context("   ") is None


def test_normalize_context_no_colon() -> None:
    assert normalize_context("Документ.РеализацияТоваровУслуг.МодульОбъекта") == \
        "Документ.РеализацияТоваровУслуг.МодульОбъекта"


def test_normalize_context_with_line_statement() -> None:
    raw = "Документ.РеализацияТоваровУслуг.МодульОбъекта : 123 : Result = DoPortionPostAtServer()"
    assert normalize_context(raw) == "Документ.РеализацияТоваровУслуг.МодульОбъекта"


def test_normalize_context_form_module_path() -> None:
    raw = "ВнешняяОбработка.StandardDocumentsPosting.Форма.MainForm.Форма : 546 : Result = X"
    assert normalize_context(raw) == "ВнешняяОбработка.StandardDocumentsPosting.Форма.MainForm.Форма"


def test_normalize_context_report_module() -> None:
    raw = "Отчёт.ОборотноСальдоваяВедомость.МодульМенеджера : 12 : Foo()"
    assert normalize_context(raw) == "Отчёт.ОборотноСальдоваяВедомость.МодульМенеджера"


def test_normalize_context_leading_whitespace() -> None:
    raw = "   Документ.Foo.МодульОбъекта   :   42 : DoStuff()"
    assert normalize_context(raw) == "Документ.Foo.МодульОбъекта"


def test_normalize_context_multiple_colons() -> None:
    # Только до первого ':' — последующие части остаются в statement и отбрасываются
    raw = "Документ.Foo.МодульОбъекта : 1 : x = a:b"
    assert normalize_context(raw) == "Документ.Foo.МодульОбъекта"


def test_normalize_context_trailing_whitespace_in_prefix() -> None:
    raw = "Документ.Foo.МодульОбъекта  : 1 : ..."
    assert normalize_context(raw) == "Документ.Foo.МодульОбъекта"


def test_normalize_context_newlines_in_context() -> None:
    raw = "Документ.Foo.МодульОбъекта : 1 : line1\nline2"
    assert normalize_context(raw) == "Документ.Foo.МодульОбъекта"


# ---------- interpret() populates context_normalized ----------


def test_interpret_populates_context_normalized() -> None:
    text = (
        "00:01.100000-2000,CALL,3,"
        "process=rphost,"
        "Context='Документ.РеализацияТоваровУслуг.МодульОбъекта : 123 : Foo()'"
    )
    raw = next(iter(iter_raw_events(text, "test.log")))
    ev = interpret(raw, file_ts=(2026, 5, 17, 18))
    assert ev.context == "Документ.РеализацияТоваровУслуг.МодульОбъекта : 123 : Foo()"
    assert ev.context_normalized == "Документ.РеализацияТоваровУслуг.МодульОбъекта"


def test_interpret_no_context_means_no_normalized() -> None:
    text = "00:01.100000-2000,CALL,3,process=rphost,OSThread=1"
    raw = next(iter(iter_raw_events(text, "test.log")))
    ev = interpret(raw, file_ts=(2026, 5, 17, 18))
    assert ev.context is None
    assert ev.context_normalized is None


# ---------- as_row tuple positional integrity ----------


def test_as_row_includes_context_normalized() -> None:
    ev = ParsedEvent(
        ts=__import__("datetime").datetime(2026, 5, 17, 18, 0, 1),
        duration_us=1000,
        event_type="CALL",
        level=3,
        context="Документ.Foo.МодульОбъекта : 1 : x",
        context_normalized="Документ.Foo.МодульОбъекта",
    )
    row = ev.as_row("test-archive", 42)
    # Колонка context — idx 7, context_normalized — idx 8 (см. EVENT_COLUMNS)
    assert row[7] == "Документ.Foo.МодульОбъекта : 1 : x"
    assert row[8] == "Документ.Foo.МодульОбъекта"


# ---------- migration smoke: fresh archive has column + index ----------


def test_fresh_archive_has_context_normalized_column() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "fresh.duckdb"
        store = DuckDBStore("arc-fresh", db_path=db)
        conn = store.open()
        cols = {row[1] for row in conn.execute("PRAGMA table_info('events')").fetchall()}
        assert "context_normalized" in cols
        # Index created
        idx_rows = conn.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'events'"
        ).fetchall()
        idx_names = {r[0] for r in idx_rows}
        assert "idx_events_ctx_norm" in idx_names
        store.close()


def test_migration_on_legacy_archive_backfills_existing_rows() -> None:
    """Симулируем legacy архив без колонки context_normalized — миграция
    должна добавить колонку и заполнить её для existing rows."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "legacy.duckdb"
        # Создаём legacy-схему вручную (без context_normalized)
        legacy_conn = duckdb.connect(str(db))
        legacy_conn.execute(
            """
            CREATE TABLE events (
                id BIGINT NOT NULL,
                archive_id VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                duration_us BIGINT,
                event_type VARCHAR NOT NULL,
                session_id INTEGER,
                user_name VARCHAR,
                context VARCHAR,
                process VARCHAR,
                process_role VARCHAR,
                process_pid INTEGER,
                sql_text TEXT,
                sql_text_normalized TEXT,
                sql_text_hash VARCHAR(32),
                rows_read BIGINT,
                rows_modified BIGINT,
                extra JSON,
                source_file VARCHAR,
                source_line_start INTEGER
            )
            """
        )
        legacy_conn.execute(
            """
            INSERT INTO events VALUES
                (1, 'arc-legacy', TIMESTAMP '2026-05-17 18:00:01', 1000, 'CALL',
                 NULL, NULL, 'Документ.Реал.МодульОбъекта : 1 : DoStuff()', NULL, 'rphost', NULL,
                 NULL, NULL, NULL, NULL, NULL, NULL, 'f.log', 1),
                (2, 'arc-legacy', TIMESTAMP '2026-05-17 18:00:02', 2000, 'CALL',
                 NULL, NULL, 'Отчёт.OSV.МодульМенеджера', NULL, 'rphost', NULL,
                 NULL, NULL, NULL, NULL, NULL, NULL, 'f.log', 2),
                (3, 'arc-legacy', TIMESTAMP '2026-05-17 18:00:03', 500, 'CONN',
                 NULL, NULL, NULL, NULL, 'rphost', NULL,
                 NULL, NULL, NULL, NULL, NULL, NULL, 'f.log', 3)
            """
        )
        legacy_conn.close()

        # Открываем через DuckDBStore — миграция должна сработать
        store = DuckDBStore("arc-legacy", db_path=db)
        conn = store.open()
        cols = {row[1] for row in conn.execute("PRAGMA table_info('events')").fetchall()}
        assert "context_normalized" in cols
        rows = conn.execute(
            "SELECT id, context, context_normalized FROM events ORDER BY id"
        ).fetchall()
        assert rows[0][2] == "Документ.Реал.МодульОбъекта"
        assert rows[1][2] == "Отчёт.OSV.МодульМенеджера"
        assert rows[2][2] is None  # context was NULL
        store.close()


def test_migration_idempotent_second_open() -> None:
    """Открыть архив дважды подряд — миграция должна быть no-op во второй раз."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "twice.duckdb"
        s1 = DuckDBStore("arc-twice", db_path=db)
        s1.open()
        s1.close()
        # Повторное открытие — ничего не должно ломаться
        s2 = DuckDBStore("arc-twice", db_path=db)
        conn = s2.open()
        cols = {row[1] for row in conn.execute("PRAGMA table_info('events')").fetchall()}
        assert "context_normalized" in cols
        s2.close()


# ---------- end-to-end: bulk_insert preserves context_normalized ----------


def test_bulk_insert_writes_context_normalized() -> None:
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "bulk.duckdb"
        store = DuckDBStore("arc-bulk", db_path=db)
        store.open()
        events = [
            ParsedEvent(
                ts=datetime(2026, 5, 17, 18, 0, 1),
                duration_us=1000,
                event_type="CALL",
                level=3,
                context="Документ.Foo.МодульОбъекта : 1 : x()",
                context_normalized="Документ.Foo.МодульОбъекта",
            )
        ]
        n = store.bulk_insert(events)
        assert n == 1
        rows = store.open().execute(
            "SELECT context, context_normalized FROM events"
        ).fetchall()
        assert rows[0][0] == "Документ.Foo.МодульОбъекта : 1 : x()"
        assert rows[0][1] == "Документ.Foo.МодульОбъекта"
        store.close()
