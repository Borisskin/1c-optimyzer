"""Sprint 5 Phase B — unit-тесты semantic rules engine.

Тестирует:
1. SDBL tokenizer — извлечение object refs, virtual table refs, ВЫРАЗИТЬ типов
2. SemanticRule loader — парсинг markdown с requires+check_name
3. Каждый из 8 чекеров — positive + negative case
4. Silent skip когда config_store не подключён
5. Aggregator интеграция (Sprint 4 syntactic + Sprint 5 semantic together)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from optimyzer_backend.configuration_metadata import (
    ConfigurationMetadataStore,
    ConfigurationParser,
)
from optimyzer_backend.query_analyzer.aggregator import QueryAnalyzer
from optimyzer_backend.query_analyzer.native_rules import (
    analyze as native_analyze,
    load_native_rules,
)
from optimyzer_backend.query_analyzer.sdbl_tokenizer import (
    extract_object_references,
    extract_virtual_table_references,
    extract_vyrazit_types,
    offset_to_line_col,
)


# ---- fixtures: synthetic configuration store ----


@pytest.fixture
def synthetic_store(tmp_path: Path) -> ConfigurationMetadataStore:
    """Synthetic выгрузка с минимальным набором объектов для семантических тестов."""
    root = tmp_path / "dump"
    root.mkdir()
    NS = (
        'xmlns="http://v8.1c.ru/8.3/MDClasses" '
        'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
        'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
    )

    def wrap(inner: str) -> str:
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<MetaDataObject {NS}>\n{inner}\n</MetaDataObject>\n'

    # Configuration.xml
    (root / "Configuration.xml").write_text(
        wrap(textwrap.dedent("""\
        <Configuration uuid="11111111-2222-3333-4444-555555555555">
          <Properties>
            <Name>ТестКонфигурация</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Тест</v8:content></v8:item></Synonym>
            <Vendor>Test</Vendor>
            <Version>1.0</Version>
          </Properties>
        </Configuration>
        """)),
        encoding="utf-8",
    )

    # Catalogs/Контрагенты — с реквизитами
    (root / "Catalogs").mkdir()
    (root / "Catalogs" / "Контрагенты.xml").write_text(
        wrap(textwrap.dedent("""\
        <Catalog uuid="cccccccc-cccc-cccc-cccc-cccccccccccc">
          <Properties>
            <Name>Контрагенты</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Контрагенты</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <Attribute><Properties>
              <Name>ИНН</Name><Type><v8:Type>xs:string</v8:Type></Type>
            </Properties></Attribute>
            <Attribute><Properties>
              <Name>КПП</Name><Type><v8:Type>xs:string</v8:Type></Type>
            </Properties></Attribute>
            <TabularSection><Properties><Name>КонтактнаяИнформация</Name></Properties>
              <ChildObjects>
                <Attribute><Properties><Name>Тип</Name><Type><v8:Type>xs:string</v8:Type></Type></Properties></Attribute>
              </ChildObjects>
            </TabularSection>
          </ChildObjects>
        </Catalog>
        """)),
        encoding="utf-8",
    )
    (root / "Catalogs" / "Номенклатура.xml").write_text(
        wrap(textwrap.dedent("""\
        <Catalog uuid="dddddddd-dddd-dddd-dddd-dddddddddddd">
          <Properties>
            <Name>Номенклатура</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Номенклатура</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <Attribute><Properties><Name>Артикул</Name><Type><v8:Type>xs:string</v8:Type></Type></Properties></Attribute>
          </ChildObjects>
        </Catalog>
        """)),
        encoding="utf-8",
    )

    # AccumulationRegisters/ТоварыНаСкладах — Balance с измерениями и ресурсами
    (root / "AccumulationRegisters").mkdir()
    (root / "AccumulationRegisters" / "ТоварыНаСкладах.xml").write_text(
        wrap(textwrap.dedent("""\
        <AccumulationRegister>
          <Properties>
            <Name>ТоварыНаСкладах</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Товары</v8:content></v8:item></Synonym>
            <RegisterType>Balance</RegisterType>
          </Properties>
          <ChildObjects>
            <Dimension><Properties><Name>Склад</Name><Type><v8:Type>cfg:CatalogRef.Склады</v8:Type></Type></Properties></Dimension>
            <Dimension><Properties><Name>Номенклатура</Name><Type><v8:Type>cfg:CatalogRef.Номенклатура</v8:Type></Type></Properties></Dimension>
            <Resource><Properties><Name>Количество</Name><Type><v8:Type>xs:decimal</v8:Type></Type></Properties></Resource>
          </ChildObjects>
        </AccumulationRegister>
        """)),
        encoding="utf-8",
    )
    (root / "AccumulationRegisters" / "Продажи.xml").write_text(
        wrap(textwrap.dedent("""\
        <AccumulationRegister>
          <Properties>
            <Name>Продажи</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Продажи</v8:content></v8:item></Synonym>
            <RegisterType>Turnovers</RegisterType>
          </Properties>
          <ChildObjects>
            <Dimension><Properties><Name>Контрагент</Name><Type><v8:Type>cfg:CatalogRef.Контрагенты</v8:Type></Type></Properties></Dimension>
            <Resource><Properties><Name>Сумма</Name><Type><v8:Type>xs:decimal</v8:Type></Type></Properties></Resource>
          </ChildObjects>
        </AccumulationRegister>
        """)),
        encoding="utf-8",
    )

    # InformationRegisters/КурсыВалют
    (root / "InformationRegisters").mkdir()
    (root / "InformationRegisters" / "КурсыВалют.xml").write_text(
        wrap(textwrap.dedent("""\
        <InformationRegister>
          <Properties><Name>КурсыВалют</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Курсы</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <Dimension><Properties><Name>Валюта</Name><Type><v8:Type>cfg:CatalogRef.Валюты</v8:Type></Type></Properties></Dimension>
            <Resource><Properties><Name>Курс</Name><Type><v8:Type>xs:decimal</v8:Type></Type></Properties></Resource>
          </ChildObjects>
        </InformationRegister>
        """)),
        encoding="utf-8",
    )

    # Enums/ВидыКонтрагентов
    (root / "Enums").mkdir()
    (root / "Enums" / "ВидыКонтрагентов.xml").write_text(
        wrap(textwrap.dedent("""\
        <Enum>
          <Properties><Name>ВидыКонтрагентов</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>ВК</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <EnumValue><Properties><Name>ЮридическоеЛицо</Name></Properties></EnumValue>
            <EnumValue><Properties><Name>ФизическоеЛицо</Name></Properties></EnumValue>
          </ChildObjects>
        </Enum>
        """)),
        encoding="utf-8",
    )

    # Constants/КурсРубля
    (root / "Constants").mkdir()
    (root / "Constants" / "КурсРубля.xml").write_text(
        wrap(textwrap.dedent("""\
        <Constant>
          <Properties><Name>КурсРубля</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>КР</v8:content></v8:item></Synonym>
          </Properties>
        </Constant>
        """)),
        encoding="utf-8",
    )

    store = ConfigurationMetadataStore(tmp_path / "test.db")
    store.index_configuration(root)
    return store


@pytest.fixture
def semantic_rules_dir() -> Path:
    """Реальная папка с 8 semantic rules — load и проверка что они грузятся."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "optimyzer_backend"
        / "query_analyzer"
        / "semantic_rules"
    )


