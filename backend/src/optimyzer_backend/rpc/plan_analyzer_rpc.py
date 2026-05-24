"""RPC методы для Plan Analyzer (Sprint 7 Phase A).

Public RPC:
    plan_analyzer.analyze_file(file_path)
        → анализ .sqlplan файла через PerformanceStudio CLI
    plan_analyzer.analyze_xml(plan_xml)
        → анализ plan XML переданного напрямую (paste из SSMS, текст и т.д.)
    plan_analyzer.status()
        → доступность binary, версия, fallback info

Шаблон взят из bsl_ls_rpc.py (Sprint 6 Phase C): graceful error reporting,
вся работа через subprocess в planview.cli.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from optimyzer_backend.planview import cli as planview_cli
from optimyzer_backend.planview.cli import (
    PlanviewBinaryNotFoundError,
    PlanviewError,
    PlanviewInvalidOutputError,
    PlanviewTimeoutError,
)
from optimyzer_backend.rpc.dispatcher import rpc
from optimyzer_backend.rpc.handlers import _ARCHIVES
from optimyzer_backend.storage.duckdb_store import get_active_connection

logger = logging.getLogger(__name__)


def _binary_status() -> dict[str, Any]:
    """Helper: текущее состояние planview binary для status_rpc."""
    path = planview_cli.get_binary_path()
    return {
        "available": path is not None,
        "binary_path": str(path) if path else None,
    }


@rpc("plan_analyzer.analyze_file")
def analyze_file_rpc(file_path: str, warnings_only: bool = False) -> dict[str, Any]:
    """Анализирует .sqlplan файл через PerformanceStudio CLI.

    Args:
        file_path: абсолютный путь к существующему .sqlplan
        warnings_only: skip operator_tree (быстрее, меньше JSON)
    """
    if not isinstance(file_path, str) or not file_path.strip():
        return {"ok": False, "error": "invalid_file_path", "details": "file_path must be non-empty string"}

    path = Path(file_path)
    if not path.is_file():
        return {
            "ok": False,
            "error": "file_not_found",
            "details": f"План не найден: {file_path}",
        }

    try:
        result = planview_cli.analyze_plan_file(path, warnings_only=warnings_only)
    except PlanviewBinaryNotFoundError as e:
        return {
            "ok": False,
            "error": "planview_binary_missing",
            "details": str(e),
            "hint": "Запустите scripts/setup-planview-binary.ps1 или соберите CLI вручную",
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": "file_not_found", "details": str(e)}
    except PlanviewTimeoutError as e:
        return {"ok": False, "error": "planview_timeout", "details": str(e)}
    except PlanviewInvalidOutputError as e:
        return {"ok": False, "error": "planview_invalid_output", "details": str(e)}
    except PlanviewError as e:
        return {"ok": False, "error": "planview_failed", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("Неожиданная ошибка анализа плана")
        return {"ok": False, "error": "unexpected", "details": str(e)}

    return {
        "ok": True,
        "result": result.model_dump(mode="json"),
        "file_name": path.name,
    }


@rpc("plan_analyzer.analyze_xml")
def analyze_xml_rpc(plan_xml: str, warnings_only: bool = False) -> dict[str, Any]:
    """Анализирует plan XML через `planview analyze --stdin`.

    Используется когда юзер делает paste из SSMS Plan Viewer или загрузил
    архив ТЖ с DBMSSQL.Plan событиями (Phase D).
    """
    if not isinstance(plan_xml, str):
        return {"ok": False, "error": "invalid_xml", "details": "plan_xml must be string"}

    if not plan_xml.strip():
        return {"ok": False, "error": "empty_xml", "details": "plan_xml пустой"}

    try:
        result = planview_cli.analyze_plan_xml(plan_xml, warnings_only=warnings_only)
    except PlanviewBinaryNotFoundError as e:
        return {
            "ok": False,
            "error": "planview_binary_missing",
            "details": str(e),
            "hint": "Запустите scripts/setup-planview-binary.ps1",
        }
    except ValueError as e:
        return {"ok": False, "error": "invalid_xml", "details": str(e)}
    except PlanviewTimeoutError as e:
        return {"ok": False, "error": "planview_timeout", "details": str(e)}
    except PlanviewInvalidOutputError as e:
        return {"ok": False, "error": "planview_invalid_output", "details": str(e)}
    except PlanviewError as e:
        return {"ok": False, "error": "planview_failed", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("Неожиданная ошибка анализа plan XML")
        return {"ok": False, "error": "unexpected", "details": str(e)}

    return {
        "ok": True,
        "result": result.model_dump(mode="json"),
        "file_name": "stdin",
    }


@rpc("plan_analyzer.status")
def status_rpc() -> dict[str, Any]:
    """Состояние PerformanceStudio binary + версия."""
    status = _binary_status()
    return {
        "ok": True,
        **status,
        "version": "PerformanceStudio 1.11.2 (Erik Darling Data)",
        "rules_count": 30,
    }


# ============== Sprint 7 Phase D — Import from TJ archive ==============


def _check_archive_ready(archive_id: str) -> dict[str, Any] | None:
    """Возвращает error-dict если архив не загружен/не готов, иначе None."""
    state = _ARCHIVES.get(archive_id)
    if state is None:
        return {"ok": False, "error": "archive_not_loaded", "details": f"Архив {archive_id} не загружен"}
    if state.get("status") != "ready":
        return {
            "ok": False,
            "error": "archive_not_ready",
            "details": f"Архив {archive_id} ещё не готов (status={state.get('status')})",
        }
    return None


@rpc("plan_analyzer.list_tj_plans")
def list_tj_plans_rpc(
    archive_id: str,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Список DBMSSQL событий из архива, у которых заполнен plan_text.

    Используется UI tab «Из архива ТЖ» для показа доступных планов запросов
    с возможностью клика для импорта в Plan Analyzer.

    Returns:
        {ok: True, items: [{event_id, ts, duration_us, sql_preview, plan_size_bytes, context}, ...],
         total, has_planSQLText}
        ok: False если архив не готов / DB connection потеряна.
    """
    err = _check_archive_ready(archive_id)
    if err:
        return err

    conn = get_active_connection(archive_id)
    if conn is None:
        return {"ok": False, "error": "no_connection", "details": "DuckDB connection не активен"}

    cur = conn.cursor()
    try:
        # Сначала проверим — а есть ли вообще planSQLText в архиве. Если нет —
        # вернём пустой items + флаг для UI чтобы показать banner с инструкцией.
        total_row = cur.execute(
            "SELECT COUNT(*) FROM events WHERE archive_id = ? AND plan_text IS NOT NULL AND plan_text <> ''",
            [archive_id],
        ).fetchone()
        total = int(total_row[0]) if total_row else 0
        if total == 0:
            return {
                "ok": True,
                "items": [],
                "total": 0,
                "has_planSQLText": False,
            }

        # Возвращаем preview SQL (первые 200 символов) для UI list — full sql
        # подгружается через get_tj_plan по клику.
        rows = cur.execute(
            """
            SELECT
                id,
                ts,
                duration_us,
                substr(sql_text, 1, 200) AS sql_preview,
                length(plan_text) AS plan_size,
                COALESCE(context_normalized, context) AS context
            FROM events
            WHERE archive_id = ?
              AND plan_text IS NOT NULL
              AND plan_text <> ''
            ORDER BY duration_us DESC NULLS LAST, ts DESC
            LIMIT ? OFFSET ?
            """,
            [archive_id, limit, offset],
        ).fetchall()
    finally:
        cur.close()

    items = [
        {
            "event_id": int(r[0]),
            "ts": r[1].isoformat() if r[1] else None,
            "duration_us": int(r[2]) if r[2] is not None else None,
            "sql_preview": r[3] or "",
            "plan_size_bytes": int(r[4]) if r[4] is not None else 0,
            "context": r[5],
        }
        for r in rows
    ]
    return {
        "ok": True,
        "items": items,
        "total": total,
        "has_planSQLText": True,
    }


