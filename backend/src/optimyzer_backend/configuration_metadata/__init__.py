"""Sprint 5 — Configuration Metadata: парсер XML выгрузки конфигурации 1С
и SQLite-индекс для семантической валидации запросов.

Состав:
    parser.py — XML парсер выгрузки (stdlib xml.etree.ElementTree)
    store.py  — SQLite индекс с hash-based invalidation
    api.py    — high-level API для query analyzer

ADR-029 (persistence в SQLite) и ADR-030 (только стандартная Python-библиотека).
"""

from optimyzer_backend.configuration_metadata.parser import (
    Attribute,
    ConfigurationObject,
    ConfigurationParser,
    TabularSection,
    FOLDER_TO_ROOT_TAG,
    ROOT_TAG_TO_KIND_RU,
)
from optimyzer_backend.configuration_metadata.store import ConfigurationMetadataStore
from optimyzer_backend.configuration_metadata.api import (
    get_default_store,
    get_default_db_path,
)

__all__ = [
    "Attribute",
    "ConfigurationObject",
    "ConfigurationParser",
    "ConfigurationMetadataStore",
    "TabularSection",
    "FOLDER_TO_ROOT_TAG",
    "ROOT_TAG_TO_KIND_RU",
    "get_default_store",
    "get_default_db_path",
]
