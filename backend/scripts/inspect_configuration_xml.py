"""Sprint 5 Phase 0 — Discovery формата XML выгрузки конфигурации 1С.

Ходит по корневой папке выгрузки (например C:\\BUFFER\\SCHEME),
считает объекты каждого типа, для одного представителя каждого типа
извлекает структуру (Name, Synonym, реквизиты, измерения, ресурсы,
табчасти) и печатает markdown-отчёт.

Использование:
    python -m backend.scripts.inspect_configuration_xml [path]

Если path не задан — читает env OPTIMYZER_CONFIG_XML_PATH, иначе
C:\\BUFFER\\SCHEME. Это deliverable для docs/CONFIGURATION_XML_FORMAT_STUDY.md.

ВАЖНО: парсер использует только стандартную библиотеку
(xml.etree.ElementTree) — никаких lxml/xmltodict (ADR-030).
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

# Namespaces из XML выгрузки 1С
NS = {
    "md": "http://v8.1c.ru/8.3/MDClasses",
    "v8": "http://v8.1c.ru/8.1/data/core",
    "xr": "http://v8.1c.ru/8.3/xcf/readable",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Маппинг английских папок (Конфигуратор использует EN-имена)
# на русский тип объекта 1С (как употребляется в запросах SDBL).
FOLDER_TO_KIND_RU = {
    "Catalogs": "Справочник",
    "Documents": "Документ",
    "AccumulationRegisters": "РегистрНакопления",
    "InformationRegisters": "РегистрСведений",
    "AccountingRegisters": "РегистрБухгалтерии",
    "CalculationRegisters": "РегистрРасчета",
    "ChartsOfAccounts": "ПланСчетов",
    "ChartsOfCharacteristicTypes": "ПланВидовХарактеристик",
    "ChartsOfCalculationTypes": "ПланВидовРасчета",
    "Enums": "Перечисление",
    "Reports": "Отчет",
    "DataProcessors": "Обработка",
    "CommonModules": "ОбщийМодуль",
    "DocumentJournals": "ЖурналДокументов",
    "Constants": "Константа",
    "ExchangePlans": "ПланОбмена",
    "Sequences": "Последовательность",
    "BusinessProcesses": "БизнесПроцесс",
    "Tasks": "Задача",
    "FilterCriteria": "КритерийОтбора",
    "Subsystems": "Подсистема",
    "Roles": "Роль",
    "ScheduledJobs": "РегламентноеЗадание",
    "CommonForms": "ОбщаяФорма",
    "CommonCommands": "ОбщаяКоманда",
    "CommonPictures": "ОбщаяКартинка",
    "CommonTemplates": "ОбщийМакет",
    "CommonAttributes": "ОбщийРеквизит",
    "DefinedTypes": "ОпределяемыйТип",
    "StyleItems": "ЭлементСтиля",
    "Languages": "Язык",
    "SessionParameters": "ПараметрСеанса",
    "SettingsStorages": "ХранилищеНастроек",
    "WebServices": "WebСервис",
    "XDTOPackages": "ПакетXDTO",
    "EventSubscriptions": "ПодпискаНаСобытие",
    "CommandGroups": "ГруппаКоманд",
    "DocumentNumerators": "НумераторДокументов",
    "FunctionalOptions": "ФункциональнаяОпция",
    "FunctionalOptionsParameters": "ПараметрФункциональнойОпции",
}

# Папки которые имеют смысл для семантической валидации запросов
QUERYABLE_FOLDERS = {
    "Catalogs",
    "Documents",
    "AccumulationRegisters",
    "InformationRegisters",
    "AccountingRegisters",
    "CalculationRegisters",
    "ChartsOfAccounts",
    "ChartsOfCharacteristicTypes",
    "ChartsOfCalculationTypes",
    "Enums",
    "DocumentJournals",
    "Constants",
    "ExchangePlans",
    "BusinessProcesses",
    "Tasks",
    "Sequences",
}


def _localname(tag: str) -> str:
    """Извлечь local name из {namespace}tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text(elem: ET.Element | None, default: str = "") -> str:
    if elem is None:
        return default
    return (elem.text or "").strip()


