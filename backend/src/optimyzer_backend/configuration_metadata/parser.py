"""XML парсер выгрузки конфигурации 1С (Sprint 5 Phase A).

Парсит выгрузку из Конфигуратора (например `C:\\BUFFER\\SCHEME`) и
строит in-memory модель метаданных. Использует только стандартную
библиотеку `xml.etree.ElementTree` (ADR-030).

Формат выгрузки задокументирован в docs/CONFIGURATION_XML_FORMAT_STUDY.md
(Phase 0 deliverable).

Парсер игнорирует non-queryable типы (CommonModules, CommonPictures,
Roles, и т.п.) — они не упоминаются в SDBL и не нужны для семантической
валидации.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


# Маппинг: корневой XML-тег объекта → русский тип (как в SDBL)
ROOT_TAG_TO_KIND_RU: dict[str, str] = {
    "Catalog": "Справочник",
    "Document": "Документ",
    "AccumulationRegister": "РегистрНакопления",
    "InformationRegister": "РегистрСведений",
    "AccountingRegister": "РегистрБухгалтерии",
    "CalculationRegister": "РегистрРасчета",
    "ChartOfAccounts": "ПланСчетов",
    "ChartOfCharacteristicTypes": "ПланВидовХарактеристик",
    "ChartOfCalculationTypes": "ПланВидовРасчета",
    "Enum": "Перечисление",
    "DocumentJournal": "ЖурналДокументов",
    "Constant": "Константа",
    "ExchangePlan": "ПланОбмена",
    "Sequence": "Последовательность",
    "BusinessProcess": "БизнесПроцесс",
    "Task": "Задача",
}

# Маппинг: имя корневой папки выгрузки → корневой XML-тег
FOLDER_TO_ROOT_TAG: dict[str, str] = {
    "Catalogs": "Catalog",
    "Documents": "Document",
    "AccumulationRegisters": "AccumulationRegister",
    "InformationRegisters": "InformationRegister",
    "AccountingRegisters": "AccountingRegister",
    "CalculationRegisters": "CalculationRegister",
    "ChartsOfAccounts": "ChartOfAccounts",
    "ChartsOfCharacteristicTypes": "ChartOfCharacteristicTypes",
    "ChartsOfCalculationTypes": "ChartOfCalculationTypes",
    "Enums": "Enum",
    "DocumentJournals": "DocumentJournal",
    "Constants": "Constant",
    "ExchangePlans": "ExchangePlan",
    "Sequences": "Sequence",
    "BusinessProcesses": "BusinessProcess",
    "Tasks": "Task",
}


# Виртуальные таблицы по типу регистра. Используется для проверок
# семантических правил (Sprint 5 Phase B) — например, что
# 'РегистрНакопления.X.Обороты' валиден если X имеет RegisterType=Balance
# или Turnovers, а 'РегистрНакопления.X.СрезПоследних' — НЕ валиден.
VIRTUAL_TABLES_BY_KIND_AND_TYPE: dict[tuple[str, str | None], list[str]] = {
    ("РегистрНакопления", "Balance"): ["Остатки", "Обороты", "ОстаткиИОбороты"],
    ("РегистрНакопления", "Turnovers"): ["Обороты"],
    ("РегистрСведений", None): ["СрезПоследних", "СрезПервых"],
    ("РегистрБухгалтерии", None): [
        "Остатки",
        "Обороты",
        "ОстаткиИОбороты",
        "ДвиженияССубконто",
        "ОборотыДтКт",
    ],
    ("РегистрРасчета", None): [
        "БазаДанных",
        "ДанныеГрафика",
        "ФактическийПериодДействия",
    ],
}


@dataclass
class Attribute:
    """Реквизит / измерение / ресурс."""

    name: str
    type_repr: str = ""  # компактная строка типа: 'xs:string', 'cfg:CatalogRef.X', и т.п.

    def to_dict(self) -> dict:
        return {"name": self.name, "type_repr": self.type_repr}


@dataclass
class TabularSection:
    """Табличная часть объекта."""

    name: str
    attributes: list[Attribute] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "attributes": [a.to_dict() for a in self.attributes]}


@dataclass
class ConfigurationObject:
    """Один объект конфигурации (Справочник.Контрагенты, и т.п.)."""

    kind_ru: str  # "Справочник", "Документ", "РегистрНакопления", ...
    name: str  # "Контрагенты"
    synonym_ru: str = ""
    register_type: str | None = None  # для AccumulationRegister: "Balance"/"Turnovers"
    attributes: list[Attribute] = field(default_factory=list)
    dimensions: list[Attribute] = field(default_factory=list)
    resources: list[Attribute] = field(default_factory=list)
    tabular_sections: list[TabularSection] = field(default_factory=list)
    enum_values: list[str] = field(default_factory=list)
    # Имена ПРЕДОПРЕДЕЛЁННЫХ элементов: для Справочник / ПланСчетов /
    # ПланВидовХарактеристик / ПланВидовРасчета — список из Predefined.xml.
    # Используется правилом `predefined_item_not_exists` для валидации
    # обращений `ЗНАЧЕНИЕ(Справочник.X.ИмяЭлемента)`. Для Перечисления
    # предопределённые значения хранятся в enum_values (отдельное правило).
    predefined_names: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """SDBL-имя объекта: 'Справочник.Контрагенты'."""
        return f"{self.kind_ru}.{self.name}"

    @property
    def virtual_tables(self) -> list[str]:
        """Список SDBL-имён виртуальных таблиц этого объекта (для регистров)."""
        key = (self.kind_ru, self.register_type)
        if key in VIRTUAL_TABLES_BY_KIND_AND_TYPE:
            return list(VIRTUAL_TABLES_BY_KIND_AND_TYPE[key])
        # Для регистров где register_type не учитывается — пробуем по kind
        key2 = (self.kind_ru, None)
        if key2 in VIRTUAL_TABLES_BY_KIND_AND_TYPE:
            return list(VIRTUAL_TABLES_BY_KIND_AND_TYPE[key2])
        return []

    def attribute_names(self) -> set[str]:
        """Все имена реквизитов (без измерений/ресурсов)."""
        return {a.name for a in self.attributes}

    def dimension_names(self) -> set[str]:
        return {d.name for d in self.dimensions}

    def resource_names(self) -> set[str]:
        return {r.name for r in self.resources}

    def tabular_section_names(self) -> set[str]:
        return {ts.name for ts in self.tabular_sections}

    def to_dict(self) -> dict:
        return {
            "kind_ru": self.kind_ru,
            "name": self.name,
            "full_name": self.full_name,
            "synonym_ru": self.synonym_ru,
            "register_type": self.register_type,
            "attributes": [a.to_dict() for a in self.attributes],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "resources": [r.to_dict() for r in self.resources],
            "tabular_sections": [ts.to_dict() for ts in self.tabular_sections],
            "enum_values": list(self.enum_values),
            "predefined_names": list(self.predefined_names),
            "virtual_tables": self.virtual_tables,
        }


# ---- internal XML helpers ----

def _localname(tag: str) -> str:
    """Извлечь local name из namespaced tag: '{ns}Catalog' → 'Catalog'."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    return (elem.text or "").strip()


