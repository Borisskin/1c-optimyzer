"""Sprint 5 Phase C — integration-тесты RPC методов configuration.* + расширенный
query_analyzer.analyze с автоматическим использованием config store.

Использует synthetic XML выгрузку (минимум: Configuration.xml + Catalog).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# Импорт регистрирует RPC методы
import optimyzer_backend.rpc.configuration_rpc  # noqa: F401
import optimyzer_backend.rpc.query_analyzer_rpc  # noqa: F401
from optimyzer_backend.configuration_metadata.api import reset_default_store_for_tests
from optimyzer_backend.rpc.configuration_rpc import (
    configuration_connect_rpc,
    configuration_disconnect_rpc,
    configuration_reindex_rpc,
    configuration_status_rpc,
)
from optimyzer_backend.rpc.query_analyzer_rpc import analyze_rpc, status_rpc


NAMESPACES = (
    'xmlns="http://v8.1c.ru/8.3/MDClasses" '
    'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
    'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)


def _wrap(inner: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<MetaDataObject {NAMESPACES}>\n{inner}\n</MetaDataObject>\n'


def _make_dump(tmp_path: Path, config_name: str = "ТестКонфигурация") -> Path:
    root = tmp_path / "rpc_dump"
    root.mkdir()
    (root / "Configuration.xml").write_text(
        _wrap(textwrap.dedent(f"""\
        <Configuration uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee">
          <Properties>
            <Name>{config_name}</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>RPC Test</v8:content></v8:item></Synonym>
            <Vendor>RPC Test Vendor</Vendor>
            <Version>9.9.9</Version>
          </Properties>
        </Configuration>
        """)),
        encoding="utf-8",
    )
    (root / "Catalogs").mkdir()
    (root / "Catalogs" / "Контрагенты.xml").write_text(
        _wrap(textwrap.dedent("""\
        <Catalog>
          <Properties><Name>Контрагенты</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>К</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <Attribute><Properties><Name>ИНН</Name><Type><v8:Type>xs:string</v8:Type></Type></Properties></Attribute>
          </ChildObjects>
        </Catalog>
        """)),
        encoding="utf-8",
    )
    return root


@pytest.fixture(autouse=True)
def isolated_config_db(tmp_path: Path, monkeypatch):
    """Каждый тест получает свой временный config_metadata.db через env."""
    custom = tmp_path / "config_metadata_isolated.db"
    monkeypatch.setenv("OPTIMYZER_CONFIG_DB_PATH", str(custom))
    reset_default_store_for_tests()
    yield
    reset_default_store_for_tests()


# ---- configuration.connect ----


class TestConfigurationConnect:
    def test_connect_to_valid_dump(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        result = configuration_connect_rpc(str(root))
        assert result["ok"] is True
        assert result["status"] == "indexed"
        assert result["object_count"] >= 1
        assert result["configuration"]["name"] == "ТестКонфигурация"
        assert result["configuration"]["vendor"] == "RPC Test Vendor"
        assert "Справочник" in result["by_kind"]

    def test_connect_returns_already_indexed_on_repeat(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        result2 = configuration_connect_rpc(str(root))
        assert result2["status"] == "already_indexed"

    def test_connect_nonexistent_path(self, tmp_path: Path):
        result = configuration_connect_rpc(str(tmp_path / "does_not_exist"))
        assert result["ok"] is False
        assert "не существует" in result["error"].lower() or "exist" in result["error"].lower()

    def test_connect_not_a_directory(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("not a dir", encoding="utf-8")
        result = configuration_connect_rpc(str(f))
        assert result["ok"] is False

    def test_connect_dir_without_configuration_xml(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = configuration_connect_rpc(str(empty))
        assert result["ok"] is False
        assert "Configuration.xml" in result["error"]

    def test_connect_empty_string(self):
        result = configuration_connect_rpc("")
        assert result["ok"] is False

    def test_connect_returns_source_path(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        result = configuration_connect_rpc(str(root))
        assert result["source_path"] == str(root)


# ---- configuration.status ----


class TestConfigurationStatus:
    def test_status_when_not_connected(self):
        result = configuration_status_rpc()
        assert result["ok"] is True
        assert result["connected"] is False

    def test_status_when_connected(self, tmp_path: Path):
        root = _make_dump(tmp_path, config_name="БП33")
        configuration_connect_rpc(str(root))
        result = configuration_status_rpc()
        assert result["connected"] is True
        assert result["object_count"] >= 1
        assert result["source_path"] == str(root)
        assert result["configuration"]["name"] == "БП33"
        assert result["configuration"]["version"] == "9.9.9"


# ---- configuration.disconnect ----


class TestConfigurationDisconnect:
    def test_disconnect_clears_status(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        assert configuration_status_rpc()["connected"] is True
        result = configuration_disconnect_rpc()
        assert result["ok"] is True
        assert configuration_status_rpc()["connected"] is False

    def test_disconnect_when_not_connected_is_idempotent(self):
        result = configuration_disconnect_rpc()
        assert result["ok"] is True


# ---- configuration.reindex ----


class TestConfigurationReindex:
    def test_reindex_when_not_connected_returns_error(self):
        result = configuration_reindex_rpc()
        assert result["ok"] is False
        assert "не подключена" in result["error"].lower() or "connect" in result["error"].lower()

    def test_reindex_repeats_indexing(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        # Сначала already_indexed
        r1 = configuration_connect_rpc(str(root))
        assert r1["status"] == "already_indexed"
        # Reindex принудительно
        r2 = configuration_reindex_rpc()
        assert r2["ok"] is True
        assert r2["status"] == "indexed"
        assert r2["object_count"] >= 1


# ---- query_analyzer.analyze auto-uses config store ----


class TestQueryAnalyzerAutoUsesConfigStore:
    def test_analyze_without_config_silent_semantic(self, tmp_path: Path):
        """Sprint 5: analyze когда config не подключён — semantic rules silent."""
        # Используем object_not_exists rule — он должен skip без config
        q = "ВЫБРАТЬ * ИЗ Справочник.НеСуществующий"
        result = analyze_rpc(q)
        assert result["ok"] is True
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "object_not_exists" not in rule_ids
        assert result["configuration_connected"] is False

    def test_analyze_with_config_runs_semantic(self, tmp_path: Path):
        """Sprint 5: analyze когда config подключён — semantic rules срабатывают."""
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        q = "ВЫБРАТЬ * ИЗ Справочник.НеСуществующий"
        result = analyze_rpc(q)
        assert result["ok"] is True
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "object_not_exists" in rule_ids
        assert result["configuration_connected"] is True

    def test_analyze_existing_object_no_semantic_finding(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        q = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты"
        result = analyze_rpc(q)
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "object_not_exists" not in rule_ids

    def test_analyze_disconnect_removes_semantic_findings(self, tmp_path: Path):
        """После disconnect — semantic rules должны замолчать."""
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        q = "ВЫБРАТЬ * ИЗ Справочник.НеСуществующий"
        r_with = analyze_rpc(q)
        assert "object_not_exists" in {f["rule_id"] for f in r_with["findings"]}
        configuration_disconnect_rpc()
        r_without = analyze_rpc(q)
        assert "object_not_exists" not in {f["rule_id"] for f in r_without["findings"]}


# ---- query_analyzer.status reports configuration_connected ----


class TestQueryAnalyzerStatusReportsConfiguration:
    def test_status_reports_disconnected_initially(self):
        result = status_rpc()
        assert result["ok"] is True
        assert result["configuration_connected"] is False
        assert result["semantic_rules_count"] >= 8

    def test_status_reports_connected_after_connect(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        result = status_rpc()
        assert result["configuration_connected"] is True

    def test_status_reports_back_to_disconnected_after_disconnect(self, tmp_path: Path):
        root = _make_dump(tmp_path)
        configuration_connect_rpc(str(root))
        configuration_disconnect_rpc()
        result = status_rpc()
        assert result["configuration_connected"] is False