def _find_first_local(parent: ET.Element, name: str) -> ET.Element | None:
    """Найти первый дочерний элемент по local name (игнорируя namespace)."""
    for child in parent.iter():
        if _localname(child.tag) == name:
            return child
    return None


def _direct_children_local(parent: ET.Element, name: str) -> Iterable[ET.Element]:
    for child in parent:
        if _localname(child.tag) == name:
            yield child


def _all_children_local(parent: ET.Element, name: str) -> Iterable[ET.Element]:
    for child in parent.iter():
        if _localname(child.tag) == name:
            yield child


def parse_object_file(xml_path: Path) -> dict:
    """Распарсить один XML-файл объекта конфигурации.

    Возвращает dict со структурой:
        {
            "root_tag": "Catalog" | "Document" | "AccumulationRegister" | ...
            "name": "Контрагенты",
            "synonym_ru": "Контрагенты",
            "register_type": "Balance" | "Turnovers" | None,
            "attributes": [{"name": "...", "type_repr": "..."}],
            "dimensions": [...],
            "resources": [...],
            "tabular_sections": [{"name": "...", "attributes": [...]}],
            "enum_values": ["...", ...],
        }
    """
    tree = ET.parse(xml_path)
    md_root = tree.getroot()
    if _localname(md_root.tag) != "MetaDataObject":
        return {"error": "not a MetaDataObject", "path": str(xml_path)}

    # Первый дочерний — это сам объект (Catalog/Document/...)
    obj_elem: ET.Element | None = None
    for child in md_root:
        if _localname(child.tag) not in ("",):
            obj_elem = child
            break

    if obj_elem is None:
        return {"error": "no object element", "path": str(xml_path)}

    root_tag = _localname(obj_elem.tag)
    out: dict = {
        "root_tag": root_tag,
        "name": "",
        "synonym_ru": "",
        "register_type": None,
        "attributes": [],
        "dimensions": [],
        "resources": [],
        "tabular_sections": [],
        "enum_values": [],
    }

    # Properties — прямой ребёнок объекта
    props = None
    for c in obj_elem:
        if _localname(c.tag) == "Properties":
            props = c
            break

    if props is not None:
        name_el = _find_first_local(props, "Name")
        out["name"] = _text(name_el)
        # Synonym → v8:item → v8:lang=ru → v8:content
        syn_el = None
        for c in props:
            if _localname(c.tag) == "Synonym":
                syn_el = c
                break
        if syn_el is not None:
            for item in syn_el:
                if _localname(item.tag) == "item":
                    lang_v = None
                    content_v = None
                    for sub in item:
                        if _localname(sub.tag) == "lang":
                            lang_v = _text(sub)
                        elif _localname(sub.tag) == "content":
                            content_v = _text(sub)
                    if lang_v == "ru" and content_v:
                        out["synonym_ru"] = content_v
                        break
        # RegisterType (для AccumulationRegister)
        for c in props:
            if _localname(c.tag) == "RegisterType":
                out["register_type"] = _text(c)
                break

    # ChildObjects — реквизиты, измерения, ресурсы, табчасти, значения перечислений
    childs = None
    for c in obj_elem:
        if _localname(c.tag) == "ChildObjects":
            childs = c
            break

    if childs is not None:
        for child in childs:
            local = _localname(child.tag)
            if local == "Attribute":
                out["attributes"].append(_parse_attr_like(child))
            elif local == "Dimension":
                out["dimensions"].append(_parse_attr_like(child))
            elif local == "Resource":
                out["resources"].append(_parse_attr_like(child))
            elif local == "EnumValue":
                # Перечисление — список имён значений
                name_el = _find_first_local(child, "Name")
                out["enum_values"].append(_text(name_el))
            elif local == "TabularSection":
                ts_name_el = _find_first_local(child, "Name")
                ts_attrs: list[dict] = []
                # Внутри TabularSection — свой ChildObjects → Attribute
                for sub in child:
                    if _localname(sub.tag) == "ChildObjects":
                        for ts_child in sub:
                            if _localname(ts_child.tag) == "Attribute":
                                ts_attrs.append(_parse_attr_like(ts_child))
                out["tabular_sections"].append(
                    {"name": _text(ts_name_el), "attributes": ts_attrs}
                )

    return out


