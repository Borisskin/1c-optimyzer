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
