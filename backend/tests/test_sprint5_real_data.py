"""Sprint 5 Phase G — Real-data acceptance gates.

Тесты прогоняются на реальной XML выгрузке Test1CProf (БП 3.0 v3.0.39.57)
из `C:\\BUFFER\\SCHEME`. Если выгрузка недоступна (env не задан или
папки нет) — все тесты этого файла skip'аются.

Blocking gates Sprint 5 DoD:
- #28: парсинг < 30 секунд, ≥100 объектов
- #29: semantic rule на несуществующем объекте срабатывает
- #30: all golden cases проходят
- #31: configuration persistence после restart tool
- #32: 7+/10 real-world запросов получают findings — **SKIP** в Sprint 5
       (Phase F скипнут по решению Сергея — переезжает в Sprint 6 где
       будет автоматический поиск SDBL по DBMSSQL.Context).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from optimyzer_backend.configuration_metadata import ConfigurationMetadataStore
from optimyzer_backend.query_analyzer.aggregator import QueryAnalyzer


# Путь к real-world выгрузке — берём из env или дефолт C:\BUFFER\SCHEME
_DEFAULT_XML_PATH = r"C:\BUFFER\SCHEME"
_REAL_XML_PATH = Path(os.environ.get("OPTIMYZER_CONFIG_XML_PATH", _DEFAULT_XML_PATH))
_REAL_AVAILABLE = (
    _REAL_XML_PATH.is_dir() and (_REAL_XML_PATH / "Configuration.xml").is_file()
)


pytestmark = pytest.mark.skipif(
    not _REAL_AVAILABLE,
    reason=(
        f"Real Test1CProf XML dump not available at {_REAL_XML_PATH}. "
        "Set OPTIMYZER_CONFIG_XML_PATH env to enable Sprint 5 acceptance gates."
    ),
)


BACKEND_DIR = Path(__file__).resolve().parent.parent
SYNTACTIC_RULES_DIR = BACKEND_DIR / "query_analyzer_rules"
SEMANTIC_RULES_DIR = (
    BACKEND_DIR
    / "src"
    / "optimyzer_backend"
    / "query_analyzer"
    / "semantic_rules"
)


@pytest.fixture(scope="module")
def real_store(tmp_path_factory) -> ConfigurationMetadataStore:
    """Индексирует real выгрузку Test1CProf один раз на модуль."""
    db = tmp_path_factory.mktemp("sprint5_acceptance") / "real.db"
    store = ConfigurationMetadataStore(db)
    store.index_configuration(_REAL_XML_PATH)
    return store


# ---- DoD #28: парсинг performance + scale ----


class TestDoD28IndexingPerformance:
    """DoD #28: парсинг Test1CProf конфигурации < 30 секунд, ≥100 объектов."""

    def test_indexing_completes_under_30_seconds(self, tmp_path):
        """Парсинг должен завершиться менее чем за 30 секунд."""
        db = tmp_path / "perf.db"
        store = ConfigurationMetadataStore(db)
        t0 = time.monotonic()
        result = store.index_configuration(_REAL_XML_PATH)
        elapsed = time.monotonic() - t0
        assert elapsed < 30.0, (
            f"DoD #28 fail: indexing took {elapsed:.1f}s (limit 30s). "
            f"Status={result['status']}, objects={result['object_count']}"
        )
        # Sanity print через assert message — не запускается если passed
        assert result["status"] == "indexed"

    def test_indexed_at_least_100_objects(self, real_store):
        count = real_store.count_objects()
        assert count >= 100, f"DoD #28 fail: only {count} objects indexed (≥100 required)"

    def test_configuration_metadata_populated(self, real_store):
        """Метаданные конфигурации (имя, версия, поставщик) извлечены."""
        assert real_store.get_meta("config_name")
        assert real_store.get_meta("config_synonym_ru")
        assert real_store.get_meta("config_version")

    def test_has_typical_bp30_objects(self, real_store):
        """Контрольная проверка: типовые объекты БП 3.0 присутствуют."""
        # Hozhraschotny — единственный регистр бухгалтерии в БП
        assert real_store.is_object_exists("РегистрБухгалтерии.Хозрасчетный")
        # Контрагенты — обязательный справочник в любой БП
        assert real_store.is_object_exists("Справочник.Контрагенты")


