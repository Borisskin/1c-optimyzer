"""Sprint 5 Phase A — unit-тесты парсера выгрузки конфигурации 1С и
SQLite-индекса метаданных.

Тестовые данные — synthetic XML, имитирующий формат Конфигуратора
(см. docs/CONFIGURATION_XML_FORMAT_STUDY.md).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from optimyzer_backend.configuration_metadata import (
    ConfigurationObject,
    ConfigurationParser,
    ConfigurationMetadataStore,
)
from optimyzer_backend.configuration_metadata.parser import (
    Attribute,
    TabularSection,
    ConfigurationParserError,
)
from optimyzer_backend.configuration_metadata.api import (
    get_default_db_path,
    get_default_store,
    reset_default_store_for_tests,
)
from optimyzer_backend.configuration_metadata.store import _levenshtein


# ---- helpers: build synthetic dump on disk ----

NAMESPACES = (
    'xmlns="http://v8.1c.ru/8.3/MDClasses" '
    'xmlns:app="http://v8.1c.ru/8.2/managed-application/core" '
    'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
    'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)


def _wrap_metadata(inner_xml: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NAMESPACES} version="2.20">
{inner_xml}
</MetaDataObject>
"""


def _make_configuration_xml(name: str, synonym_ru: str, vendor: str, version: str) -> str:
    inner = textwrap.dedent(
        f"""\
        <Configuration uuid="11111111-2222-3333-4444-555555555555">
          <Properties>
            <Name>{name}</Name>
            <Synonym>
              <v8:item>
                <v8:lang>ru</v8:lang>
                <v8:content>{synonym_ru}</v8:content>
              </v8:item>
            </Synonym>
            <Vendor>{vendor}</Vendor>
            <Version>{version}</Version>
          </Properties>
        </Configuration>
        """
    )
    return _wrap_metadata(inner)


def _make_catalog_xml(name: str, synonym_ru: str, attrs: list[tuple[str, str]], ts_attrs: list[tuple[str, list[tuple[str, str]]]] | None = None) -> str:
    attr_xml = ""
    for aname, atype in attrs:
        attr_xml += textwrap.dedent(
            f"""\
            <Attribute uuid="aaaaaaaa-1111-2222-3333-{aname.ljust(12, 'x')[:12]}">
              <Properties>
                <Name>{aname}</Name>
                <Type><v8:Type>{atype}</v8:Type></Type>
              </Properties>
            </Attribute>
            """
        )
    ts_xml = ""
    for ts_name, ts_inner_attrs in (ts_attrs or []):
        inner = ""
        for tn, tt in ts_inner_attrs:
            inner += textwrap.dedent(
                f"""\
                <Attribute uuid="bbbbbbbb-{tn.ljust(8, 'y')[:8]}-2222-3333-444444444444">
                  <Properties>
                    <Name>{tn}</Name>
                    <Type><v8:Type>{tt}</v8:Type></Type>
                  </Properties>
                </Attribute>
                """
            )
        ts_xml += textwrap.dedent(
            f"""\
            <TabularSection uuid="cccccccc-1111-2222-3333-444444444444">
              <Properties><Name>{ts_name}</Name></Properties>
              <ChildObjects>
            {textwrap.indent(inner, "    ")}
              </ChildObjects>
            </TabularSection>
            """
        )
    inner_main = textwrap.dedent(
        f"""\
        <Catalog uuid="dddddddd-1111-2222-3333-444444444444">
          <Properties>
            <Name>{name}</Name>
            <Synonym>
              <v8:item>
                <v8:lang>ru</v8:lang>
                <v8:content>{synonym_ru}</v8:content>
              </v8:item>
            </Synonym>
            <Hierarchical>false</Hierarchical>
          </Properties>
          <ChildObjects>
        {textwrap.indent(attr_xml, "    ")}
        {textwrap.indent(ts_xml, "    ")}
          </ChildObjects>
        </Catalog>
        """
    )
    return _wrap_metadata(inner_main)


