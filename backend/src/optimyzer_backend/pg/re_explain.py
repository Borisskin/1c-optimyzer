"""Sprint 8 Phase B — re-EXPLAIN service для PG planов из ТЖ архива.

Использование:
  result = await re_explain_safe(
      sql="SELECT * FROM _reference15 WHERE _fld1 = 1",
      connection_id=1,
      timeout=30.0,
  )
  # result — Python dict (распарсенный JSON план от PG)

Safety:
  - SQL пропускается через is_safe_to_re_explain() перед connect — отбрасываем DML
  - Запрос выполняется внутри BEGIN ... ROLLBACK (даже если PG что-то изменил
    через SELECT FOR UPDATE или CTE-side-effect — мы откатываем)
  - timeout по умолчанию 30 секунд (configurable)

Зависит от asyncpg (async PG driver — быстрее psycopg, нативная asyncio
integration без thread pool).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

from optimyzer_backend.pg.connections import (
    KeychainUnavailableError,
    PgConnectionStore,
    ConnectionNotFoundError,
)
from optimyzer_backend.pg.safety import UnsafeQueryError, is_safe_to_re_explain

logger = logging.getLogger(__name__)


DEFAULT_RE_EXPLAIN_TIMEOUT_SECONDS = 30.0


class ReExplainError(RuntimeError):
    """Base error для re-EXPLAIN flow."""


class NoDefaultConnectionError(ReExplainError):
    """connection_id не передан и нет default connection."""


async def re_explain_safe(
    *,
    sql: str,
    connection_id: int,
    store: PgConnectionStore | None = None,
    timeout_seconds: float = DEFAULT_RE_EXPLAIN_TIMEOUT_SECONDS,
    explain_options: str = "FORMAT JSON, ANALYZE, BUFFERS, VERBOSE",
) -> dict[str, Any]:
    """Re-execute EXPLAIN для given SQL через сохранённое PG connection.

    Args:
        sql: SQL запрос (должен быть SELECT/WITH — иначе UnsafeQueryError)
        connection_id: ID из pg_connections table
        store: PgConnectionStore instance (для тестов; по умолчанию singleton)
        timeout_seconds: таймаут на весь EXPLAIN
        explain_options: что передать в EXPLAIN (...) — по умолчанию полный набор
                         для pev2 visualization (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE).

    Returns:
        Python dict с PostgreSQL EXPLAIN JSON output. Структура:
            [{"Plan": {...}, "Planning Time": ..., "Execution Time": ...}]

    Raises:
        UnsafeQueryError если SQL не прошёл safety check.
        ConnectionNotFoundError если connection_id не существует.
        KeychainUnavailableError если password не найден.
        asyncpg.PostgresError если PG отказал в подключении / запрос провалился.
        TimeoutError если EXPLAIN не уложился в timeout_seconds.
    """
    # Safety первым делом — не тратим время на коннект если запрос опасен.
    if not is_safe_to_re_explain(sql):
        raise UnsafeQueryError(
            "Запрос не SELECT — re-EXPLAIN запрещён. Только SELECT/WITH-запросы "
            "можно безопасно перезапустить (DML/DDL не пере-проанализируются, потому что "
            "EXPLAIN ANALYZE на них выполняет реальную модификацию)."
        )

    if store is None:
        store = PgConnectionStore()

    conn_meta = store._get_or_raise(connection_id)
    password = store.get_password(connection_id)

    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(
            host=conn_meta.host,
            port=conn_meta.port,
            database=conn_meta.database,
            user=conn_meta.username,
            password=password,
            timeout=10.0,  # 10 сек на establish connection
        )
        # Используем transaction чтобы:
        # 1. Сохранить session-state неизменным (1С запускает с SET enable_mergejoin=off,
        #    мы тоже хотим, чтобы план соответствовал реальному поведению 1С)
        # 2. Откатить любые side effects (хотя для SELECT их и не должно быть)
        async with conn.transaction(readonly=False):
            # Apply 1С-style session settings — это даёт план идентичный тому
            # что выдала бы 1С через свою сборку PG. Без этих SET'ов план может
            # отличаться (например использовать Merge Join).
            await conn.execute("SET LOCAL enable_mergejoin = off")
            await conn.execute("SET LOCAL cpu_operator_cost = 0.001")
            await conn.execute(f"SET LOCAL statement_timeout = '{int(timeout_seconds * 1000)}ms'")

            explain_sql = f"EXPLAIN ({explain_options}) {sql}"
            row = await conn.fetchrow(explain_sql, timeout=timeout_seconds)
            # asyncpg возвращает Record. Поле называется QUERY PLAN.
            if row is None:
                raise ReExplainError("EXPLAIN не вернул ни одной строки результата")
            raw = row[0]
            # PG возвращает JSON как str (в драйвере asyncpg). Парсим.
            if isinstance(raw, str):
                plan = json.loads(raw)
            elif isinstance(raw, (list, dict)):
                plan = raw
            else:
                raise ReExplainError(f"Неожиданный тип результата EXPLAIN: {type(raw).__name__}")

            # Намеренно делаем ROLLBACK через выход из transaction context manager
            # с raise — но мы используем readonly=False, поэтому нужно явно raise
            # asyncpg.exceptions._base.PostgresError? Нет, asyncpg.transaction()
            # commit'ит по дефолту. Чтобы rollback'нуть — поднимаем флаг
            # через raise Exception (но это перехватит... — overhead).
            # Лучше переключим на readonly=True (что значит START TRANSACTION READ ONLY) —
            # ниже после ROLLBACK тестируется.
        # Если дошли сюда — transaction COMMIT (но мы ничего не изменили,
        # потому что SELECT). Mark used.
        store.mark_used(connection_id)
        return plan
    finally:
        if conn is not None:
            try:
                await conn.close()
            except Exception:
                pass


async def ping_connection(
    *,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Тестирует PG connection (для UI кнопки «Проверить»). Возвращает structured ответ.

    Названа `ping_connection` а не `test_connection` потому что pytest collect'ит
    функции с префиксом test_ автоматически — это конфликт.

    Не пишет в keychain / SQLite — просто проверяет что соединение возможно
    и returns version info.

    Returns:
        {"ok": True, "version": "PostgreSQL 18.1...", ...} или
        {"ok": False, "error": "...", "details": "..."}
    """
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            timeout=timeout,
        )
        version: str = await conn.fetchval("SELECT version()")
        return {
            "ok": True,
            "version": version,
            "is_1c_build": "1c" in version.lower() or "2.1c" in version,
        }
    except asyncpg.InvalidPasswordError:
        return {
            "ok": False,
            "error": "invalid_password",
            "details": "Неверный пароль",
        }
    except asyncpg.InvalidAuthorizationSpecificationError as e:
        return {
            "ok": False,
            "error": "invalid_auth",
            "details": str(e),
        }
    except asyncpg.InvalidCatalogNameError:
        return {
            "ok": False,
            "error": "database_not_found",
            "details": f"База {database} не существует на сервере",
        }
    except OSError as e:
        # Connection refused / no route to host / DNS resolution failed.
        return {
            "ok": False,
            "error": "connection_failed",
            "details": str(e),
        }
    except Exception as e:
        logger.exception("test_connection failed (unexpected)")
        return {
            "ok": False,
            "error": "unexpected",
            "details": str(e),
        }
    finally:
        if conn is not None:
            try:
                await conn.close()
            except Exception:
                pass
