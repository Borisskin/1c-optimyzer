"""Sprint 8 Phase B — тесты PgConnectionStore.

Использует in-memory keyring backend чтобы не трогать реальный OS keychain.
"""

from __future__ import annotations

import keyring
import pytest
from keyring.backend import KeyringBackend

from optimyzer_backend.pg.connections import (
    ConnectionNotFoundError,
    KEYCHAIN_SERVICE,
    KeychainUnavailableError,
    PgConnectionStore,
)


# ============================================================
# In-memory keyring backend для тестов
# ============================================================


class InMemoryKeyring(KeyringBackend):
    """Хранит passwords в dict — для тестов без реального OS keychain."""

    priority = 999  # max — overrides любой другой keyring backend

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if (service, username) in self._store:
            del self._store[(service, username)]
        else:
            raise keyring.errors.PasswordDeleteError(
                f"No password for {service}/{username}"
            )


@pytest.fixture
def memory_keyring(monkeypatch: pytest.MonkeyPatch) -> InMemoryKeyring:
    """Подменяем глобальный keyring на in-memory backend."""
    backend = InMemoryKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "delete_password", backend.delete_password)
    return backend


@pytest.fixture
def store(tmp_path, memory_keyring) -> PgConnectionStore:
    """Изолированный store в tmp SQLite."""
    return PgConnectionStore(db_path=tmp_path / "test_metadata.sqlite")


# ============================================================
# add() / list_all() / get()
# ============================================================


def test_add_connection_returns_public_object(store: PgConnectionStore):
    conn = store.add(
        name="Test PG",
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass",
    )
    assert conn.name == "Test PG"
    assert conn.host == "localhost"
    assert conn.port == 5432
    assert conn.database == "testdb"
    assert conn.username == "testuser"
    assert conn.id > 0
    # Public object не имеет password info — нельзя случайно залогать.
    assert not hasattr(conn, "password")
    assert not hasattr(conn, "password_keychain_key")


def test_add_first_connection_becomes_default(store: PgConnectionStore):
    conn = store.add(
        name="Default candidate",
        host="h",
        port=5432,
        database="d",
        username="u",
        password="p",
    )
    assert conn.is_default is True


def test_second_connection_is_not_default(store: PgConnectionStore):
    c1 = store.add(name="c1", host="h", port=5432, database="d", username="u", password="p")
    c2 = store.add(name="c2", host="h", port=5432, database="d", username="u", password="p")
    assert c1.is_default is True
    # c2 не default — мы переопределяем только при первом insertion.
    refetched = store.get(c2.id)
    assert refetched is not None
    assert refetched.is_default is False


def test_list_all_orders_default_first(store: PgConnectionStore):
    store.add(name="A", host="h", port=5432, database="d", username="u", password="p")
    c2 = store.add(name="B", host="h", port=5432, database="d", username="u", password="p")
    store.set_default(c2.id)
    items = store.list_all()
    assert items[0].id == c2.id
    assert items[0].is_default is True


def test_get_returns_none_for_unknown(store: PgConnectionStore):
    assert store.get(99999) is None


def test_count(store: PgConnectionStore):
    assert store.count() == 0
    store.add(name="A", host="h", port=5432, database="d", username="u", password="p")
    assert store.count() == 1
    store.add(name="B", host="h", port=5432, database="d", username="u", password="p")
    assert store.count() == 2


# ============================================================
# Password keychain
# ============================================================


def test_password_saved_to_keychain(
    store: PgConnectionStore, memory_keyring: InMemoryKeyring
):
    conn = store.add(
        name="K", host="h", port=5432, database="d", username="u", password="secret-pw-123"
    )
    pwd = store.get_password(conn.id)
    assert pwd == "secret-pw-123"


def test_get_password_unknown_connection_raises(store: PgConnectionStore):
    with pytest.raises(ConnectionNotFoundError):
        store.get_password(99999)


def test_delete_removes_from_keychain(
    store: PgConnectionStore, memory_keyring: InMemoryKeyring
):
    conn = store.add(
        name="K", host="h", port=5432, database="d", username="u", password="del-me"
    )
    # Сначала проверим что password есть.
    assert store.get_password(conn.id) == "del-me"
    # Удаляем connection.
    store.delete(conn.id)
    # После delete connection нет.
    assert store.get(conn.id) is None
    # И password из keychain удалён (in-memory backend подтвердит).
    assert store.count() == 0


def test_delete_unknown_raises(store: PgConnectionStore):
    with pytest.raises(ConnectionNotFoundError):
        store.delete(99999)


def test_keychain_failure_rolls_back_sqlite(
    store: PgConnectionStore, monkeypatch: pytest.MonkeyPatch
):
    """Если keychain.set_password выкинул исключение — SQLite row должен быть удалён.

    Иначе у нас orphan record с keychain_key который ведёт в никуда — это сломает
    delete (нечего удалять) и get_password (вернёт None).
    """
    def raise_(*_args, **_kwargs):
        raise RuntimeError("keychain access denied")
    monkeypatch.setattr(keyring, "set_password", raise_)

    with pytest.raises(KeychainUnavailableError):
        store.add(name="X", host="h", port=5432, database="d", username="u", password="p")

    # SQLite не должна содержать orphan row.
    assert store.count() == 0


# ============================================================
# set_default / get_default
# ============================================================


def test_set_default_unique(store: PgConnectionStore):
    c1 = store.add(name="A", host="h", port=5432, database="d", username="u", password="p")
    c2 = store.add(name="B", host="h", port=5432, database="d", username="u", password="p")

    store.set_default(c2.id)
    items = store.list_all()
    defaults = [i for i in items if i.is_default]
    assert len(defaults) == 1
    assert defaults[0].id == c2.id


def test_set_default_unknown_raises(store: PgConnectionStore):
    with pytest.raises(ConnectionNotFoundError):
        store.set_default(99999)


def test_get_default_returns_none_when_no_connections(store: PgConnectionStore):
    assert store.get_default() is None


def test_get_default_returns_marked(store: PgConnectionStore):
    c1 = store.add(name="A", host="h", port=5432, database="d", username="u", password="p")
    d = store.get_default()
    assert d is not None
    assert d.id == c1.id


# ============================================================
# mark_used
# ============================================================


def test_mark_used_sets_last_used_at(store: PgConnectionStore):
    c = store.add(name="A", host="h", port=5432, database="d", username="u", password="p")
    assert c.last_used_at is None
    store.mark_used(c.id)
    refetched = store.get(c.id)
    assert refetched is not None
    assert refetched.last_used_at is not None


# ============================================================
# to_dict
# ============================================================


def test_to_dict_excludes_password_keychain_key(store: PgConnectionStore):
    """Public to_dict() для RPC ответа не должен содержать password_keychain_key.

    Это internal field, утечка в UI = security issue (юзер видит key который
    может использовать для попытки доступа к keychain напрямую).
    """
    c = store.add(name="A", host="h", port=5432, database="d", username="u", password="p")
    d = c.to_dict()
    assert "password" not in d
    assert "password_keychain_key" not in d
    # Зато безопасные поля присутствуют.
    assert d["name"] == "A"
    assert d["host"] == "h"
    assert d["port"] == 5432