def _direct_child(parent: ET.Element, local_name: str) -> ET.Element | None:
    """Поиск ПРЯМОГО ребёнка по local name (без рекурсии)."""
    for child in parent:
        if _localname(child.tag) == local_name:
            return child
    return None


def _direct_children(parent: ET.Element, local_name: str) -> Iterable[ET.Element]:
    for child in parent:
        if _localname(child.tag) == local_name:
            yield child


def _extract_synonym_ru(props: ET.Element) -> str:
    """Извлечь русский синоним из <Synonym><v8:item>...</v8:item></Synonym>."""
    syn = _direct_child(props, "Synonym")
    if syn is None:
        return ""
    for item in _direct_children(syn, "item"):
        lang = ""
        content = ""
        for sub in item:
            local = _localname(sub.tag)
            if local == "lang":
                lang = _text(sub)
            elif local == "content":
                content = _text(sub)
        if lang == "ru" and content:
            return content
    return ""


def _extract_type_repr(props: ET.Element) -> str:
    """Извлечь компактное представление типа реквизита."""
    type_node = _direct_child(props, "Type")
    if type_node is None:
        return ""
    parts: list[str] = []
    for sub in type_node:
        if _localname(sub.tag) == "Type":
            txt = _text(sub)
            if txt:
                parts.append(txt)
    return " | ".join(parts)