@pytest.fixture
def semantic_rules(semantic_rules_dir: Path):
    rules = load_native_rules(semantic_rules_dir)
    assert len(rules) >= 8, f"Expected ≥8 semantic rules, got {len(rules)}"
    return rules


# ---- SDBL tokenizer tests ----


class TestSdblTokenizer:
    def test_extract_simple_catalog_ref(self):
        refs = extract_object_references("ВЫБРАТЬ * ИЗ Справочник.Контрагенты")
        assert len(refs) == 1
        assert refs[0].full_name == "Справочник.Контрагенты"
        assert refs[0].kind_ru == "Справочник"
        assert refs[0].name == "Контрагенты"

    def test_extract_multiple_refs(self):
        q = "ВЫБРАТЬ * ИЗ Документ.АвансовыйОтчет КАК А ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.Валюты КАК В"
        refs = extract_object_references(q)
        full_names = {r.full_name for r in refs}
        assert "Документ.АвансовыйОтчет" in full_names
        assert "Справочник.Валюты" in full_names

    def test_extract_virtual_table_ref(self):
        refs = extract_virtual_table_references(
            "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, )"
        )
        assert len(refs) == 1
        assert refs[0].full_name == "РегистрНакопления.ТоварыНаСкладах"
        assert refs[0].virtual_table == "Остатки"

    def test_extract_virtual_table_information_register(self):
        refs = extract_virtual_table_references(
            "ВЫБРАТЬ * ИЗ РегистрСведений.КурсыВалют.СрезПоследних(&Дата, )"
        )
        assert len(refs) == 1
        assert refs[0].virtual_table == "СрезПоследних"

    def test_extract_vyrazit_type(self):
        refs = extract_vyrazit_types("ВЫРАЗИТЬ(Поле КАК Справочник.Контрагенты)")
        assert len(refs) == 1
        assert refs[0].full_name == "Справочник.Контрагенты"

    def test_extract_no_refs_in_empty_query(self):
        assert extract_object_references("") == []
        assert extract_object_references("ВЫБРАТЬ 1") == []

    def test_extract_does_not_match_inside_identifier(self):
        """'МойСправочник.Х' не должен матчиться (нет word boundary)."""
        refs = extract_object_references("ВЫБРАТЬ МойСправочник.Х")
        # 'МойСправочник' содержит 'Справочник' но не как отдельное слово.
        # Lookahead должен это поймать.
        full_names = {r.full_name for r in refs}
        assert "Справочник.Х" not in full_names

    def test_offset_to_line_col_first_line(self):
        assert offset_to_line_col("ABC", 0) == (1, 1)
        assert offset_to_line_col("ABC", 1) == (1, 2)
        assert offset_to_line_col("ABC", 3) == (1, 4)

    def test_offset_to_line_col_multiline(self):
        text = "line1\nline2\nline3"
        # offset 6 = "l" в "line2" (после "line1\n")
        assert offset_to_line_col(text, 6) == (2, 1)
        # offset 12 = "l" в "line3"
        assert offset_to_line_col(text, 12) == (3, 1)