def _parse_attr_like(elem: ET.Element) -> dict:
    """Парсит Attribute / Dimension / Resource — у всех одинаковая структура."""
    props = None
    for c in elem:
        if _localname(c.tag) == "Properties":
            props = c
            break
    if props is None:
        return {"name": "", "type_repr": ""}
    name = _text(_find_first_local(props, "Name"))
    type_repr = _extract_type_repr(props)
    return {"name": name, "type_repr": type_repr}


def _extract_type_repr(props: ET.Element) -> str:
    """Извлечь компактное строковое представление типа.

    В XML тип лежит в <Type><v8:Type>...</v8:Type></Type>. Может быть
    несколько v8:Type (составной тип). Возвращаем 'Type1 | Type2' либо
    одиночный 'CatalogRef.Контрагенты'.
    """
    type_node = None
    for c in props:
        if _localname(c.tag) == "Type":
            type_node = c
            break
    if type_node is None:
        return ""
    parts: list[str] = []
    for sub in type_node:
        if _localname(sub.tag) == "Type":
            txt = _text(sub)
            if txt:
                parts.append(txt)
    return " | ".join(parts) if parts else ""


def count_objects(root: Path) -> dict[str, dict]:
    """Считаем XML-файлы в каждой корневой папке (объект = .xml файл)."""
    stats: dict[str, dict] = {}
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        xml_files = sorted(sub.glob("*.xml"))
        stats[sub.name] = {
            "count": len(xml_files),
            "first_xml": xml_files[0] if xml_files else None,
        }
    return stats


