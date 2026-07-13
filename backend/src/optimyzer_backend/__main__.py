"""JSON-RPC entry point. Читает запросы из stdin, пишет ответы в stdout, логи — в stderr."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from optimyzer_backend.rpc.dispatcher import Dispatcher
from optimyzer_backend.rpc import handlers  # noqa: F401  — регистрирует методы
from optimyzer_backend.rpc import sql_rpc  # noqa: F401  — регистрирует SQL RPC
from optimyzer_backend.rpc import views_rpc  # noqa: F401  — pre-built views
from optimyzer_backend.rpc import comparison_rpc  # noqa: F401  — multi-archive compare
from optimyzer_backend.rpc import explainer_rpc  # noqa: F401  — Sprint 3 explainer
from optimyzer_backend.rpc import query_analyzer_rpc  # noqa: F401  — Sprint 4 query analyzer
from optimyzer_backend.rpc import configuration_rpc  # noqa: F401  — Sprint 5 configuration metadata
from optimyzer_backend.rpc import bsl_ls_rpc  # noqa: F401  — Sprint 6 bsl-LS adapter
from optimyzer_backend.rpc import plan_analyzer_rpc  # noqa: F401  — Sprint 7 Plan Analyzer
from optimyzer_backend.rpc import pg_rpc  # noqa: F401  — Sprint 8 Phase B PG connections + re-EXPLAIN
from optimyzer_backend.rpc import sql_antipatterns_rpc  # noqa: F401  — Sprint 8 Phase C SQL antipatterns
from optimyzer_backend.rpc import logcfg_rpc  # noqa: F401  — Sprint 10 TJ Config Builder
from optimyzer_backend.rpc import regression_rpc  # noqa: F401  — Sprint 11 Phase E Performance Regression


def _err(code: int, message: str, request_id: Any = None, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": err}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> int:
    _log(f"[optimyzer-backend] started, python={sys.version.split()[0]}")

    try:
        disp = Dispatcher.default()
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as e:
                resp = _err(-32700, f"Parse error: {e}")
                _write(resp)
                continue

            resp = disp.handle(req)
            if resp is not None:
                _write(resp)
    except KeyboardInterrupt:
        _log("[optimyzer-backend] interrupt, shutting down")
        return 0
    except Exception:
        _log("[optimyzer-backend] fatal: " + traceback.format_exc())
        return 1
    return 0


def _write(resp: dict) -> None:
    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