# ---- semantic rule loader ----


class TestSemanticRuleLoader:
    def test_load_minimum_8_semantic_rules(self, semantic_rules):
        assert len(semantic_rules) >= 8

    def test_all_semantic_rules_have_category_semantic(self, semantic_rules):
        for rule in semantic_rules:
            assert rule.category == "semantic", (
                f"{rule.id}: expected category=semantic, got {rule.category}"
            )

    def test_all_semantic_rules_require_configuration_metadata(self, semantic_rules):
        for rule in semantic_rules:
            assert "configuration_metadata" in rule.requires, (
                f"{rule.id}: missing requires=[configuration_metadata]"
            )

    def test_all_semantic_rules_have_check_name(self, semantic_rules):
        from optimyzer_backend.query_analyzer.semantic_checks import SEMANTIC_CHECKS

        for rule in semantic_rules:
            assert rule.check_name is not None, f"{rule.id}: no check_name"
            assert rule.check_name in SEMANTIC_CHECKS, (
                f"{rule.id}: check_name '{rule.check_name}' not in SEMANTIC_CHECKS"
            )


# ---- individual semantic checks ----


def _find_rule(rules, rule_id):
    for r in rules:
        if r.id == rule_id:
            return r
    pytest.fail(f"Rule '{rule_id}' not found in loaded semantic rules")


class TestObjectNotExists:
    def test_positive_unknown_register(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_not_exists")
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.НеСуществующий"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert findings[0].rule_id == "object_not_exists"
        assert findings[0].severity == "critical"
        assert "НеСуществующий" in findings[0].message

    def test_negative_existing_catalog(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_not_exists")
        q = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []

    def test_silent_without_config_store(self, semantic_rules):
        rule = _find_rule(semantic_rules, "object_not_exists")
        q = "ВЫБРАТЬ * ИЗ Справочник.НесуществующийДажеНаSemantic"
        # config_store=None → rule должно skip без findings
        findings = native_analyze(q, [rule], config_store=None)
        assert findings == []

    def test_silent_with_unconfig_store(self, tmp_path, semantic_rules):
        """Store существует но не is_indexed → silent skip."""
        rule = _find_rule(semantic_rules, "object_not_exists")
        empty_store = ConfigurationMetadataStore(tmp_path / "empty.db")
        assert not empty_store.is_indexed()
        q = "ВЫБРАТЬ * ИЗ Справочник.НесуществующийТовар"
        findings = native_analyze(q, [rule], config_store=empty_store)
        assert findings == []

    def test_similar_objects_suggested(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_not_exists")
        # Опечатка
        q = "ВЫБРАТЬ * ИЗ Справочник.Кантрагенты"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "Контрагенты" in findings[0].explanation_md


class TestVirtualTableNotSupported:
    def test_positive_wrong_vtable_for_register_kind(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "virtual_table_not_supported")
        # СрезПоследних на регистре накопления — недопустимо
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.СрезПоследних"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) >= 1
        # findings[0].message содержит "СрезПоследних" и "ТоварыНаСкладах"
        msg = findings[0].message
        assert "СрезПоследних" in msg
        assert "ТоварыНаСкладах" in msg

    def test_positive_turnovers_register_no_balance(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "virtual_table_not_supported")
        # 'Продажи' — Turnovers, у неё нет .Остатки
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.Продажи.Остатки(, )"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "Остатки" in findings[0].message

    def test_negative_correct_vtable(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "virtual_table_not_supported")
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, )"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


class TestVyrazitTypeNotExists:
    def test_positive_unknown_type_in_vyrazit(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "vyrazit_type_not_exists")
        q = "ВЫБРАТЬ ВЫРАЗИТЬ(Поле КАК Справочник.НетТакого)"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "Справочник.НетТакого" in findings[0].message

    def test_negative_existing_type_in_vyrazit(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "vyrazit_type_not_exists")
        q = "ВЫБРАТЬ ВЫРАЗИТЬ(Поле КАК Справочник.Контрагенты)"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


class TestRegisterDimensionMissing:
    def test_positive_filter_by_non_dimension(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "register_dimension_or_field_missing")
        # Количество — ресурс (не измерение) — фильтр в виртуалке некорректен
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, Количество = 5)"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        # Должно сработать — Количество не измерение
        assert len(findings) >= 1
        assert "Количество" in findings[0].message

    def test_negative_filter_by_dimension(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "register_dimension_or_field_missing")
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, Склад = &Скл)"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