@rpc("plan_analyzer.get_tj_plan")
def get_tj_plan_rpc(archive_id: str, event_id: int) -> dict[str, Any]:
    """Возвращает полные данные одного DBMSSQL события с планом.

    Используется при клике на строку в списке tab «Из архива ТЖ» —
    UI получает sql_text + plan_text для отображения и AI-анализа.
    """
    err = _check_archive_ready(archive_id)
    if err:
        return err

    conn = get_active_connection(archive_id)
    if conn is None:
        return {"ok": False, "error": "no_connection", "details": "DuckDB connection не активен"}

    cur = conn.cursor()
    try:
        row = cur.execute(
            """
            SELECT sql_text, plan_text, ts, duration_us,
                   COALESCE(context_normalized, context) AS context
            FROM events
            WHERE archive_id = ? AND id = ?
            LIMIT 1
            """,
            [archive_id, event_id],
        ).fetchone()
    finally:
        cur.close()

    if row is None:
        return {"ok": False, "error": "event_not_found", "details": f"Событие id={event_id} не найдено"}

    sql_text, plan_text, ts, duration_us, context = row
    if not plan_text:
        return {
            "ok": False,
            "error": "no_plan_text",
            "details": "У этого события нет plan_text — возможно logcfg.xml без <plan/>",
        }

    return {
        "ok": True,
        "event_id": event_id,
        "sql_text": sql_text or "",
        "plan_text": plan_text,
        "ts": ts.isoformat() if ts else None,
        "duration_us": int(duration_us) if duration_us is not None else None,
        "context": context,
    }