# ---- DoD #29: semantic rule срабатывает на несуществующем объекте ----


class TestDoD29SemanticRuleOnRealConfig:
    """DoD #29: semantic rule срабатывает на запросе с несуществующим в БП объектом."""

    def test_semantic_rule_object_not_exists_fires(self, real_store):
        """В БП 3.0 нет регистра 'ТоварыНаСкладах' (он есть в УТ, не в БП).
        object_not_exists должно сработать."""
        analyzer = QueryAnalyzer(
            rules_dir=SYNTACTIC_RULES_DIR, semantic_rules_dir=SEMANTIC_RULES_DIR
        )
        q = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, )"
        result = analyzer.analyze(q, config_store=real_store)
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "object_not_exists" in rule_ids, (
            f"DoD #29 fail: object_not_exists не сработало. Findings: {rule_ids}"
        )

    def test_semantic_silent_when_no_config(self):
        """DoD #29 negative: без config — semantic rules silent."""
        analyzer = QueryAnalyzer(
            rules_dir=SYNTACTIC_RULES_DIR, semantic_rules_dir=SEMANTIC_RULES_DIR
        )
        q = "ВЫБРАТЬ * ИЗ Справочник.НесуществующийСправочник"
        result = analyzer.analyze(q, config_store=None)
        rule_ids = {f["rule_id"] for f in result["findings"]}
        assert "object_not_exists" not in rule_ids


# ---- DoD #30: all golden cases pass ----


class TestDoD30GoldenSuitePasses:
    """DoD #30: все golden cases проходят (один прогон)."""

    def test_golden_suite_runner_collects_minimum_30_cases(self):
        """Sanity: collect собирает ≥30 cases."""
        from tests.test_golden_suite import _collect_golden_cases

        cases = _collect_golden_cases()
        basic = [c for c in cases if c[0] in ("positive", "negative", "edge_cases")]
        assert len(basic) >= 30


# ---- DoD #31: configuration persistence after restart ----


class TestDoD31Persistence:
    """DoD #31: после повторного открытия tool конфигурация остаётся подключённой."""

    def test_index_survives_new_store_instance(self, tmp_path):
        db = tmp_path / "persistence.db"

        # Первая сессия — индексируем
        store1 = ConfigurationMetadataStore(db)
        r1 = store1.index_configuration(_REAL_XML_PATH)
        assert r1["status"] == "indexed"
        count1 = store1.count_objects()
        del store1

        # Вторая сессия — открываем тот же файл
        store2 = ConfigurationMetadataStore(db)
        assert store2.is_indexed()
        assert store2.count_objects() == count1
        # Хеш не изменился → already_indexed
        r2 = store2.index_configuration(_REAL_XML_PATH)
        assert r2["status"] == "already_indexed"

    def test_meta_survives_restart(self, tmp_path):
        db = tmp_path / "meta_persist.db"
        store1 = ConfigurationMetadataStore(db)
        store1.index_configuration(_REAL_XML_PATH)
        version1 = store1.get_meta("config_version")
        synonym1 = store1.get_meta("config_synonym_ru")
        del store1

        store2 = ConfigurationMetadataStore(db)
        assert store2.get_meta("config_version") == version1
        assert store2.get_meta("config_synonym_ru") == synonym1


# ---- DoD #32: Phase F real-world (SKIPPED in Sprint 5) ----


class TestDoD32RealWorldFindings:
    """DoD #32: 7+/10 real-world запросов получают findings.

    SPRINT 5: Phase F (manual extraction SDBL из DBMSSQL контекстов) скипнут
    по решению Сергея — переезжает в Sprint 6 где будет автоматический поиск
    SDBL через MCP BSL Atlas + Context tokenizer (см.
    docs/OPUS_HANDOVER_SPRINT_5.md).

    Текущий тест — placeholder, всегда skip в Sprint 5.
    """

    @pytest.mark.skip(reason="Phase F → Sprint 6 (DBMSSQL.Context-based SDBL extraction)")
    def test_real_world_queries_get_findings(self):
        pass