class TestEnumValueNotExists:
    def test_positive_unknown_enum_value(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "enum_value_not_exists")
        q = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты КАК К ГДЕ К.Вид = Перечисление.ВидыКонтрагентов.ИП"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "ИП" in findings[0].message

    def test_negative_valid_enum_value(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "enum_value_not_exists")
        q = "ВЫБРАТЬ Перечисление.ВидыКонтрагентов.ЮридическоеЛицо"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


class TestAttributeNotExistsInFromAlias:
    def test_positive_unknown_attribute(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "attribute_not_exists_in_from_alias")
        q = "ВЫБРАТЬ К.НесуществующийРеквизит ИЗ Справочник.Контрагенты КАК К"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) >= 1
        msgs = [f.message for f in findings]
        assert any("НесуществующийРеквизит" in m for m in msgs)

    def test_negative_existing_attribute(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "attribute_not_exists_in_from_alias")
        q = "ВЫБРАТЬ К.ИНН ИЗ Справочник.Контрагенты КАК К"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []

    def test_negative_standard_attribute(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "attribute_not_exists_in_from_alias")
        # 'Ссылка' и 'Наименование' — стандартные, должны быть OK
        q = "ВЫБРАТЬ К.Ссылка, К.Наименование, К.Код ИЗ Справочник.Контрагенты КАК К"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


class TestRegisterResourceUsedAsDimension:
    def test_positive_resource_in_vtable_params(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "register_resource_used_as_dimension")
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, Количество = 0)"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) >= 1
        assert "Количество" in findings[0].message

    def test_negative_dimension_in_vtable_params(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "register_resource_used_as_dimension")
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, Склад = &Скл)"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