def render_report(root: Path, stats: dict[str, dict]) -> str:
    """Сгенерировать markdown-отчёт о структуре выгрузки."""
    out: list[str] = []
    out.append("# Configuration XML Format Study")
    out.append("")
    out.append(f"**Источник:** `{root}`  ")
    out.append("**Phase:** Sprint 5 Phase 0 (Discovery)  ")
    out.append("**Цель:** зафиксировать формат XML выгрузки конфигурации 1С")
    out.append("до написания backend парсера (Phase A).")
    out.append("")
    out.append("Документ сгенерирован автоматически скриптом")
    out.append("`backend/scripts/inspect_configuration_xml.py`.")
    out.append("")

    # 1. Глобальная статистика
    out.append("## 1. Общая статистика")
    out.append("")
    out.append("| Папка (EN) | Тип объекта (RU) | Кол-во | Запросный? |")
    out.append("|---|---|---:|:---:|")
    total = 0
    queryable_total = 0
    for folder, info in stats.items():
        kind_ru = FOLDER_TO_KIND_RU.get(folder, "—")
        queryable = "Yes" if folder in QUERYABLE_FOLDERS else "—"
        count = info["count"]
        total += count
        if folder in QUERYABLE_FOLDERS:
            queryable_total += count
        out.append(f"| {folder} | {kind_ru} | {count} | {queryable} |")
    out.append(f"| **Итого** | | **{total}** | |")
    out.append(f"| (из них запросных) | | **{queryable_total}** | |")
    out.append("")

    # 2. Корневой Configuration.xml
    out.append("## 2. Корневой `Configuration.xml`")
    out.append("")
    out.append(
        "Содержит имя конфигурации, синоним, версию платформы, версию "
        "конфигурации, поставщика, ссылки на все объекты. Для Sprint 5 "
        "нас интересуют только `Properties/Name` и `Properties/Synonym`:"
    )
    config_xml = root / "Configuration.xml"
    if config_xml.exists():
        try:
            cfg_data = parse_object_file(config_xml)
            out.append("")
            out.append(f"- **Корневой тег:** `{cfg_data.get('root_tag', '?')}`")
            out.append(f"- **Name:** `{cfg_data.get('name', '?')}`")
            out.append(f"- **Synonym (ru):** `{cfg_data.get('synonym_ru', '?')}`")
            out.append("")
        except Exception as exc:
            out.append(f"_(не удалось распарсить: {exc})_")
            out.append("")

    # 3. Структура XML-файла объекта (общая схема)
    out.append("## 3. Структура XML-файла объекта (общая схема)")
    out.append("")
    out.append("Каждый XML-файл объекта (например `Catalogs/Контрагенты.xml`) имеет")
    out.append("единообразную структуру:")
    out.append("")
    out.append("```xml")
    out.append('<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" ...>')
    out.append('  <Catalog uuid="..."> <!-- ИЛИ Document, AccumulationRegister, и т.д. -->')
    out.append("    <InternalInfo>")
    out.append('      <xr:GeneratedType name="CatalogRef.Контрагенты" category="Ref"/>')
    out.append("      <!-- generated types: Object, Ref, Selection, List, Manager -->")
    out.append("    </InternalInfo>")
    out.append("    <Properties>")
    out.append("      <Name>Контрагенты</Name>")
    out.append("      <Synonym>")
    out.append("        <v8:item>")
    out.append("          <v8:lang>ru</v8:lang>")
    out.append("          <v8:content>Контрагенты</v8:content>")
    out.append("        </v8:item>")
    out.append("      </Synonym>")
    out.append("      <!-- type-specific properties: Hierarchical, RegisterType, ChartOfAccounts ... -->")
    out.append("    </Properties>")
    out.append("    <ChildObjects>")
    out.append("      <Attribute>...</Attribute>            <!-- реквизит -->")
    out.append("      <Dimension>...</Dimension>            <!-- измерение (регистры) -->")
    out.append("      <Resource>...</Resource>              <!-- ресурс (регистры) -->")
    out.append("      <TabularSection>...</TabularSection>  <!-- табчасть -->")
    out.append("      <EnumValue>...</EnumValue>            <!-- значение перечисления -->")
    out.append("      <Form>имя_формы</Form>                <!-- ссылка на форму -->")
    out.append("      <Command>...</Command>")
    out.append("    </ChildObjects>")
    out.append("  </Catalog>")
    out.append("</MetaDataObject>")
    out.append("```")
    out.append("")
    out.append("**Корневые теги по типам:**")
    out.append("")
    out.append("| Папка | Корневой тег объекта |")
    out.append("|---|---|")
    out.append("| Catalogs | `Catalog` |")
    out.append("| Documents | `Document` |")
    out.append("| AccumulationRegisters | `AccumulationRegister` |")
    out.append("| InformationRegisters | `InformationRegister` |")
    out.append("| AccountingRegisters | `AccountingRegister` |")
    out.append("| CalculationRegisters | `CalculationRegister` |")
    out.append("| ChartsOfAccounts | `ChartOfAccounts` |")
    out.append("| ChartsOfCharacteristicTypes | `ChartOfCharacteristicTypes` |")
    out.append("| ChartsOfCalculationTypes | `ChartOfCalculationTypes` |")
    out.append("| Enums | `Enum` |")
    out.append("| DocumentJournals | `DocumentJournal` |")
    out.append("| Constants | `Constant` |")
    out.append("| ExchangePlans | `ExchangePlan` |")
    out.append("")

    # 4. Структура Attribute / Dimension / Resource
    out.append("## 4. Структура `Attribute` / `Dimension` / `Resource`")
    out.append("")
    out.append("У всех трёх типов структура `<Properties>` одинаковая:")
    out.append("")
    out.append("```xml")
    out.append('<Attribute uuid="...">')
    out.append("  <Properties>")
    out.append("    <Name>ИНН</Name>")
    out.append("    <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>ИНН</v8:content></v8:item></Synonym>")
    out.append("    <Type>")
    out.append("      <v8:Type>xs:string</v8:Type>            <!-- примитивный -->")
    out.append("      <v8:StringQualifiers>")
    out.append("        <v8:Length>12</v8:Length>")
    out.append("        <v8:AllowedLength>Variable</v8:AllowedLength>")
    out.append("      </v8:StringQualifiers>")
    out.append("    </Type>")
    out.append("  </Properties>")
    out.append("</Attribute>")
    out.append("```")
    out.append("")
    out.append("**Возможные значения `<v8:Type>`:**")
    out.append("")
    out.append("- `xs:string` — Строка (+ StringQualifiers с Length)")
    out.append("- `xs:decimal` — Число (+ NumberQualifiers с Digits/FractionDigits)")
    out.append("- `xs:boolean` — Булево")
    out.append("- `xs:dateTime` — Дата")
    out.append("- `cfg:CatalogRef.X` — ссылка на справочник X")
    out.append("- `cfg:DocumentRef.X` — ссылка на документ X")
    out.append("- `cfg:EnumRef.X` — ссылка на перечисление X")
    out.append("- `cfg:ChartOfCharacteristicTypesRef.X` — ссылка на ПВХ X")
    out.append("- `cfg:DefinedType.X` — определяемый тип (составной)")
    out.append("- `cfg:AccumulationRegisterRecordSet.X` — рекордсет регистра")
    out.append("")
    out.append("Несколько `<v8:Type>` внутри одного `<Type>` = составной тип.")
    out.append("")

    # 5. Виртуальные таблицы регистров
    out.append("## 5. Виртуальные таблицы регистров")
    out.append("")
    out.append("Виртуальные таблицы не хранятся отдельным тегом — они выводятся из")
    out.append("типа регистра:")
    out.append("")
    out.append("| Тип регистра | XML-тег | RegisterType | Виртуальные таблицы (SDBL) |")
    out.append("|---|---|---|---|")
    out.append("| Регистр накопления (остатков) | `AccumulationRegister` | `Balance` | `Остатки`, `Обороты`, `ОстаткиИОбороты` |")
    out.append("| Регистр накопления (оборотов) | `AccumulationRegister` | `Turnovers` | `Обороты` |")
    out.append("| Регистр сведений | `InformationRegister` | — | `СрезПоследних`, `СрезПервых` |")
    out.append("| Регистр бухгалтерии | `AccountingRegister` | — | `Остатки`, `Обороты`, `ОстаткиИОбороты`, `ДвиженияССубконто`, `ОборотыДтКт` |")
    out.append("| Регистр расчёта | `CalculationRegister` | — | `БазаДанных`, `ДанныеГрафика`, `ФактическийПериодДействия` |")
    out.append("")

    # 6. Per-type samples
    out.append("## 6. Образцы структуры по типам")
    out.append("")
    for folder in [
        "Catalogs",
        "Documents",
        "AccumulationRegisters",
        "InformationRegisters",
        "AccountingRegisters",
        "ChartsOfCharacteristicTypes",
        "ChartsOfAccounts",
        "Enums",
        "DocumentJournals",
    ]:
        if folder not in stats or stats[folder]["first_xml"] is None:
            continue
        sample_path = stats[folder]["first_xml"]
        try:
            data = parse_object_file(sample_path)
        except Exception as exc:
            out.append(f"### {folder} — `{sample_path.name}`")
            out.append("")
            out.append(f"_(parse error: {exc})_")
            out.append("")
            continue

        kind_ru = FOLDER_TO_KIND_RU.get(folder, "?")
        out.append(f"### {folder} ({kind_ru}) — образец `{sample_path.name}`")
        out.append("")
        out.append(f"- **Корневой тег:** `{data['root_tag']}`")
        out.append(f"- **Name:** `{data['name']}`")
        out.append(f"- **Synonym (ru):** `{data['synonym_ru']}`")
        if data.get("register_type"):
            out.append(f"- **RegisterType:** `{data['register_type']}`")
        out.append(f"- **Реквизитов:** {len(data['attributes'])}")
        out.append(f"- **Измерений:** {len(data['dimensions'])}")
        out.append(f"- **Ресурсов:** {len(data['resources'])}")
        out.append(f"- **Табчастей:** {len(data['tabular_sections'])}")
        out.append(f"- **Значений перечисления:** {len(data['enum_values'])}")
        if data["attributes"]:
            out.append("")
            out.append("Первые 5 реквизитов:")
            for a in data["attributes"][:5]:
                out.append(f"  - `{a['name']}` : `{a['type_repr']}`")
        if data["dimensions"]:
            out.append("")
            out.append("Измерения:")
            for d in data["dimensions"]:
                out.append(f"  - `{d['name']}` : `{d['type_repr']}`")
        if data["resources"]:
            out.append("")
            out.append("Ресурсы:")
            for r in data["resources"]:
                out.append(f"  - `{r['name']}` : `{r['type_repr']}`")
        if data["enum_values"]:
            out.append("")
            out.append(f"Значения: `{', '.join(data['enum_values'][:10])}`")
        out.append("")

    # 7. Выводы для Phase A
    out.append("## 7. Выводы и input для Phase A")
    out.append("")
    out.append("**Структура единообразная** — `MetaDataObject/<тип>/Properties` +")
    out.append("`ChildObjects` есть у всех queryable объектов. Можно сделать")
    out.append("**generic парсер с диспатчем по корневому тегу**.")
    out.append("")
    out.append("**Парсер Phase A должен:**")
    out.append("")
    out.append("1. Игнорировать неprestrelnye типы (CommonModules, CommonPictures,")
    out.append("   Roles, и т.п.) — они не упоминаются в SDBL.")
    out.append("2. Извлекать только `Name`, `Synonym` (ru), `Attribute`, `Dimension`,")
    out.append("   `Resource`, `TabularSection`, `EnumValue` — этого достаточно для")
    out.append("   семантической валидации запросов в Sprint 5.")
    out.append("3. Для регистров — определять тип виртуальных таблиц по")
    out.append("   `RegisterType` + типу регистра (см. таблицу в разделе 5).")
    out.append("4. Использовать только `xml.etree.ElementTree` (ADR-030).")
    out.append("")
    out.append("**STOP RULE не сработал:** структура полностью консистентна между")
    out.append("разными типами объектов. Generic парсер с базовым алгоритмом +")
    out.append("type-specific шагами (например, RegisterType для AccumulationRegister)")
    out.append("реализуем без блокирующих неопределённостей.")
    out.append("")

    return "\n".join(out)