def _make_accumulation_register_xml(
    name: str, register_type: str, dimensions: list[tuple[str, str]], resources: list[tuple[str, str]]
) -> str:
    dim_xml = ""
    for dn, dt in dimensions:
        dim_xml += textwrap.dedent(
            f"""\
            <Dimension uuid="eeeeeeee-1111-2222-3333-444444444444">
              <Properties>
                <Name>{dn}</Name>
                <Type><v8:Type>{dt}</v8:Type></Type>
              </Properties>
            </Dimension>
            """
        )
    res_xml = ""
    for rn, rt in resources:
        res_xml += textwrap.dedent(
            f"""\
            <Resource uuid="ffffffff-1111-2222-3333-444444444444">
              <Properties>
                <Name>{rn}</Name>
                <Type><v8:Type>{rt}</v8:Type></Type>
              </Properties>
            </Resource>
            """
        )
    inner = textwrap.dedent(
        f"""\
        <AccumulationRegister uuid="11112222-3333-4444-5555-666666666666">
          <Properties>
            <Name>{name}</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>{name}</v8:content></v8:item></Synonym>
            <RegisterType>{register_type}</RegisterType>
          </Properties>
          <ChildObjects>
        {textwrap.indent(dim_xml + res_xml, "    ")}
          </ChildObjects>
        </AccumulationRegister>
        """
    )
    return _wrap_metadata(inner)


def _make_enum_xml(name: str, values: list[str]) -> str:
    ev_xml = ""
    for v in values:
        ev_xml += textwrap.dedent(
            f"""\
            <EnumValue uuid="99999999-1111-2222-3333-444444444444">
              <Properties><Name>{v}</Name></Properties>
            </EnumValue>
            """
        )
    inner = textwrap.dedent(
        f"""\
        <Enum uuid="88888888-1111-2222-3333-444444444444">
          <Properties>
            <Name>{name}</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>{name}</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
        {textwrap.indent(ev_xml, "    ")}
          </ChildObjects>
        </Enum>
        """
    )
    return _wrap_metadata(inner)


@pytest.fixture
def synthetic_dump(tmp_path: Path) -> Path:
    """Synthetic выгрузка с минимальным набором объектов."""
    root = tmp_path / "dump"
    root.mkdir()
    # Configuration.xml
    (root / "Configuration.xml").write_text(
        _make_configuration_xml("ТестоваяКонфигурация", "Тестовая конфигурация", "Test Inc.", "1.0.1"),
        encoding="utf-8",
    )
    # Catalogs/Контрагенты.xml
    catalogs = root / "Catalogs"
    catalogs.mkdir()
    (catalogs / "Контрагенты.xml").write_text(
        _make_catalog_xml(
            "Контрагенты",
            "Контрагенты",
            [
                ("ИНН", "xs:string"),
                ("КПП", "xs:string"),
                ("ВидКонтрагента", "cfg:EnumRef.ВидыКонтрагентов"),
            ],
            ts_attrs=[
                ("КонтактнаяИнформация", [("Тип", "cfg:EnumRef.ТипыКонтактнойИнформации"), ("Значение", "xs:string")]),
            ],
        ),
        encoding="utf-8",
    )
    # Catalogs/Валюты.xml
    (catalogs / "Валюты.xml").write_text(
        _make_catalog_xml("Валюты", "Валюты", [("Код", "xs:string")]),
        encoding="utf-8",
    )
    # AccumulationRegisters/ТоварыНаСкладах.xml (Balance)
    arf = root / "AccumulationRegisters"
    arf.mkdir()
    (arf / "ТоварыНаСкладах.xml").write_text(
        _make_accumulation_register_xml(
            "ТоварыНаСкладах",
            "Balance",
            [("Склад", "cfg:CatalogRef.Склады"), ("Номенклатура", "cfg:CatalogRef.Номенклатура")],
            [("Количество", "xs:decimal")],
        ),
        encoding="utf-8",
    )
    # AccumulationRegisters/ПродажиОбороты.xml (Turnovers)
    (arf / "Продажи.xml").write_text(
        _make_accumulation_register_xml(
            "Продажи",
            "Turnovers",
            [("Контрагент", "cfg:CatalogRef.Контрагенты")],
            [("Сумма", "xs:decimal")],
        ),
        encoding="utf-8",
    )
    # Enums/ВидыКонтрагентов.xml
    enums = root / "Enums"
    enums.mkdir()
    (enums / "ВидыКонтрагентов.xml").write_text(
        _make_enum_xml("ВидыКонтрагентов", ["ЮридическоеЛицо", "ФизическоеЛицо"]),
        encoding="utf-8",
    )
    # InformationRegisters/КурсыВалют.xml
    info_dir = root / "InformationRegisters"
    info_dir.mkdir()
    ir_xml = _wrap_metadata(textwrap.dedent("""\
        <InformationRegister uuid="11112222-3333-4444-5555-666666666666">
          <Properties>
            <Name>КурсыВалют</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Курсы валют</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <Dimension uuid="11112222-3333-4444-5555-666666666666">
              <Properties><Name>Валюта</Name><Type><v8:Type>cfg:CatalogRef.Валюты</v8:Type></Type></Properties>
            </Dimension>
            <Resource uuid="22223333-4444-5555-6666-777777777777">
              <Properties><Name>Курс</Name><Type><v8:Type>xs:decimal</v8:Type></Type></Properties>
            </Resource>
          </ChildObjects>
        </InformationRegister>
        """))
    (info_dir / "КурсыВалют.xml").write_text(ir_xml, encoding="utf-8")
    return root


