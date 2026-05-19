"""Synthetic TDEADLOCK fixture для Sprint 3 Phase D acceptance.

В production-архиве Сергея (Phase 0 discovery) обнаружено 0 TDEADLOCK events,
поэтому real-data validation Phase D отложена в OPUS_HANDOVER follow-up.
Эта fixture создаёт минимальный DuckDB архив с 3 TDEADLOCK events
покрывающих типичные паттерны по ЦУП 2.12.3:

  1. ЦУП 2.12.3.2 — повышение уровня блокировки (Shared -> Exclusive)
     в одной транзакции: одна сессия читает с Shared lock, другая тоже
     с Shared lock, затем обе пытаются повысить до Exclusive → deadlock.

  2. ЦУП 2.12.3.3 — захват ресурсов в разном порядке: сессия A блокирует
     ресурс X затем ждёт Y; сессия B блокирует Y затем ждёт X.

  3. Один-ресурс deadlock между двумя процессами на одной таблице.

Schema полей в extra JSON — по ИТС спецификации:
  - Regions: "Имя.Объекта Mode, Имя.Другого.Объекта Mode2"
  - WaitConnections: "<id1>,<id2>"
  - DeadlockConnectionIntersections: "<id1>->Объект1 | <id2>->Объект2"
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb


SYNTHETIC_ARCHIVE_ID = "synthetic-tdeadlock-fixture"


def create_synthetic_tdeadlock_archive(db_path: Path) -> str:
    """Создаёт мини-DuckDB архив с 3 TDEADLOCK events + контекстные CALL/TLOCK.

    Returns: archive_id, который можно использовать в SQLExecutor для тестов.

    db_path: путь к .duckdb файлу. Будет перезаписан если существует.
    """
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    conn.execute(
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
            context_normalized VARCHAR,
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

    # Deadlock type 1 — повышение уровня блокировки (ЦУП 2.12.3.2)
    # Две сессии (1001, 1002) одновременно проводят документ Реализация,
    # обе берут Shared lock на Партии, затем пытаются повысить до Exclusive.
    dl1_extra = {
        "Regions": "РегистрНакопления.ПартииТоваровНаСкладах.Записи Exclusive",
        "WaitConnections": "1001,1002",
        "DeadlockConnectionIntersections": "1001->РегистрНакопления.ПартииТоваровНаСкладах.Записи | 1002->РегистрНакопления.ПартииТоваровНаСкладах.Записи",
        "usr": "ИвановИИ",
    }

    # Deadlock type 2 — захват в разном порядке (ЦУП 2.12.3.3)
    # Сессия 2001 захватила Документ.Реализация затем ждёт РегистрНакопления.Товары;
    # Сессия 2002 захватила РегистрНакопления.Товары затем ждёт Документ.Реализация.
    dl2_extra = {
        "Regions": (
            "Документ.РеализацияТоваровУслуг.Записи Exclusive, "
            "РегистрНакопления.ТоварыНаСкладах.Записи Exclusive"
        ),
        "WaitConnections": "2001,2002",
        "DeadlockConnectionIntersections": (
            "2001->РегистрНакопления.ТоварыНаСкладах.Записи | "
            "2002->Документ.РеализацияТоваровУслуг.Записи"
        ),
        "usr": "ПетровПП",
    }

    # Deadlock type 3 — один-ресурс между двумя процессами разных PID
    dl3_extra = {
        "Regions": "Справочник.Контрагенты.Ссылка Exclusive",
        "WaitConnections": "3001,3002",
        "DeadlockConnectionIntersections": "3001->Справочник.Контрагенты.Ссылка | 3002->Справочник.Контрагенты.Ссылка",
        "usr": "СидоровСС",
    }

    rows = [
        # === Deadlock 1: Реализация × 2 sessions, повышение блокировки ===
        # Окружающие CALL events до deadlock (контекст)
        (101, SYNTHETIC_ARCHIVE_ID, "2026-05-19 10:00:00", 5_000_000, "CALL",
         1001, "ИвановИИ", "Документ.РеализацияТоваровУслуг.МодульОбъекта : 12 : Записать()",
         "Документ.РеализацияТоваровУслуг.МодульОбъекта",
         "rphost-1", "rphost", 12044, None, None, None, None, None, None, "synthetic.log", 1),
        (102, SYNTHETIC_ARCHIVE_ID, "2026-05-19 10:00:01", 4_000_000, "CALL",
         1002, "ИвановИИ", "Документ.РеализацияТоваровУслуг.МодульОбъекта : 12 : Записать()",
         "Документ.РеализацияТоваровУслуг.МодульОбъекта",
         "rphost-1", "rphost", 12044, None, None, None, None, None, None, "synthetic.log", 2),
        # TLOCK на обеих сессиях (попытка повысить блокировку)
        (103, SYNTHETIC_ARCHIVE_ID, "2026-05-19 10:00:02", 3_000_000, "TLOCK",
         1001, "ИвановИИ", None, None,
         "rphost-1", "rphost", 12044, None, None, None, None, None,
         json.dumps({"Regions": "РегистрНакопления.ПартииТоваровНаСкладах.Записи Exclusive", "WaitConnections": "1002"}),
         "synthetic.log", 3),
        # TDEADLOCK — finale
        (104, SYNTHETIC_ARCHIVE_ID, "2026-05-19 10:00:03", 5_000, "TDEADLOCK",
         1001, "ИвановИИ", None, None,
         "rphost-1", "rphost", 12044, None, None, None, None, None,
         json.dumps(dl1_extra), "synthetic.log", 4),

        # === Deadlock 2: Реализация vs Товары, захват в разном порядке ===
        (201, SYNTHETIC_ARCHIVE_ID, "2026-05-19 11:00:00", 2_000_000, "CALL",
         2001, "ПетровПП", "Документ.РеализацияТоваровУслуг.МодульОбъекта : 25 : ОбработкаПроведения()",
         "Документ.РеализацияТоваровУслуг.МодульОбъекта",
         "rphost-2", "rphost", 12044, None, None, None, None, None, None, "synthetic.log", 10),
        (202, SYNTHETIC_ARCHIVE_ID, "2026-05-19 11:00:00", 2_000_000, "CALL",
         2002, "ПетровПП", "Документ.ПоступлениеТоваровУслуг.МодульОбъекта : 25 : ОбработкаПроведения()",
         "Документ.ПоступлениеТоваровУслуг.МодульОбъекта",
         "rphost-2", "rphost", 12044, None, None, None, None, None, None, "synthetic.log", 11),
        (203, SYNTHETIC_ARCHIVE_ID, "2026-05-19 11:00:02", 8_000, "TDEADLOCK",
         2001, "ПетровПП", None, None,
         "rphost-2", "rphost", 12044, None, None, None, None, None,
         json.dumps(dl2_extra), "synthetic.log", 12),

        # === Deadlock 3: Контрагенты ===
        (301, SYNTHETIC_ARCHIVE_ID, "2026-05-19 12:00:00", 1_000_000, "CALL",
         3001, "СидоровСС", "Справочник.Контрагенты.МодульМенеджера : 5 : ОбновитьСсылку()",
         "Справочник.Контрагенты.МодульМенеджера",
         "rphost-3", "rphost", 13780, None, None, None, None, None, None, "synthetic.log", 20),
        (302, SYNTHETIC_ARCHIVE_ID, "2026-05-19 12:00:01", 6_000, "TDEADLOCK",
         3001, "СидоровСС", None, None,
         "rphost-3", "rphost", 13780, None, None, None, None, None,
         json.dumps(dl3_extra), "synthetic.log", 21),
    ]

    conn.executemany(
        "INSERT INTO events VALUES (" + ",".join(["?"] * 20) + ")", rows
    )
    conn.close()
    return SYNTHETIC_ARCHIVE_ID


def deadlock_event_ids() -> list[int]:
    """ID трёх синтетических TDEADLOCK events для acceptance tests."""
    return [104, 203, 302]
