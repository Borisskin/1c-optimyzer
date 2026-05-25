"""Sprint 8 Phase B — RPC методы для PG connections + re-EXPLAIN.

Public RPC:
    pg.list_connections()       → список PG connections (без password)
    pg.add_connection(...)      → создать новый
    pg.delete_connection(id)    → удалить
    pg.test_connection_form(...) → проверить unsaved credentials (для формы Add)
    pg.test_connection(id)      → проверить уже сохранённый
    pg.set_default(id)          → пометить как default

    plan_analyzer.re_explain(sql, connection_id?)
        → backend.re_explain_safe()
        → JSON план для pev2 visualization
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from optimyzer_backend.pg.connections import (
    ConnectionNotFoundError,
    KeychainUnavailableError,
    PgConnectionStore,
)
from optimyzer_backend.pg.re_explain import (
    NoDefaultConnectionError,
    ReExplainError,
    ping_connection as ping_pg_connection_async,
    re_explain_safe,
)
from optimyzer_backend.pg.safety import UnsafeQueryError
from optimyzer_backend.rpc.dispatcher import rpc

logger = logging.getLogger(__name__)


# Singleton store — открываем SQLite по дефолтному пути. В тестах monkeypatch
# через _get_store() helper или передачей store=... в re_explain_safe().
_store: PgConnectionStore | None = None


def _get_store() -> PgConnectionStore:
    global _store
    if _store is None:
        _store = PgConnectionStore()
    return _store


def _reset_store_for_tests(store: PgConnectionStore | None) -> None:
    """Только для тестов — заменить singleton."""
    global _store
    _store = store


@rpc("pg.list_connections")
def list_connections_rpc() -> dict[str, Any]:
    """Список всех PG connections (без password). Sprint 8 Phase B."""
    try:
        items = _get_store().list_all()
        return {
            "ok": True,
            "items": [i.to_dict() for i in items],
            "total": len(items),
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("pg.list_connections failed")
        return {"ok": False, "error": "list_failed", "details": str(e)}


@rpc("pg.add_connection")
def add_connection_rpc(
    name: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> dict[str, Any]:
    """Создать новое PG connection. Password сохраняется в OS keychain."""
    # Validation.
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "invalid_name", "details": "name пустой"}
    if not isinstance(host, str) or not host.strip():
        return {"ok": False, "error": "invalid_host", "details": "host пустой"}
    if not isinstance(port, int) or not (1 <= port <= 65535):
        return {"ok": False, "error": "invalid_port", "details": "port должен быть 1..65535"}
    if not isinstance(database, str) or not database.strip():
        return {"ok": False, "error": "invalid_database", "details": "database пустая"}
    if not isinstance(username, str) or not username.strip():
        return {"ok": False, "error": "invalid_username", "details": "username пустой"}
    # Password может быть любой строкой включая пустую — 1С dev баз с trust auth
    # допускают пустой пароль. Не валидируем здесь.

    try:
        conn = _get_store().add(
            name=name.strip(),
            host=host.strip(),
            port=port,
            database=database.strip(),
            username=username.strip(),
            password=password,
        )
        return {"ok": True, "connection": conn.to_dict()}
    except KeychainUnavailableError as e:
        return {"ok": False, "error": "keychain_unavailable", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("pg.add_connection failed")
        return {"ok": False, "error": "add_failed", "details": str(e)}


@rpc("pg.delete_connection")
def delete_connection_rpc(connection_id: int) -> dict[str, Any]:
    """Удалить connection (и из SQLite, и из keychain)."""
    try:
        _get_store().delete(int(connection_id))
        return {"ok": True}
    except ConnectionNotFoundError as e:
        return {"ok": False, "error": "not_found", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("pg.delete_connection failed")
        return {"ok": False, "error": "delete_failed", "details": str(e)}


@rpc("pg.set_default")
def set_default_rpc(connection_id: int) -> dict[str, Any]:
    """Пометить connection как default (используется когда юзер не передал ID явно)."""
    try:
        _get_store().set_default(int(connection_id))
        return {"ok": True}
    except ConnectionNotFoundError as e:
        return {"ok": False, "error": "not_found", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("pg.set_default failed")
        return {"ok": False, "error": "set_default_failed", "details": str(e)}


@rpc("pg.test_connection")
def test_connection_rpc(connection_id: int) -> dict[str, Any]:
    """Тест уже сохранённого connection — читаем password из keychain, пробуем connect."""
    try:
        store = _get_store()
        conn = store._get_or_raise(int(connection_id))
        password = store.get_password(int(connection_id))
    except ConnectionNotFoundError as e:
        return {"ok": False, "error": "not_found", "details": str(e)}
    except KeychainUnavailableError as e:
        return {"ok": False, "error": "keychain_unavailable", "details": str(e)}

    return _run_async(
        ping_pg_connection_async(
            host=conn.host,
            port=conn.port,
            database=conn.database,
            username=conn.username,
            password=password,
        )
    )


@rpc("pg.test_connection_form")
def test_connection_form_rpc(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> dict[str, Any]:
    """Тест unsaved credentials — для формы Add Connection (до сохранения).

    Не пишет ни в SQLite, ни в keychain. Проверяет что соединение работает.
    """
    return _run_async(
        ping_pg_connection_async(
            host=host,
            port=int(port),
            database=database,
            username=username,
            password=password,
        )
    )


@rpc("plan_analyzer.re_explain")
def plan_analyzer_re_explain_rpc(
    sql: str,
    connection_id: int | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Re-execute EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE) для given SQL.

    Args:
        sql: SQL запрос (должен быть SELECT/WITH).
        connection_id: ID PG connection. Если None — используется default.
        timeout_seconds: таймаут на весь EXPLAIN.

    Returns:
        {"ok": True, "plan_json": "[{...}]", "engine": "postgres"} — план как JSON string
        {"ok": False, "error": "...", "details": "..."}

    plan_json — это JSON-string чтобы UI мог передать его напрямую в pev2 (он
    ожидает string). Backend парсит и заново сериализует — гарантирует валидность.
    """
    try:
        store = _get_store()
        if connection_id is None:
            default = store.get_default()
            if default is None:
                return {
                    "ok": False,
                    "error": "no_default_connection",
                    "details": "Не указан connection_id и нет default PG connection. Создайте в Настройках.",
                }
            connection_id = default.id

        plan = _run_async(
            re_explain_safe(
                sql=sql,
                connection_id=int(connection_id),
                store=store,
                timeout_seconds=float(timeout_seconds),
            )
        )
    except UnsafeQueryError as e:
        return {"ok": False, "error": "unsafe_query", "details": str(e)}
    except ConnectionNotFoundError as e:
        return {"ok": False, "error": "not_found", "details": str(e)}
    except KeychainUnavailableError as e:
        return {"ok": False, "error": "keychain_unavailable", "details": str(e)}
    except NoDefaultConnectionError as e:
        return {"ok": False, "error": "no_default_connection", "details": str(e)}
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "error": "timeout",
            "details": f"EXPLAIN не уложился в {timeout_seconds} секунд",
        }
    except ReExplainError as e:
        return {"ok": False, "error": "re_explain_failed", "details": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("plan_analyzer.re_explain failed (unexpected)")
        # Сообщаем тип ошибки чтобы UI мог различить asyncpg.PostgresError etc.
        return {
            "ok": False,
            "error": "unexpected",
            "details": f"{type(e).__name__}: {e}",
        }

    import json
    return {
        "ok": True,
        "plan_json": json.dumps(plan, ensure_ascii=False),
        "engine": "postgres",
    }


def _run_async(coro: Any) -> Any:
    """Запустить async coroutine из sync RPC context.

    RPC handlers в Optimyzer — sync (см. existing rpc.dispatcher). Но re-EXPLAIN
    нативно async (asyncpg). Запускаем через asyncio.run() — это создаёт новый
    event loop. В production RPC dispatcher работает в Tauri sidecar threading
    model, новый loop безопасен.

    Тесты, которым нужен control над loop'ом, должны вызывать re_explain_safe()
    напрямую (он async), а не через RPC handler.
    """
    return asyncio.run(coro)
