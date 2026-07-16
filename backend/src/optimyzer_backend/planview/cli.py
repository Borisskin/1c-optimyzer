"""PerformanceStudio CLI subprocess wrapper (Sprint 7 Phase A).

Главный entry point — analyze_plan_file/xml. Внутри:
  1. Resolve путь к planview.exe (bundled или dev-fallback)
  2. Запуск subprocess с timeout
  3. Parse JSON stdout в PlanAnalysisResult

Если бинарь недоступен (binary не скачан, или dev-mode без bundle) —
raises PlanviewBinaryNotFoundError. RPC уровень ловит это и возвращает
graceful error для UI.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .models import PlanAnalysisResult

logger = logging.getLogger(__name__)


class PlanviewError(RuntimeError):
    """Базовая ошибка обёртки."""


class PlanviewBinaryNotFoundError(PlanviewError):
    """planview.exe не найден ни в bundled, ни в dev-fallback location."""


class PlanviewTimeoutError(PlanviewError):
    """Анализ занял больше чем timeout_seconds."""


class PlanviewInvalidOutputError(PlanviewError):
    """JSON output от planview не распарсился."""


# Глобально кешируем путь к binary — чтобы не resolve'ить на каждый вызов.
# Сбрасывается через reset_binary_cache() (тесты).
_BINARY_PATH: Optional[Path] = None
_BINARY_CHECKED: bool = False


def _candidate_paths() -> list[Path]:
    """Кандидаты на расположение planview.exe в priority order.

    1. ENV `OPTIMYZER_PLANVIEW_EXE` — override для tests / debug
    2. Bundled resource (production): задаётся через ENV
       `OPTIMYZER_PLANVIEW_BUNDLED_PATH` от Tauri sidecar at startup
    3. Production self-relative: sidecar-exe лежит в <install>/binaries/backend/,
       planview — рядом, в <install>/binaries/planview/. Не зависит от ENV,
       поэтому работает даже если Tauri его не передал.
    4. Dev fallback — собранный CLI в research/PerformanceStudio/...
    5. Dev fallback — в frontend/src-tauri/binaries/planview/ (если уже скачан)
    """
    out: list[Path] = []
    env_override = os.environ.get("OPTIMYZER_PLANVIEW_EXE")
    if env_override:
        out.append(Path(env_override))

    bundled_env = os.environ.get("OPTIMYZER_PLANVIEW_BUNDLED_PATH")
    if bundled_env:
        out.append(Path(bundled_env))

    # Production (PyInstaller frozen): ищем бинарь относительно самого sidecar-exe.
    # Раскладка инсталлятора: <install>/binaries/backend/optimyzer_backend.exe
    #                        <install>/binaries/planview/planview.exe
    if getattr(sys, "frozen", False):
        try:
            backend_dir = Path(sys.executable).resolve().parent
            out.append(backend_dir.parent / "planview" / "planview.exe")
        except (OSError, IndexError):
            pass

    # Repo-relative fallback (dev).
    # backend/src/optimyzer_backend/planview/cli.py → 5 уровней до repo root.
    try:
        repo_root = Path(__file__).resolve().parents[4]
        out.extend(
            [
                repo_root / "frontend" / "src-tauri" / "binaries" / "planview" / "planview.exe",
                repo_root / "research" / "PerformanceStudio" / "src" / "PlanViewer.Cli"
                / "bin" / "Release" / "net10.0" / "win-x64" / "publish" / "planview.exe",
                repo_root / "research" / "PerformanceStudio" / "src" / "PlanViewer.Cli"
                / "bin" / "Release" / "net10.0" / "planview.exe",
                repo_root / "research" / "PerformanceStudio" / "src" / "PlanViewer.Cli"
                / "bin" / "Debug" / "net10.0" / "planview.exe",
            ]
        )
    except IndexError:
        pass

    return out


def reset_binary_cache() -> None:
    """Сбрасывает кеш _BINARY_PATH — используется в тестах."""
    global _BINARY_PATH, _BINARY_CHECKED
    _BINARY_PATH = None
    _BINARY_CHECKED = False


def get_binary_path() -> Optional[Path]:
    """Возвращает путь к planview.exe или None если не найден."""
    global _BINARY_PATH, _BINARY_CHECKED
    if _BINARY_CHECKED:
        return _BINARY_PATH

    for candidate in _candidate_paths():
        if candidate.is_file():
            _BINARY_PATH = candidate
            _BINARY_CHECKED = True
            logger.info("planview binary resolved: %s", candidate)
            return candidate

    _BINARY_PATH = None
    _BINARY_CHECKED = True
    logger.warning("planview binary НЕ найден. Кандидаты: %s", _candidate_paths())
    return None


def is_available() -> bool:
    """True если planview.exe найден и executable."""
    return get_binary_path() is not None


def _require_binary() -> Path:
    """Raises PlanviewBinaryNotFoundError если бинарь недоступен."""
    path = get_binary_path()
    if path is None:
        raise PlanviewBinaryNotFoundError(
            "planview.exe не найден. Запустите scripts/setup-planview-binary.ps1 "
            "или соберите CLI из research/PerformanceStudio/src/PlanViewer.Cli/ "
            "(требуется .NET 10 SDK)."
        )
    return path


def _parse_output(raw_stdout: str, source_label: str) -> PlanAnalysisResult:
    """Парсит JSON stdout от planview в PlanAnalysisResult."""
    try:
        data = json.loads(raw_stdout)
    except json.JSONDecodeError as e:
        snippet = raw_stdout[:200].replace("\n", " ")
        raise PlanviewInvalidOutputError(
            f"planview output не JSON: {e}. Начало: {snippet!r}"
        ) from e

    try:
        return PlanAnalysisResult(**data)
    except Exception as e:  # pydantic.ValidationError
        raise PlanviewInvalidOutputError(
            f"planview output не соответствует схеме PlanAnalysisResult: {e}"
        ) from e


def analyze_plan_file(
    sqlplan_path: Path | str,
    *,
    timeout_seconds: int = 60,
    warnings_only: bool = False,
) -> PlanAnalysisResult:
    """Анализирует .sqlplan файл через `planview analyze <file> --output json`.

    Args:
        sqlplan_path: путь к существующему .sqlplan
        timeout_seconds: subprocess timeout (default 60)
        warnings_only: skip operator_tree (faster output, smaller JSON)

    Returns:
        PlanAnalysisResult с statements, warnings, missing_indexes, operator_tree

    Raises:
        FileNotFoundError если sqlplan_path не существует
        PlanviewBinaryNotFoundError если planview.exe отсутствует
        PlanviewTimeoutError если subprocess завис
        PlanviewError если exit code != 0 (PerformanceStudio внутренняя ошибка)
        PlanviewInvalidOutputError если JSON parse failed
    """
    p = Path(sqlplan_path)
    if not p.is_file():
        raise FileNotFoundError(f"План не найден: {p}")

    binary = _require_binary()

    args = [str(binary), "analyze", str(p), "--output", "json"]
    if warnings_only:
        args.append("--warnings-only")

    logger.debug("planview cmd: %s", " ".join(args))

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise PlanviewTimeoutError(
            f"planview таймаут после {timeout_seconds}s на {p.name}"
        ) from e

    if result.returncode != 0:
        stderr_snip = (result.stderr or "")[:500]
        raise PlanviewError(
            f"planview exit {result.returncode} на {p.name}: {stderr_snip}"
        )

    return _parse_output(result.stdout, p.name)


def analyze_plan_xml(
    plan_xml: str,
    *,
    timeout_seconds: int = 60,
    warnings_only: bool = False,
) -> PlanAnalysisResult:
    """Анализирует plan XML напрямую через `planview analyze --stdin --output json`.

    Args:
        plan_xml: SHOWPLAN XML (полный <ShowPlanXML>...</ShowPlanXML>)
        timeout_seconds: subprocess timeout (default 60)
        warnings_only: skip operator_tree

    Returns:
        PlanAnalysisResult

    Raises: см. analyze_plan_file
    """
    if not plan_xml or not plan_xml.strip():
        raise ValueError("plan_xml пустой")

    binary = _require_binary()

    args = [str(binary), "analyze", "--stdin", "--output", "json"]
    if warnings_only:
        args.append("--warnings-only")

    logger.debug("planview cmd (stdin): %s", " ".join(args))

    try:
        result = subprocess.run(
            args,
            input=plan_xml,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise PlanviewTimeoutError(
            f"planview таймаут после {timeout_seconds}s (stdin mode)"
        ) from e

    if result.returncode != 0:
        stderr_snip = (result.stderr or "")[:500]
        raise PlanviewError(f"planview exit {result.returncode} (stdin): {stderr_snip}")

    return _parse_output(result.stdout, "stdin")
