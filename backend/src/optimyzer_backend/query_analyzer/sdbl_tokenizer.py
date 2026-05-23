"""Sprint 5 — regex-based extractor object references из SDBL запросов.

НЕ полноценный SDBL парсер. Извлекает токены вида:

    Документ.АвансовыйОтчет
    Справочник.Контрагенты
    РегистрНакопления.ТоварыНаСкладах
    РегистрНакопления.ТоварыНаСкладах.Остатки
    Контрагенты.ИНН                    # обращение к полю объекта
    Хозрасчетный.Субконто1             # обращение к ресурсу регистра

Для семантической валидации этого достаточно. Полный парсер SDBL —
Sprint 6+ scope.

Pivot rule (из SPRINT_5_PROMPT, ADR-031): если regex extractor даёт
<70% точность на real запросах — рассмотреть pyparsing tokenizer или
вернуться к BSL Language Server подходу. Sprint 5 baseline: regex.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Множество русских типов объектов, упоминаемых в SDBL FROM/JOIN.
# Совпадает с ROOT_TAG_TO_KIND_RU из configuration_metadata.parser
# (но дублируется здесь чтобы избежать import cycle).
OBJECT_KINDS_RU: tuple[str, ...] = (
    "Справочник",
    "Документ",
    "РегистрНакопления",
    "РегистрСведений",
    "РегистрБухгалтерии",
    "РегистрРасчета",
    "ПланСчетов",
    "ПланВидовХарактеристик",
    "ПланВидовРасчета",
    "Перечисление",
    "ЖурналДокументов",
    "Константа",
    "ПланОбмена",
    "Последовательность",
    "БизнесПроцесс",
    "Задача",
)

# Идентификатор 1С: русские/латинские буквы + цифры + подчёркивания,
# не начинается с цифры.
_IDENT = r"[А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*"

# Регекс для object reference: Документ.АвансовыйОтчет / РегистрНакопления.Х
_KIND_ALT = "|".join(OBJECT_KINDS_RU)
_OBJECT_REF_RE = re.compile(
    rf"(?<![А-Яа-яA-Za-z0-9_])({_KIND_ALT})\.({_IDENT})"
)

# Виртуальные таблицы регистров — расширение object ref:
# РегистрНакопления.ТоварыНаСкладах.Остатки
# (или .Обороты, .ОстаткиИОбороты, .СрезПоследних, .ДвиженияССубконто, etc.)
_VIRTUAL_TABLE_NAMES = (
    "Остатки",
    "Обороты",
    "ОстаткиИОбороты",
    "СрезПоследних",
    "СрезПервых",
    "ДвиженияССубконто",
    "ОборотыДтКт",
    "БазаДанных",
    "ДанныеГрафика",
    "ФактическийПериодДействия",
)
_VTABLE_ALT = "|".join(_VIRTUAL_TABLE_NAMES)
_VIRTUAL_TABLE_RE = re.compile(
    rf"(?<![А-Яа-яA-Za-z0-9_])({_KIND_ALT})\.({_IDENT})\.({_VTABLE_ALT})"
)

# ВЫРАЗИТЬ(... КАК Тип) — извлечение типа для проверки существования
# ВЫРАЗИТЬ(Х КАК Справочник.Контрагенты)
_VYRAZIT_RE = re.compile(
    rf"(?im)ВЫРАЗИТЬ\s*\(\s*[^()]+\s+КАК\s+({_KIND_ALT})\.({_IDENT})\s*\)"
)


@dataclass
class ObjectReference:
    """Упоминание объекта в SDBL запросе."""

    kind_ru: str       # "Справочник", "Документ", ...
    name: str          # "Контрагенты"
    full_name: str     # "Справочник.Контрагенты"
    offset_start: int  # абсолютный offset в тексте запроса (0-based)
    offset_end: int    # exclusive


@dataclass
class VirtualTableReference:
    """Упоминание виртуальной таблицы регистра (РегистрНакопления.Х.Остатки)."""

    kind_ru: str           # "РегистрНакопления"
    register_name: str     # "ТоварыНаСкладах"
    virtual_table: str     # "Остатки"
    full_name: str         # "РегистрНакопления.ТоварыНаСкладах" (без vtable)
    offset_start: int
    offset_end: int


@dataclass
class VyrazitTypeReference:
    """Упоминание типа в ВЫРАЗИТЬ(X КАК Тип.X)."""

    kind_ru: str
    name: str
    full_name: str
    offset_start: int
    offset_end: int


def extract_object_references(query_text: str) -> list[ObjectReference]:
    """Извлекает все ссылки на объекты конфигурации.

    Returns list[ObjectReference]. Дубликаты НЕ удаляются — нужно знать
    про все упоминания для построения findings с правильными координатами.
    """
    refs: list[ObjectReference] = []
    if not query_text:
        return refs

    # Сначала находим virtual tables — они длиннее обычных refs.
    # Запомним их offsets чтобы не считать обычным object_ref родителя.
    vtable_offsets: set[tuple[int, int]] = set()
    for m in _VIRTUAL_TABLE_RE.finditer(query_text):
        kind = m.group(1)
        register = m.group(2)
        vtable = m.group(3)
        # Offsets базовой части (без .vtable) — для исключения из object_ref
        base_end = m.start(2) + len(register)
        vtable_offsets.add((m.start(1), base_end))

    for m in _OBJECT_REF_RE.finditer(query_text):
        kind = m.group(1)
        name = m.group(2)
        if (m.start(1), m.end(2)) in vtable_offsets:
            # Это базовая часть virtual table ref — её отдельным
            # virtual_table_references найдёт. Object ref всё равно
            # сохраняем — для check_object_not_exists проверки.
            pass
        refs.append(
            ObjectReference(
                kind_ru=kind,
                name=name,
                full_name=f"{kind}.{name}",
                offset_start=m.start(1),
                offset_end=m.end(2),
            )
        )
    return refs


def extract_virtual_table_references(query_text: str) -> list[VirtualTableReference]:
    """Извлекает обращения к виртуальным таблицам регистров."""
    refs: list[VirtualTableReference] = []
    if not query_text:
        return refs
    for m in _VIRTUAL_TABLE_RE.finditer(query_text):
        kind = m.group(1)
        register = m.group(2)
        vtable = m.group(3)
        refs.append(
            VirtualTableReference(
                kind_ru=kind,
                register_name=register,
                virtual_table=vtable,
                full_name=f"{kind}.{register}",
                offset_start=m.start(1),
                offset_end=m.end(3),
            )
        )
    return refs


def extract_vyrazit_types(query_text: str) -> list[VyrazitTypeReference]:
    """Извлекает типы из конструкции ВЫРАЗИТЬ(... КАК Тип.X)."""
    refs: list[VyrazitTypeReference] = []
    if not query_text:
        return refs
    for m in _VYRAZIT_RE.finditer(query_text):
        kind = m.group(1)
        name = m.group(2)
        refs.append(
            VyrazitTypeReference(
                kind_ru=kind,
                name=name,
                full_name=f"{kind}.{name}",
                offset_start=m.start(1),
                offset_end=m.end(2),
            )
        )
    return refs


def offset_to_line_col(text: str, offset: int) -> tuple[int, int]:
    """1-based (line, col) для абсолютного offset.

    Reuse от native_rules._offset_to_line_col, но открыт публично — это
    нужно semantic checks при построении Finding-ов.
    """
    if offset <= 0:
        return 1, 1
    if offset > len(text):
        offset = len(text)
    prefix = text[:offset]
    prefix_norm = prefix.replace("\r\n", "\n").replace("\r", "\n")
    line_idx = prefix_norm.count("\n")
    last_nl = prefix_norm.rfind("\n")
    col = len(prefix_norm) - (last_nl + 1) if last_nl >= 0 else len(prefix_norm)
    return line_idx + 1, col + 1