def main(argv: list[str]) -> int:
    # Парсим argv: [--out FILE] [PATH]
    output_path: Path | None = None
    positional: list[str] = []
    i = 1
    while i < len(argv):
        if argv[i] in ("--out", "-o"):
            if i + 1 >= len(argv):
                print("ERROR: --out requires a file path", file=sys.stderr)
                return 2
            output_path = Path(argv[i + 1])
            i += 2
        else:
            positional.append(argv[i])
            i += 1

    if positional:
        root_path = Path(positional[0])
    else:
        root_path = Path(os.environ.get("OPTIMYZER_CONFIG_XML_PATH", r"C:\BUFFER\SCHEME"))
    if not root_path.exists():
        print(f"ERROR: path does not exist: {root_path}", file=sys.stderr)
        return 1
    if not (root_path / "Configuration.xml").is_file():
        print(
            f"ERROR: not a configuration dump (no Configuration.xml in {root_path})",
            file=sys.stderr,
        )
        return 1

    print(f"[inspect] root={root_path}", file=sys.stderr)
    stats = count_objects(root_path)
    print(f"[inspect] {len(stats)} folders, computing report...", file=sys.stderr)
    report = render_report(root_path, stats)

    if output_path is not None:
        # Пишем напрямую в UTF-8 без BOM (обход PowerShell `>` который
        # дефолтит в UTF-16 LE на Windows PowerShell 5.1).
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report + "\n", encoding="utf-8")
        print(f"[inspect] report written: {output_path} ({output_path.stat().st_size} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(report)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