class TestObjectKindMisspelled:
    def test_plural_spravochniki(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_kind_misspelled")
        # Опечатка — множественное число "Справочники"
        q = "ВЫБРАТЬ * ИЗ Справочники.Контрагенты"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "Справочники" in findings[0].message
        assert "Справочник" in findings[0].message

    def test_plural_dokumenty(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_kind_misspelled")
        q = "ВЫБРАТЬ * ИЗ Документы.АвансовыйОтчет"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "Документы" in findings[0].message

    def test_plural_registry(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_kind_misspelled")
        q = "ВЫБРАТЬ * ИЗ РегистрыНакопления.Х"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) == 1
        assert "РегистрыНакопления" in findings[0].message
        assert "РегистрНакопления" in findings[0].message

    def test_correct_kind_no_finding(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "object_kind_misspelled")
        # Правильный тип "Справочник" (единственное число)
        q = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []

    def test_misspelled_kind_also_triggers_object_not_exists(self, synthetic_store, semantic_rules):
        """Сценарий пользователя: 'Справочники.Города1' — оба rule срабатывают.

        - object_kind_misspelled: 'Справочники' → 'Справочник'
        - object_not_exists: 'Справочник.Города1' не существует
        """
        kind_rule = _find_rule(semantic_rules, "object_kind_misspelled")
        exist_rule = _find_rule(semantic_rules, "object_not_exists")
        q = "ВЫБРАТЬ * ИЗ Справочники.Города1 КАК Города"
        findings = native_analyze(q, [kind_rule, exist_rule], config_store=synthetic_store)
        rule_ids = {f.rule_id for f in findings}
        assert "object_kind_misspelled" in rule_ids
        assert "object_not_exists" in rule_ids


class TestConstantUsedWithDot:
    def test_positive_constant_with_dot(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "constant_used_with_dot")
        q = "ВЫБРАТЬ Константа.КурсРубля.Значение"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert len(findings) >= 1
        assert "Значение" in findings[0].message
        assert "КурсРубля" in findings[0].message

    def test_negative_constant_without_dot(self, synthetic_store, semantic_rules):
        rule = _find_rule(semantic_rules, "constant_used_with_dot")
        # Константа.X сам по себе — допустимо (вернёт значение)
        q = "ВЫБРАТЬ Константа.КурсРубля"
        findings = native_analyze(q, [rule], config_store=synthetic_store)
        assert findings == []


# ---- aggregator integration ----


class TestAggregatorIntegration:
    def test_analyzer_loads_both_syntactic_and_semantic_rules(self):
        backend_dir = Path(__file__).resolve().parent.parent
        syn_dir = backend_dir / "query_analyzer_rules"
        sem_dir = (
            backend_dir
            / "src"
            / "optimyzer_backend"
            / "query_analyzer"
            / "semantic_rules"
        )
        analyzer = QueryAnalyzer(rules_dir=syn_dir, semantic_rules_dir=sem_dir)
        assert len(analyzer.native_rules) >= 13  # Sprint 4
        assert len(analyzer.semantic_rules) >= 8  # Sprint 5

    def test_analyze_returns_configuration_connected_flag(self, synthetic_store):
        backend_dir = Path(__file__).resolve().parent.parent
        syn_dir = backend_dir / "query_analyzer_rules"
        sem_dir = (
            backend_dir
            / "src"
            / "optimyzer_backend"
            / "query_analyzer"
            / "semantic_rules"
        )
        analyzer = QueryAnalyzer(rules_dir=syn_dir, semantic_rules_dir=sem_dir)
        result = analyzer.analyze(
            "ВЫБРАТЬ * ИЗ Справочник.Контрагенты", config_store=synthetic_store
        )
        assert result["configuration_connected"] is True
        result2 = analyzer.analyze("ВЫБРАТЬ * ИЗ Справочник.Контрагенты", config_store=None)
        assert result2["configuration_connected"] is False

    def test_semantic_findings_appear_when_store_connected(self, synthetic_store):
        backend_dir = Path(__file__).resolve().parent.parent
        syn_dir = backend_dir / "query_analyzer_rules"
        sem_dir = (
            backend_dir
            / "src"
            / "optimyzer_backend"
            / "query_analyzer"
            / "semantic_rules"
        )
        analyzer = QueryAnalyzer(rules_dir=syn_dir, semantic_rules_dir=sem_dir)
        result = analyzer.analyze(
            "ВЫБРАТЬ * ИЗ Справочник.НесуществующийГде",
            config_store=synthetic_store,
        )
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "object_not_exists" in rule_ids

    def test_semantic_findings_silent_without_store(self):
        backend_dir = Path(__file__).resolve().parent.parent
        syn_dir = backend_dir / "query_analyzer_rules"
        sem_dir = (
            backend_dir
            / "src"
            / "optimyzer_backend"
            / "query_analyzer"
            / "semantic_rules"
        )
        analyzer = QueryAnalyzer(rules_dir=syn_dir, semantic_rules_dir=sem_dir)
        result = analyzer.analyze(
            "ВЫБРАТЬ * ИЗ Справочник.НесуществующийГде",
            config_store=None,
        )
        rule_ids = {f["rule_id"] for f in result["findings"]}
        # Sprint 4 syntactic rules могут что-то найти, но semantic — нет
        assert "object_not_exists" not in rule_ids
        assert "virtual_table_not_supported" not in rule_ids
        assert "enum_value_not_exists" not in rule_ids

    def test_sprint4_rules_still_work_with_semantic_extension(self, synthetic_store):
        """Регрессия: Sprint 4 rules не должны сломаться от Sprint 5 расширения."""
        backend_dir = Path(__file__).resolve().parent.parent
        syn_dir = backend_dir / "query_analyzer_rules"
        sem_dir = (
            backend_dir
            / "src"
            / "optimyzer_backend"
            / "query_analyzer"
            / "semantic_rules"
        )
        analyzer = QueryAnalyzer(rules_dir=syn_dir, semantic_rules_dir=sem_dir)
        # Запрос с OR в WHERE (Sprint 4 rule or_in_where)
        q = "ВЫБРАТЬ * ИЗ Справочник.Контрагенты ГДЕ Поле = 1 ИЛИ Поле = 2"
        result = analyzer.analyze(q, config_store=synthetic_store)
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "or_in_where" in rule_ids