def _parse_attr_like(elem: ET.Element) -> Attribute:
    """Парсит элемент Attribute / Dimension / Resource — одинаковая структура."""
    props = _direct_child(elem, "Properties")
    if props is None:
        return Attribute(name="", type_repr="")
    name = _text(_direct_child(props, "Name"))
    type_repr = _extract_type_repr(props)
    return Attribute(name=name, type_repr=type_repr)


def _parse_tabular_section(elem: ET.Element) -> TabularSection | None:
    """Парсит <TabularSection> с вложенным <ChildObjects><Attribute>."""
    props = _direct_child(elem, "Properties")
    if props is None:
        return None
    name = _text(_direct_child(props, "Name"))
    if not name:
        return None
    ts_attrs: list[Attribute] = []
    childs = _direct_child(elem, "ChildObjects")
    if childs is not None:
        for sub in _direct_children(childs, "Attribute"):
            ts_attrs.append(_parse_attr_like(sub))
    return TabularSection(name=name, attributes=ts_attrs)


# ---- ConfigurationParser ----


class ConfigurationParserError(Exception):
    """Ошибка парсинга выгрузки конфигурации."""


class ConfigurationParser:
    """Парсер всей выгрузки конфигурации.

    Использование::

        parser = ConfigurationParser(Path("C:/BUFFER/SCHEME"))
        objects = parser.parse()
        # → list[ConfigurationObject]
    """

    def __init__(self, root_path: Path) -> None:
        self.root_path = Path(root_path)
        if not self.root_path.is_dir():
            raise ConfigurationParserError(f"Not a directory: {self.root_path}")
        if not (self.root_path / "Configuration.xml").is_file():
            raise ConfigurationParserError(
                f"No Configuration.xml in {self.root_path} — это не выгрузка 1С"
            )

    def get_configuration_info(self) -> dict[str, str]:
        """Парсит корневой Configuration.xml — Name + Synonym + Vendor + Version."""
        config_xml = self.root_path / "Configuration.xml"
        try:
            tree = ET.parse(config_xml)
        except ET.ParseError as exc:
            raise ConfigurationParserError(f"Bad Configuration.xml: {exc}")
        md_root = tree.getroot()
        if _localname(md_root.tag) != "MetaDataObject":
            raise ConfigurationParserError("Configuration.xml: not a MetaDataObject")
        cfg_elem = None
        for child in md_root:
            if _localname(child.tag) == "Configuration":
                cfg_elem = child
                break
        if cfg_elem is None:
            raise ConfigurationParserError("Configuration.xml: no <Configuration> child")
        props = _direct_child(cfg_elem, "Properties")
        if props is None:
            return {"name": "", "synonym_ru": "", "vendor": "", "version": ""}
        return {
            "name": _text(_direct_child(props, "Name")),
            "synonym_ru": _extract_synonym_ru(props),
            "vendor": _text(_direct_child(props, "Vendor")),
            "version": _text(_direct_child(props, "Version")),
        }

    def parse(self) -> list[ConfigurationObject]:
        """Парсит все queryable объекты выгрузки.

        Игнорирует папки которые НЕ соответствуют queryable типам
        (CommonModules, CommonPictures, Roles, и т.п.). Файлы которые
        не удалось распарсить — пропускаются с warning в лог.
        """
        objects: list[ConfigurationObject] = []
        for folder_name, root_tag in FOLDER_TO_ROOT_TAG.items():
            folder = self.root_path / folder_name
            if not folder.is_dir():
                continue
            kind_ru = ROOT_TAG_TO_KIND_RU[root_tag]
            for xml_file in sorted(folder.glob("*.xml")):
                try:
                    obj = self._parse_object_file(xml_file, root_tag, kind_ru)
                    if obj is not None:
                        objects.append(obj)
                except ET.ParseError as exc:
                    logger.warning("Skip %s: ParseError: %s", xml_file.name, exc)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skip %s: %s: %s", xml_file.name, type(exc).__name__, exc)
        return objects

    # Типы, у которых имеет смысл искать Predefined.xml. Регистры, перечисления,
    # документы и т.п. предопределённых элементов в этом смысле не имеют.
    _PREDEFINED_KINDS_RU = frozenset({
        "Справочник",
        "ПланСчетов",
        "ПланВидовХарактеристик",
        "ПланВидовРасчета",
    })

    def _parse_predefined_names(self, xml_path: Path, kind_ru: str, name: str) -> list[str]:
        """Извлекает имена предопределённых элементов из Ext/Predefined.xml.

        Predefined.xml лежит рядом с описанием объекта по пути
        ``<Folder>/<Name>/Ext/Predefined.xml``. Содержимое — дерево
        ``<Item><Name>...</Name><ChildItems><Item>...</Item></ChildItems></Item>``.

        Возвращает плоский список имён (включая вложенные). Если файла нет
        или это не подходящий тип объекта — пустой список.
        """
        if kind_ru not in self._PREDEFINED_KINDS_RU:
            return []
        # xml_path = <root>/<Folder>/<Name>.xml; Predefined.xml — рядом
        predefined_path = xml_path.parent / name / "Ext" / "Predefined.xml"
        if not predefined_path.is_file():
            return []
        try:
            tree = ET.parse(predefined_path)
        except ET.ParseError as exc:
            logger.warning("Skip Predefined.xml %s: %s", predefined_path, exc)
            return []
        names: list[str] = []
        # Корневой элемент <PredefinedData> (или другой) → рекурсивно собираем
        # все локальные <Name> прямых детей <Item>.
        for item in self._iter_items_recursive(tree.getroot()):
            for child in item:
                if _localname(child.tag) == "Name":
                    txt = _text(child)
                    if txt:
                        names.append(txt)
                    break
        return names

    def _iter_items_recursive(self, elem: ET.Element) -> Iterable[ET.Element]:
        """DFS по всем <Item> в произвольной глубине (учитывая <ChildItems>)."""
        for child in elem:
            if _localname(child.tag) == "Item":
                yield child
                yield from self._iter_items_recursive(child)
            else:
                # ChildItems и другие промежуточные обёртки
                yield from self._iter_items_recursive(child)

    def _parse_object_file(
        self, xml_path: Path, expected_root_tag: str, kind_ru: str
    ) -> ConfigurationObject | None:
        """Парсит один XML-файл объекта конфигурации."""
        tree = ET.parse(xml_path)
        md_root = tree.getroot()
        if _localname(md_root.tag) != "MetaDataObject":
            return None
        obj_elem = None
        for child in md_root:
            if _localname(child.tag) == expected_root_tag:
                obj_elem = child
                break
        if obj_elem is None:
            return None

        props = _direct_child(obj_elem, "Properties")
        if props is None:
            return None

        name = _text(_direct_child(props, "Name"))
        if not name:
            return None

        synonym_ru = _extract_synonym_ru(props)
        register_type_el = _direct_child(props, "RegisterType")
        register_type = _text(register_type_el) if register_type_el is not None else None
        if register_type == "":
            register_type = None

        attributes: list[Attribute] = []
        dimensions: list[Attribute] = []
        resources: list[Attribute] = []
        tabular_sections: list[TabularSection] = []
        enum_values: list[str] = []

        childs = _direct_child(obj_elem, "ChildObjects")
        if childs is not None:
            for child in childs:
                local = _localname(child.tag)
                if local == "Attribute":
                    attributes.append(_parse_attr_like(child))
                elif local == "Dimension":
                    dimensions.append(_parse_attr_like(child))
                elif local == "Resource":
                    resources.append(_parse_attr_like(child))
                elif local == "EnumValue":
                    ev_props = _direct_child(child, "Properties")
                    if ev_props is not None:
                        ev_name = _text(_direct_child(ev_props, "Name"))
                        if ev_name:
                            enum_values.append(ev_name)
                elif local == "TabularSection":
                    ts = _parse_tabular_section(child)
                    if ts is not None:
                        tabular_sections.append(ts)

        predefined_names = self._parse_predefined_names(xml_path, kind_ru, name)

        return ConfigurationObject(
            kind_ru=kind_ru,
            name=name,
            synonym_ru=synonym_ru,
            register_type=register_type,
            attributes=attributes,
            dimensions=dimensions,
            resources=resources,
            tabular_sections=tabular_sections,
            enum_values=enum_values,
            predefined_names=predefined_names,
        )