# ---- parser tests ----


class TestParser:
    def test_parser_rejects_missing_path(self, tmp_path: Path):
        with pytest.raises(ConfigurationParserError):
            ConfigurationParser(tmp_path / "nonexistent")

    def test_parser_rejects_dir_without_configuration_xml(self, tmp_path: Path):
        (tmp_path / "empty").mkdir()
        with pytest.raises(ConfigurationParserError):
            ConfigurationParser(tmp_path / "empty")

    def test_get_configuration_info(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        info = parser.get_configuration_info()
        assert info["name"] == "ТестоваяКонфигурация"
        assert info["synonym_ru"] == "Тестовая конфигурация"
        assert info["vendor"] == "Test Inc."
        assert info["version"] == "1.0.1"

    def test_parse_catalog_with_attributes(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        catalog = next(o for o in objects if o.full_name == "Справочник.Контрагенты")
        assert catalog.kind_ru == "Справочник"
        assert catalog.name == "Контрагенты"
        assert catalog.synonym_ru == "Контрагенты"
        attr_names = {a.name for a in catalog.attributes}
        assert attr_names == {"ИНН", "КПП", "ВидКонтрагента"}
        # Тип ссылочного реквизита извлекается
        view_attr = next(a for a in catalog.attributes if a.name == "ВидКонтрагента")
        assert view_attr.type_repr == "cfg:EnumRef.ВидыКонтрагентов"

    def test_parse_catalog_with_tabular_section(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        catalog = next(o for o in objects if o.full_name == "Справочник.Контрагенты")
        assert len(catalog.tabular_sections) == 1
        ts = catalog.tabular_sections[0]
        assert ts.name == "КонтактнаяИнформация"
        ts_attr_names = {a.name for a in ts.attributes}
        assert ts_attr_names == {"Тип", "Значение"}

    def test_parse_accumulation_register_balance_with_dimensions_resources(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        ar = next(o for o in objects if o.full_name == "РегистрНакопления.ТоварыНаСкладах")
        assert ar.register_type == "Balance"
        assert {d.name for d in ar.dimensions} == {"Склад", "Номенклатура"}
        assert {r.name for r in ar.resources} == {"Количество"}
        # Виртуальные таблицы Balance-регистра
        assert set(ar.virtual_tables) == {"Остатки", "Обороты", "ОстаткиИОбороты"}

    def test_parse_accumulation_register_turnovers_has_only_turnovers_vtable(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        ar = next(o for o in objects if o.full_name == "РегистрНакопления.Продажи")
        assert ar.register_type == "Turnovers"
        assert ar.virtual_tables == ["Обороты"]

    def test_parse_information_register_virtual_tables(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        ir = next(o for o in objects if o.full_name == "РегистрСведений.КурсыВалют")
        assert set(ir.virtual_tables) == {"СрезПоследних", "СрезПервых"}

    def test_parse_enum_values(self, synthetic_dump: Path):
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        en = next(o for o in objects if o.full_name == "Перечисление.ВидыКонтрагентов")
        assert en.enum_values == ["ЮридическоеЛицо", "ФизическоеЛицо"]

    def test_parse_non_existent_folders_skipped(self, synthetic_dump: Path):
        """Папок Documents/AccountingRegisters нет — парсер не падает."""
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        kinds = {o.kind_ru for o in objects}
        # есть Справочник, РегистрНакопления, РегистрСведений, Перечисление
        assert "Документ" not in kinds
        assert "РегистрБухгалтерии" not in kinds

    def test_parse_invalid_xml_files_skipped(self, synthetic_dump: Path):
        """Битый XML файл не должен ронять парсер — только warning в лог."""
        broken = synthetic_dump / "Catalogs" / "Битый.xml"
        broken.write_text("<not><valid", encoding="utf-8")
        parser = ConfigurationParser(synthetic_dump)
        objects = parser.parse()
        # Контрагенты + Валюты остались
        catalog_names = {o.name for o in objects if o.kind_ru == "Справочник"}
        assert "Контрагенты" in catalog_names
        assert "Валюты" in catalog_names


# ---- store tests ----


class TestStore:
    def test_index_synthetic_dump(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        result = store.index_configuration(synthetic_dump)
        assert result["status"] == "indexed"
        assert result["object_count"] >= 4
        assert result["configuration"]["name"] == "ТестоваяКонфигурация"
        assert result["configuration"]["synonym_ru"] == "Тестовая конфигурация"
        assert "Справочник" in result["by_kind"]

    def test_is_object_exists_positive(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        assert store.is_object_exists("Справочник.Контрагенты")
        assert store.is_object_exists("Справочник.Валюты")
        assert store.is_object_exists("РегистрНакопления.ТоварыНаСкладах")
        assert store.is_object_exists("Перечисление.ВидыКонтрагентов")

    def test_is_object_exists_negative(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        assert not store.is_object_exists("Справочник.Несуществующий")
        assert not store.is_object_exists("Документ.Несуществующий")
        # Имя без префикса типа не должно срабатывать
        assert not store.is_object_exists("Контрагенты")

    def test_get_attributes(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        attrs = store.get_attributes("Справочник.Контрагенты")
        names = {a.name for a in attrs}
        assert names == {"ИНН", "КПП", "ВидКонтрагента"}

    def test_get_dimensions_and_resources(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        dims = store.get_dimensions("РегистрНакопления.ТоварыНаСкладах")
        res = store.get_resources("РегистрНакопления.ТоварыНаСкладах")
        assert {d.name for d in dims} == {"Склад", "Номенклатура"}
        assert {r.name for r in res} == {"Количество"}

    def test_get_virtual_tables_balance(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        vt = store.get_virtual_tables("РегистрНакопления.ТоварыНаСкладах")
        assert set(vt) == {"Остатки", "Обороты", "ОстаткиИОбороты"}

    def test_get_virtual_tables_turnovers(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        vt = store.get_virtual_tables("РегистрНакопления.Продажи")
        assert vt == ["Обороты"]

    def test_get_virtual_tables_information_register(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        vt = store.get_virtual_tables("РегистрСведений.КурсыВалют")
        assert set(vt) == {"СрезПоследних", "СрезПервых"}

    def test_get_virtual_tables_catalog_returns_empty(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        assert store.get_virtual_tables("Справочник.Контрагенты") == []

    def test_get_enum_values(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        values = store.get_enum_values("Перечисление.ВидыКонтрагентов")
        assert values == ["ЮридическоеЛицо", "ФизическоеЛицо"]

    def test_get_object_full_roundtrip(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        obj = store.get_object("Справочник.Контрагенты")
        assert obj is not None
        assert obj.kind_ru == "Справочник"
        assert obj.name == "Контрагенты"
        assert len(obj.attributes) == 3
        assert len(obj.tabular_sections) == 1
        ts = obj.tabular_sections[0]
        assert ts.name == "КонтактнаяИнформация"
        assert {a.name for a in ts.attributes} == {"Тип", "Значение"}

    def test_get_object_returns_none_for_unknown(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        assert store.get_object("Справочник.Несуществующий") is None

    def test_hash_invalidation_no_change_returns_already_indexed(
        self, synthetic_dump: Path, tmp_path: Path
    ):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        r1 = store.index_configuration(synthetic_dump)
        assert r1["status"] == "indexed"
        r2 = store.index_configuration(synthetic_dump)
        assert r2["status"] == "already_indexed"
        assert r2["object_count"] == r1["object_count"]

    def test_hash_invalidation_changed_xml_triggers_reindex(
        self, synthetic_dump: Path, tmp_path: Path
    ):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        # Меняем один файл (mtime + content)
        (synthetic_dump / "Catalogs" / "Новый.xml").write_text(
            _make_catalog_xml("Новый", "Новый", [("Поле1", "xs:string")]),
            encoding="utf-8",
        )
        r2 = store.index_configuration(synthetic_dump)
        assert r2["status"] == "indexed"
        assert store.is_object_exists("Справочник.Новый")

    def test_persistence_across_store_instances(
        self, synthetic_dump: Path, tmp_path: Path
    ):
        db = tmp_path / "test.db"
        store1 = ConfigurationMetadataStore(db)
        store1.index_configuration(synthetic_dump)
        del store1
        # Новый экземпляр — должен видеть тот же индекс
        store2 = ConfigurationMetadataStore(db)
        assert store2.is_indexed()
        assert store2.is_object_exists("Справочник.Контрагенты")
        r = store2.index_configuration(synthetic_dump)
        assert r["status"] == "already_indexed"

    def test_clear_removes_index(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        assert store.is_indexed()
        store.clear()
        assert not store.is_indexed()
        assert store.count_objects() == 0

    def test_search_similar_objects(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        # 'Кантрагенты' (опечатка) → Контрагенты
        similar = store.search_similar_objects("Справочник.Кантрагенты", max_distance=3)
        assert "Справочник.Контрагенты" in similar

    def test_search_similar_objects_no_match_for_distant_name(
        self, synthetic_dump: Path, tmp_path: Path
    ):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        similar = store.search_similar_objects("Справочник.СовершенноДругое", max_distance=3)
        assert "Справочник.Контрагенты" not in similar

    def test_stats_by_kind(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        stats = store.stats_by_kind()
        assert stats["Справочник"] == 2  # Контрагенты + Валюты
        assert stats["РегистрНакопления"] == 2
        assert stats["Перечисление"] == 1
        assert stats["РегистрСведений"] == 1

    def test_meta_get_set(self, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.set_meta("foo", "bar")
        assert store.get_meta("foo") == "bar"
        store.set_meta("foo", "baz")
        assert store.get_meta("foo") == "baz"
        assert store.get_meta("nonexistent") is None

    def test_get_meta_after_indexing(self, synthetic_dump: Path, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        store.index_configuration(synthetic_dump)
        assert store.get_meta("source_path") == str(synthetic_dump)
        assert store.get_meta("config_name") == "ТестоваяКонфигурация"
        assert store.get_meta("config_synonym_ru") == "Тестовая конфигурация"
        assert store.get_meta("config_version") == "1.0.1"
        assert store.get_meta("indexed_at") is not None
        assert store.get_meta("source_hash") is not None


# ---- Sprint 6 placeholders ----


class TestSprint6Placeholders:
    def test_find_module_by_context_raises_not_implemented(self, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        with pytest.raises(NotImplementedError, match="Sprint 6"):
            store.find_module_by_context("dummy.context")

    def test_extract_sdbl_from_module_raises_not_implemented(self, tmp_path: Path):
        store = ConfigurationMetadataStore(tmp_path / "test.db")
        with pytest.raises(NotImplementedError, match="Sprint 6"):
            store.extract_sdbl_from_module(None, 1)  # type: ignore[arg-type]


# ---- API tests ----


class TestApiHelpers:
    def test_get_default_db_path_uses_env_override(self, tmp_path: Path, monkeypatch):
        custom = tmp_path / "custom.db"
        monkeypatch.setenv("OPTIMYZER_CONFIG_DB_PATH", str(custom))
        reset_default_store_for_tests()
        assert get_default_db_path() == custom
        store = get_default_store()
        assert store.db_path == custom
        reset_default_store_for_tests()

    def test_get_default_db_path_falls_back_to_backend_data(
        self, monkeypatch
    ):
        monkeypatch.delenv("OPTIMYZER_CONFIG_DB_PATH", raising=False)
        reset_default_store_for_tests()
        p = get_default_db_path()
        # Должно быть .../backend/data/config_metadata.db
        assert p.name == "config_metadata.db"
        assert p.parent.name == "data"


# ---- Levenshtein helper ----


class TestLevenshtein:
    def test_levenshtein_identical(self):
        assert _levenshtein("abc", "abc") == 0

    def test_levenshtein_empty_strings(self):
        assert _levenshtein("", "abc") == 3
        assert _levenshtein("abc", "") == 3
        assert _levenshtein("", "") == 0

    def test_levenshtein_single_substitution(self):
        assert _levenshtein("кот", "код") == 1

    def test_levenshtein_typical_typo(self):
        assert _levenshtein("Контрагенты", "Кантрагенты") == 1

    def test_levenshtein_completely_different(self):
        # 'abc' vs 'xyz' = 3
        assert _levenshtein("abc", "xyz") == 3
