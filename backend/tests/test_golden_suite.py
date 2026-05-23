"""Sprint 5 Phase E — Golden test suite runner.

Параметризованный pytest runner который проходит по всем папкам
`tests/golden/queries/{positive,negative,edge_cases,semantic}/NN_name/`
и валидирует results анализатора против `expected.json`.

DoD #17: минимум 30 cases (10 positive + 10 negative + 10 edge).
DoD #18: минимум 5 semantic cases.
DoD #19: pytest runner с параметризацией.

Semantic cases используют общий synthetic config store-fixture
(БП-подобный с Контрагенты / ТоварыНаСкладах / ВидыКонтрагентов /
КурсРубля), такой же как в test_semantic_rules.py.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from optimyzer_backend.configuration_metadata import ConfigurationMetadataStore
from optimyzer_backend.query_analyzer.aggregator import QueryAnalyzer


GOLDEN_ROOT = Path(__file__).parent / "golden" / "queries"
BACKEND_DIR = Path(__file__).resolve().parent.parent

SYNTACTIC_RULES_DIR = BACKEND_DIR / "query_analyzer_rules"
SEMANTIC_RULES_DIR = (
    BACKEND_DIR
    / "src"
    / "optimyzer_backend"
    / "query_analyzer"
    / "semantic_rules"
)


def _collect_golden_cases():
    """Собирает все папки с query.sdbl + expected.json."""
    cases: list[tuple[str, str, Path, Path]] = []
    if not GOLDEN_ROOT.is_dir():
        return cases
    for category in ["positive", "negative", "edge_cases", "semantic", "real_world"]:
        category_path = GOLDEN_ROOT / category
        if not category_path.is_dir():
            continue
        for case_dir in sorted(category_path.iterdir()):
            if not case_dir.is_dir():
                continue
            query_file = case_dir / "query.sdbl"
            expected_file = case_dir / "expected.json"
            if query_file.exists() and expected_file.exists():
                cases.append((category, case_dir.name, query_file, expected_file))
    return cases


# Fixture: synthetic configuration для semantic cases
NAMESPACES = (
    'xmlns="http://v8.1c.ru/8.3/MDClasses" '
    'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
    'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)


def _wrap(inner: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<MetaDataObject {NAMESPACES}>\n{inner}\n</MetaDataObject>\n'


@pytest.fixture(scope="module")
def golden_test_config_store(tmp_path_factory) -> ConfigurationMetadataStore:
    """Конфигурация для semantic golden cases — БП-подобная.

    Содержит:
    - Справочник.Контрагенты (с реквизитом ВидКонтрагента)
    - Справочник.Валюты
    - РегистрНакопления.ТоварыНаСкладах (Balance — для virtual_table тестов)
    - Перечисление.ВидыКонтрагентов (со значениями ЮридическоеЛицо/ФизическоеЛицо/ИП)
    - Константа.КурсРубля (для constant_used_with_dot)
    """
    tmp_path = tmp_path_factory.mktemp("golden_config")
    root = tmp_path / "dump"
    root.mkdir()
    (root / "Configuration.xml").write_text(
        _wrap(textwrap.dedent("""\
        <Configuration>
          <Properties>
            <Name>GoldenTestConfig</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Golden</v8:content></v8:item></Synonym>
            <Vendor>Optimyzer Tests</Vendor>
            <Version>1.0</Version>
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
            <Attribute><Properties>
              <Name>ИНН</Name><Type><v8:Type>xs:string</v8:Type></Type>
            </Properties></Attribute>
            <Attribute><Properties>
              <Name>ВидКонтрагента</Name><Type><v8:Type>cfg:EnumRef.ВидыКонтрагентов</v8:Type></Type>
            </Properties></Attribute>
          </ChildObjects>
        </Catalog>
        """)),
        encoding="utf-8",
    )
    (root / "Catalogs" / "Валюты.xml").write_text(
        _wrap(textwrap.dedent("""\
        <Catalog>
          <Properties><Name>Валюты</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>В</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <Attribute><Properties><Name>Код</Name><Type><v8:Type>xs:string</v8:Type></Type></Properties></Attribute>
          </ChildObjects>
        </Catalog>
        """)),
        encoding="utf-8",
    )
    (root / "AccumulationRegisters").mkdir()
    (root / "AccumulationRegisters" / "ТоварыНаСкладах.xml").write_text(
        _wrap(textwrap.dedent("""\
        <AccumulationRegister>
          <Properties><Name>ТоварыНаСкладах</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>ТНС</v8:content></v8:item></Synonym>
            <RegisterType>Balance</RegisterType>
          </Properties>
          <ChildObjects>
            <Dimension><Properties><Name>Склад</Name><Type><v8:Type>cfg:CatalogRef.Склады</v8:Type></Type></Properties></Dimension>
            <Resource><Properties><Name>Количество</Name><Type><v8:Type>xs:decimal</v8:Type></Type></Properties></Resource>
          </ChildObjects>
        </AccumulationRegister>
        """)),
        encoding="utf-8",
    )
    (root / "Enums").mkdir()
    (root / "Enums" / "ВидыКонтрагентов.xml").write_text(
        _wrap(textwrap.dedent("""\
        <Enum>
          <Properties><Name>ВидыКонтрагентов</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>ВК</v8:content></v8:item></Synonym>
          </Properties>
          <ChildObjects>
            <EnumValue><Properties><Name>ЮридическоеЛицо</Name></Properties></EnumValue>
            <EnumValue><Properties><Name>ФизическоеЛицо</Name></Properties></EnumValue>
            <EnumValue><Properties><Name>ИндивидуальныйПредприниматель</Name></Properties></EnumValue>
          </ChildObjects>
        </Enum>
        """)),
        encoding="utf-8",
    )
    (root / "Constants").mkdir()
    (root / "Constants" / "КурсРубля.xml").write_text(
        _wrap(textwrap.dedent("""\
        <Constant>
          <Properties><Name>КурсРубля</Name>
            <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>КР</v8:content></v8:item></Synonym>
          </Properties>
        </Constant>
        """)),
        encoding="utf-8",
    )
    store = ConfigurationMetadataStore(tmp_path / "golden.db")
    store.index_configuration(root)
    return store


@pytest.fixture(scope="module")
def analyzer() -> QueryAnalyzer:
    return QueryAnalyzer(
        rules_dir=SYNTACTIC_RULES_DIR,
        semantic_rules_dir=SEMANTIC_RULES_DIR,
    )


# ---- DoD checks ----


class TestGoldenSuiteCounts:
    """DoD проверки на размер golden suite (быстрая sanity)."""

    def test_minimum_30_total_basic_cases(self):
        """DoD #17: ≥30 cases в positive + negative + edge_cases."""
        cases = _collect_golden_cases()
        basic = [c for c in cases if c[0] in ("positive", "negative", "edge_cases")]
        assert len(basic) >= 30, f"DoD #17 fail: got {len(basic)} basic cases"

    def test_minimum_5_semantic_cases(self):
        """DoD #18: ≥5 semantic cases."""
        cases = _collect_golden_cases()
        semantic = [c for c in cases if c[0] == "semantic"]
        assert len(semantic) >= 5, f"DoD #18 fail: got {len(semantic)} semantic cases"

    def test_each_case_has_valid_expected_json(self):
        """Каждый expected.json должен парситься как валидный JSON со списком findings."""
        for category, name, _, expected_file in _collect_golden_cases():
            try:
                data = json.loads(expected_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                pytest.fail(f"{category}/{name}/expected.json: invalid JSON: {exc}")
            assert "findings" in data, f"{category}/{name}: missing 'findings' key"
            assert isinstance(data["findings"], list), (
                f"{category}/{name}: 'findings' must be list"
            )


# ---- Main parametrized runner ----


@pytest.mark.parametrize(
    "category, name, query_file, expected_file",
    _collect_golden_cases(),
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_golden_case(
    category: str,
    name: str,
    query_file: Path,
    expected_file: Path,
    analyzer: QueryAnalyzer,
    golden_test_config_store: ConfigurationMetadataStore,
):
    """Каждый golden case прогоняется через analyzer и проверяется."""
    query_text = query_file.read_text(encoding="utf-8")
    expected = json.loads(expected_file.read_text(encoding="utf-8"))

    requires_config = expected.get("requires_configuration", False)
    store = golden_test_config_store if requires_config else None

    result = analyzer.analyze(query_text, config_store=store)
    actual_findings = result["findings"]
    actual_rule_ids = {f["rule_id"] for f in actual_findings}

    expected_findings = expected["findings"]
    expected_rule_ids = {f["rule_id"] for f in expected_findings}

    # 1. Все expected rules должны найтись
    missing = expected_rule_ids - actual_rule_ids
    if missing:
        pytest.fail(
            f"{category}/{name}: missing expected findings: {sorted(missing)}. "
            f"Actual findings: {sorted(actual_rule_ids)}"
        )

    # 2. Для negative cases — НЕ должно быть critical/warning findings
    if category == "negative":
        bad = [
            f for f in actual_findings
            if f["severity"] in ("critical", "warning")
        ]
        if bad:
            pytest.fail(
                f"{category}/{name}: unexpected critical/warning findings: "
                f"{[(f['rule_id'], f['severity']) for f in bad]}"
            )
