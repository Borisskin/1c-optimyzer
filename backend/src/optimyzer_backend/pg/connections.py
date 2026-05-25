"""Sprint 8 Phase B — PG connections storage с keychain для passwords.

Архитектура:
  - Metadata (host/port/db/username, без password) живёт в SQLite
    (metadata.sqlite, таблица pg_connections — см. sqlite_store.py)
  - Password сохраняется в OS keychain (Windows Credential Manager на Win,
    Keychain на macOS, secret service на Linux) через библиотеку keyring
  - Связь через `password_keychain_key` — уникальный ключ для каждого connection.

Keychain service name: "1c-optimyzer-pg" (constant).
Keychain account format: "conn-{id}".

Когда юзер удаляет connection — удаляем и из SQLite, и из keychain.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import keyring

from optimyzer_backend.storage.sqlite_store import SqliteStore, default_metadata_path

logger = logging.getLogger(__name__)

# Service name в keychain — единственная константа для всех connections юзера.
# Account name внутри сервиса — уникальный ключ password_keychain_key.
KEYCHAIN_SERVICE = "1c-optimyzer-pg"


@dataclass
class PgConnection:
    """Полная модель PG connection с password key. Internal — не отдаётся в UI."""

    id: int
    name: str
    host: str
    port: int
    database: str
    username: str
    password_keychain_key: str
    created_at: str
    last_used_at: str | None
    is_default: bool


@dataclass
class PgConnectionPublic:
    """Public-safe модель — без password info. Отдаётся в UI/RPC."""

    id: int
    name: str
    host: str
    port: int
    database: str
    username: str
    created_at: str
    last_used_at: str | None
    is_default: bool

    @classmethod
    def from_full(cls, c: PgConnection) -> "PgConnectionPublic":
        return cls(
            id=c.id,
            name=c.name,
            host=c.host,
            port=c.port,
            database=c.database,
            username=c.username,
            created_at=c.created_at,
            last_used_at=c.last_used_at,
            is_default=c.is_default,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "is_default": self.is_default,
        }


class PgConnectionStore:
    """SQLite-backed CRUD для PG connections + keychain integration.

    Lifecycle:
      - add()    → создаёт SQLite row + сохраняет password в keychain
      - get_password() → читает password из keychain (для re-EXPLAIN)
      - delete() → удаляет SQLite row + удаляет password из keychain
    """

    def __init__(self, db_path: Path | None = None) -> None:
        # Используем общий SqliteStore — schema уже включает pg_connections.
        # Передаём path для тестов (default — APPDATA/1c-optimyzer/metadata.sqlite).
        self._store = SqliteStore(db_path or default_metadata_path())

    def add(
        self,
        *,
        name: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
    ) -> PgConnectionPublic:
        """Создаёт connection. Password сохраняется в keychain под uniquely-generated key."""
        # Генерируем непредсказуемый ключ для keychain account. URL-safe чтобы
        # сразу можно было использовать без escaping.
        keychain_key = f"conn-{secrets.token_urlsafe(12)}"
        with self._store._conn() as c:
            cur = c.execute(
                """
                INSERT INTO pg_connections
                    (name, host, port, database, username, password_keychain_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    host,
                    port,
                    database,
                    username,
                    keychain_key,
                    datetime.utcnow().isoformat(),
                ),
            )
            new_id = cur.lastrowid

        # После SQLite commit — сохраняем в keychain. Если keychain недоступен
        # (на dev машинах без secret service на Linux), keyring.set_password
        # выбросит исключение. Откатываем SQLite row тогда.
        try:
            keyring.set_password(KEYCHAIN_SERVICE, keychain_key, password)
        except Exception as e:
            logger.exception("Не удалось сохранить PG password в keychain")
            # Cleanup SQLite row чтобы не было orphan record без password.
            with self._store._conn() as c:
                c.execute("DELETE FROM pg_connections WHERE id = ?", (new_id,))
            raise KeychainUnavailableError(
                f"Не удалось сохранить пароль в OS keychain: {e}. "
                f"Проверьте что у вашего пользователя есть доступ к OS секретному хранилищу."
            ) from e

        # Если это первое connection — делаем его default.
        if self.count() == 1:
            self.set_default(new_id)

        return PgConnectionPublic.from_full(self._get_or_raise(new_id))

    def list_all(self) -> list[PgConnectionPublic]:
        """Список всех connections (без password info)."""
        with self._store._conn() as c:
            rows = c.execute(
                """
                SELECT id, name, host, port, database, username,
                       password_keychain_key, created_at, last_used_at, is_default
                FROM pg_connections
                ORDER BY is_default DESC, created_at ASC
                """
            ).fetchall()
        return [PgConnectionPublic.from_full(_row_to_full(r)) for r in rows]

    def get(self, connection_id: int) -> PgConnectionPublic | None:
        try:
            return PgConnectionPublic.from_full(self._get_or_raise(connection_id))
        except ConnectionNotFoundError:
            return None

    def _get_or_raise(self, connection_id: int) -> PgConnection:
        with self._store._conn() as c:
            row = c.execute(
                """
                SELECT id, name, host, port, database, username,
                       password_keychain_key, created_at, last_used_at, is_default
                FROM pg_connections
                WHERE id = ?
                """,
                (connection_id,),
            ).fetchone()
        if row is None:
            raise ConnectionNotFoundError(f"PG connection id={connection_id} не найден")
        return _row_to_full(row)

    def get_password(self, connection_id: int) -> str:
        """Читает password из keychain. Raises ConnectionNotFoundError / KeychainUnavailableError."""
        conn = self._get_or_raise(connection_id)
        try:
            pwd = keyring.get_password(KEYCHAIN_SERVICE, conn.password_keychain_key)
        except Exception as e:
            raise KeychainUnavailableError(
                f"Не удалось прочитать пароль из OS keychain: {e}"
            ) from e
        if pwd is None:
            raise KeychainUnavailableError(
                f"Пароль для connection #{connection_id} ({conn.name}) не найден в keychain. "
                f"Возможно был очищен вручную. Удалите connection и создайте заново."
            )
        return pwd

    def delete(self, connection_id: int) -> None:
        """Удаляет connection из SQLite + password из keychain.

        Если password из keychain не удалось удалить (например он там не был —
        keychain corruption) — просто логируем warning, не падаем. Главное —
        запись в SQLite очищена.
        """
        conn = self._get_or_raise(connection_id)
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, conn.password_keychain_key)
        except Exception as e:
            logger.warning(
                "Не удалось удалить PG password из keychain для %s: %s",
                conn.password_keychain_key, e,
            )
        with self._store._conn() as c:
            c.execute("DELETE FROM pg_connections WHERE id = ?", (connection_id,))

    def set_default(self, connection_id: int) -> None:
        """Назначает default. Снимает флаг с остальных (single-default invariant)."""
        # Убедимся что connection существует.
        self._get_or_raise(connection_id)
        with self._store._conn() as c:
            c.execute("UPDATE pg_connections SET is_default = 0 WHERE is_default = 1")
            c.execute(
                "UPDATE pg_connections SET is_default = 1 WHERE id = ?",
                (connection_id,),
            )

    def get_default(self) -> PgConnectionPublic | None:
        with self._store._conn() as c:
            row = c.execute(
                """
                SELECT id, name, host, port, database, username,
                       password_keychain_key, created_at, last_used_at, is_default
                FROM pg_connections
                WHERE is_default = 1
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return PgConnectionPublic.from_full(_row_to_full(row))

    def mark_used(self, connection_id: int) -> None:
        """Обновляет last_used_at в момент успешного re-EXPLAIN."""
        with self._store._conn() as c:
            c.execute(
                "UPDATE pg_connections SET last_used_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), connection_id),
            )

    def count(self) -> int:
        with self._store._conn() as c:
            row = c.execute("SELECT COUNT(*) FROM pg_connections").fetchone()
        return int(row[0]) if row else 0


def _row_to_full(row: Any) -> PgConnection:
    """sqlite3.Row → PgConnection."""
    return PgConnection(
        id=int(row["id"]),
        name=row["name"],
        host=row["host"],
        port=int(row["port"]),
        database=row["database"],
        username=row["username"],
        password_keychain_key=row["password_keychain_key"],
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
        is_default=bool(row["is_default"]),
    )


class ConnectionNotFoundError(ValueError):
    """Запрошенный connection_id не существует в SQLite."""


class KeychainUnavailableError(RuntimeError):
    """OS keychain недоступен (linux без secret service / corruption / cleared)."""
