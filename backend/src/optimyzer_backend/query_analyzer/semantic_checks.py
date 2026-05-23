"""Sprint 5 — Semantic checks для Query Analyzer.

Реализации функций-чекеров которые сравнивают SDBL-запрос с реальной
структурой конфигурации (через ConfigurationMetadataStore).

Каждый чекер принимает (query_text, rule, config_store) и возвращает
список Finding. Имена чекеров регистрируются в SEMANTIC_CHECKS dict и
вызываются из native_rules.analyze() через run_semantic_check().

Все чекеры:
- Silent если store не подключён (analyze() уже фильтрует на этом уровне)
- Используют sdbl_tokenizer для извлечения refs
- Подставляют {{placeholders}} в markdown body rule перед возвратом
"""

from __future__ import annotations

from typing import Callable

from optimyzer_backend.query_analyzer.sdbl_tokenizer import (
    extract_object_references,
    extract_virtual_table_references,
    extract_vyrazit_types,
    offset_to_line_col,
)


# ---- Helpers ----


def _make_finding(
    rule,
    query_text: str,
    offset_start: int,
    offset_end: int,
    message: str,
    explanation_md: str,
):
    """Конструирует Finding с правильными координатами. Импорт здесь
    (а не в module scope) — чтобы избежать circular import с native_rules."""
    from optimyzer_backend.query_analyzer.native_rules import Finding

    ls, cs = offset_to_line_col(query_text, offset_start)
    le, ce = offset_to_line_col(query_text, offset_end)
    return Finding(
        source="semantic",
        rule_id=rule.id,
        severity=rule.severity,
        category=rule.category,
        line_start=ls,
        line_end=le,
        col_start=cs,
        col_end=ce,
        message=message,
        explanation_md=explanation_md,
        tags=list(rule.tags),
    )


def _render_body(body: str, replacements: dict[str, str]) -> str:
    """Подставляет {{key}} → value в markdown body rule."""
    out = body
    for key, val in replacements.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def _format_similar(similar: list[str]) -> str:
    """Markdown list из похожих имён, или сообщение о их отсутствии."""
    if not similar:
        return "_Похожих имён в конфигурации не найдено._"
    return "\n".join(f"- `{s}`" for s in similar)


_VALUE_CALL_RE = __import__("re").compile(
    r"(?i)(?<![А-Яа-яA-Za-z0-9_])ЗНАЧЕНИЕ\s*\("
)


def _mask_value_calls(query_text: str) -> str:
    """Заменяет содержимое каждого ``ЗНАЧЕНИЕ(...)`` (вместе с самими
    скобками и словом ЗНАЧЕНИЕ) на пробелы той же длины.

    Зачем: внутри ``ЗНАЧЕНИЕ(...)`` идёт обращение к **предопределённому**
    элементу справочника / счёта / вида характеристики / значению
    перечисления — это НЕ доступ к реквизиту через алиас. Если оставить
    эти подстроки в тексте, ``check_attribute_not_exists_in_from_alias``
    ошибочно посчитает имя предопределённого реквизитом и выдаст false
    positive (видели на запросах БП 3.0 со счетами вида
    ``ЗНАЧЕНИЕ(ПланСчетов.Хозрасчетный.РасчетыСПрочимиПокупателямиИЗаказчиками)``).

    Сохраняем длину текста — это важно, потому что offset'ы остальных
    findings вычисляются по позиции в исходной строке.

    Простой балансировщик скобок: ЗНАЧЕНИЕ() в SDBL не содержит вложенных
    вызовов, но защищаемся на случай странного ввода — считаем до тех
    пор, пока счётчик скобок не вернётся в 0.
    """
    masked = list(query_text)
    pos = 0
    n = len(query_text)
    while True:
        m = _VALUE_CALL_RE.search(query_text, pos)
        if m is None:
            break
        # m.end() указывает сразу ПОСЛЕ '('. Стартуем баланс с 1.
        depth = 1
        i = m.end()
        while i < n and depth > 0:
            ch = query_text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1
        # Маскируем весь диапазон [m.start(), i)
        for k in range(m.start(), i):
            if masked[k] != "\n":
                masked[k] = " "
        pos = i
    return "".join(masked)


# ---- Checks ----


def check_object_not_exists(query_text: str, rule, store) -> list:
    """Объект из FROM/JOIN/ВЫРАЗИТЬ не существует в подключённой конфигурации."""
    findings: list = []
    seen: set[str] = set()
    for ref in extract_object_references(query_text):
        if ref.full_name in seen:
            continue
        seen.add(ref.full_name)
        if store.is_object_exists(ref.full_name):
            continue
        similar = store.search_similar_objects(ref.full_name, max_distance=3, limit=5)
        body = _render_body(
            rule.body,
            {
                "object_full_name": ref.full_name,
                "similar_objects": _format_similar(similar),
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                ref.offset_start,
                ref.offset_end,
                f"Объект «{ref.full_name}» не существует в подключённой конфигурации",
                body,
            )
        )
    return findings


def check_object_kind_misspelled(query_text: str, rule, store) -> list:
    """Опечатка в типе объекта: множественное число вместо единственного.

    Срабатывает на 'Справочники.Х' (вместо 'Справочник.Х'), 'Документы.Y'
    и других типичных typos из KIND_TYPOS_RU. Эту проверку можно делать
    БЕЗ подключённой конфигурации — но мы оставляем requires=
    [configuration_metadata] для консистентности с остальными semantic
    rules (silent skip без store).
    """
    findings: list = []
    for ref in extract_object_references(query_text):
        if ref.raw_kind is None:
            continue  # тип написан правильно
        body = _render_body(
            rule.body,
            {
                "wrong_kind": ref.raw_kind,
                "correct_kind": ref.kind_ru,
                "object_name": ref.name,
                "correct_full_name": ref.full_name,
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                ref.kind_offset_start,
                ref.kind_offset_end,
                f"Тип «{ref.raw_kind}» написан во множественном числе — в 1С используется «{ref.kind_ru}»",
                body,
            )
        )
    return findings


def check_virtual_table_not_supported(query_text: str, rule, store) -> list:
    """Виртуальная таблица не существует для этого типа регистра.

    Пример: РегистрНакопления.Х.СрезПоследних — недопустимо (СрезПоследних
    есть только у регистров сведений).
    Также: РегистрНакопления (Turnovers).Х.Остатки — недопустимо.
    """
    findings: list = []
    for vref in extract_virtual_table_references(query_text):
        if not store.is_object_exists(vref.full_name):
            continue  # Эту ошибку поймает object_not_exists
        valid = store.get_virtual_tables(vref.full_name)
        if vref.virtual_table in valid:
            continue
        body = _render_body(
            rule.body,
            {
                "object_full_name": vref.full_name,
                "virtual_table": vref.virtual_table,
                "valid_virtual_tables": (
                    ", ".join(f"`{v}`" for v in valid) if valid
                    else "_у этого объекта виртуальных таблиц нет_"
                ),
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                vref.offset_start,
                vref.offset_end,
                f"Виртуальная таблица «{vref.virtual_table}» недопустима для «{vref.full_name}»",
                body,
            )
        )
    return findings


def check_vyrazit_type_not_exists(query_text: str, rule, store) -> list:
    """В конструкции ВЫРАЗИТЬ(... КАК X.Y) тип не существует.

    Это отдельный чекер от object_not_exists потому что в ВЫРАЗИТЬ
    обычно ожидают конкретный referencable тип (Справочник/Документ/
    Перечисление), и сообщение об ошибке более узкое.
    """
    findings: list = []
    for tref in extract_vyrazit_types(query_text):
        if store.is_object_exists(tref.full_name):
            continue
        similar = store.search_similar_objects(tref.full_name, max_distance=3, limit=5)
        body = _render_body(
            rule.body,
            {
                "object_full_name": tref.full_name,
                "similar_objects": _format_similar(similar),
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                tref.offset_start,
                tref.offset_end,
                f"Тип «{tref.full_name}» в ВЫРАЗИТЬ() не существует в конфигурации",
                body,
            )
        )
    return findings


def check_register_dimension_or_field_missing(query_text: str, rule, store) -> list:
    """Обнаруживает обращения вида РегистрНакопления.Х.Остатки(, Поле = ...)
    с проверкой что Поле — реально измерение/реквизит этого регистра.

    Sprint 5: упрощённая проверка по virtual table parameters в первом
    приближении. Полная проверка структуры WHERE / ВЫБРАТЬ полей —
    Sprint 6+ scope (нужен SDBL парсер).

    В Sprint 5 этот чекер ищет паттерн:
        РегНак.Х.Остатки(, Имя = ...)  ИЛИ  РегНак.Х.Остатки(, Имя В (...))
    и проверяет что Имя — это измерение регистра Х.
    """
    findings: list = []
    # Это не самый точный паттерн (не учитывает вложенные скобки), но
    # для подавляющего большинства запросов работает.
    import re

    # РегистрНакопления.Х.Остатки( , Поле1 = ... [И Поле2 = ...] )
    # Захватываем "Имя" между запятой и оператором сравнения.
    pattern = re.compile(
        r"(?im)(РегистрНакопления|РегистрСведений|РегистрБухгалтерии|РегистрРасчета)"
        r"\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\."
        r"(?:Остатки|Обороты|ОстаткиИОбороты|СрезПоследних|СрезПервых)"
        r"\s*\(\s*[^,)]*,\s*([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\s*[=В]"
    )
    for m in pattern.finditer(query_text):
        kind = m.group(1)
        register = m.group(2)
        field_name = m.group(3)
        full_name = f"{kind}.{register}"
        if not store.is_object_exists(full_name):
            continue
        dims = store.get_dimensions(full_name)
        dim_names = {d.name for d in dims}
        if field_name in dim_names:
            continue
        # Это не измерение — finding
        similar = ", ".join(f"`{n}`" for n in sorted(dim_names))
        body = _render_body(
            rule.body,
            {
                "object_full_name": full_name,
                "field_name": field_name,
                "available_dimensions": similar or "_у регистра нет измерений_",
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                m.start(3),
                m.end(3),
                f"«{field_name}» — не измерение регистра «{full_name}»",
                body,
            )
        )
    return findings


def check_enum_value_not_exists(query_text: str, rule, store) -> list:
    """Значение перечисления не существует.

    Паттерн: Перечисление.X.ИмяЗначения — проверяем что ИмяЗначения
    есть в enum_values объекта.
    """
    findings: list = []
    import re

    # Перечисление.X.ИмяЗначения — Y может быть до .Z
    # Используем _IDENT для имени enum value.
    pattern = re.compile(
        r"(?<![А-Яа-яA-Za-z0-9_])Перечисление\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
        r"\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
    )
    for m in pattern.finditer(query_text):
        enum_name = m.group(1)
        value_name = m.group(2)
        full_name = f"Перечисление.{enum_name}"
        if not store.is_object_exists(full_name):
            continue
        valid_values = store.get_enum_values(full_name)
        if value_name in valid_values:
            continue
        # Не валидное значение
        body = _render_body(
            rule.body,
            {
                "object_full_name": full_name,
                "value_name": value_name,
                "valid_values": (
                    ", ".join(f"`{v}`" for v in valid_values)
                    if valid_values
                    else "_у этого перечисления нет значений_"
                ),
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                m.start(2),
                m.end(2),
                f"Значение «{value_name}» не существует в перечислении «{full_name}»",
                body,
            )
        )
    return findings


def check_attribute_not_exists_in_from_alias(query_text: str, rule, store) -> list:
    """Обращение к несуществующему реквизиту через алиас FROM.

    Pattern: FROM Справочник.Контрагенты КАК К ... К.НесуществующийРеквизит
    Sprint 5: упрощённо — находим FROM <тип>.<имя> [КАК <алиас>] и потом
    ищем <алиас>.<поле> в остальном тексте, проверяя поле на существование.

    Если в запросе нет алиаса (FROM Справочник.Контрагенты, без КАК) —
    то ссылки на поля идут через прямое имя 'Контрагенты.X'. Это тоже
    поддерживаем.

    Ограничение Sprint 5: один FROM = один алиас. Полная поддержка
    JOIN/UNION/subquery — Sprint 6+.
    """
    findings: list = []
    import re

    # FROM <Kind>.<Name> [КАК <Alias>]
    from_re = re.compile(
        r"(?im)(?:ИЗ|FROM)\s+(Справочник|Документ|ПланСчетов|ПланВидовХарактеристик|"
        r"ПланВидовРасчета|ЖурналДокументов)\."
        r"([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
        r"(?:\s+(?:КАК|AS)\s+([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*))?"
    )
    aliases: list[tuple[str, str]] = []  # (alias, full_name)
    for m in from_re.finditer(query_text):
        kind = m.group(1)
        name = m.group(2)
        alias = m.group(3) or name  # без КАК → используется имя объекта
        full_name = f"{kind}.{name}"
        if store.is_object_exists(full_name):
            aliases.append((alias, full_name))

    if not aliases:
        return findings

    # ЗНАЧЕНИЕ(Kind.Object.Item) — это обращение к ПРЕДОПРЕДЕЛЁННОМУ
    # элементу, а не доступ к реквизиту через alias. Маскируем такие
    # вызовы пробелами (длина сохраняется → offset'ы остальных findings
    # корректны), чтобы regex `alias.X` не зацеплял их.
    # Отдельно валидируется правилом `predefined_item_not_exists`.
    search_text = _mask_value_calls(query_text)

    # Для каждого alias ищем alias.X. Lookbehind включает точку — иначе
    # в строке `Kind.Alias.X` regex принял бы `Alias.X` за обращение к
    # реквизиту, хотя на самом деле это часть полного имени объекта.
    for alias, full_name in aliases:
        attr_pattern = re.compile(
            rf"(?<![А-Яа-яA-Za-z0-9_.]){re.escape(alias)}\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
        )
        # Все реквизиты + табчасти + StandardAttribute (стандартные поля
        # 1С — Ссылка, Код, Наименование, ПометкаУдаления, Предопределённый,
        # ДатаДок и т.п.). Sprint 5: не требуем точного списка стандартных
        # — просто считаем их валидными если ничего из конфигурации
        # не подошло. Это снижает false positive rate.
        valid_attrs = {a.name for a in store.get_attributes(full_name)}
        valid_attrs |= set(store.get_tabular_section_names(full_name))
        # Стандартные атрибуты которые есть у любого Catalog/Document — whitelist:
        # (если конфигурация позже подскажет другие, можно расширить через
        # парсинг <StandardAttributes>; в Sprint 5 — фиксированный список)
        STANDARD_ATTRS = {
            "Ссылка", "Код", "Наименование", "ПометкаУдаления",
            "Предопределенный", "ПредопределенноеЗначение", "ВерсияДанных",
            "Родитель", "Владелец", "ЭтоГруппа",
            # Документ
            "Дата", "Номер", "Проведен",
            # Регистры
            "Регистратор", "ПериодРегистрации", "Период", "Активность",
            "НомерСтроки", "ВидДвижения",
        }
        valid_attrs |= STANDARD_ATTRS

        for m in attr_pattern.finditer(search_text):
            attr_name = m.group(1)
            if attr_name in valid_attrs:
                continue
            # Не валидный реквизит
            similar = ", ".join(
                f"`{a}`"
                for a in sorted(
                    {a.name for a in store.get_attributes(full_name)} - STANDARD_ATTRS
                )[:8]
            )
            body = _render_body(
                rule.body,
                {
                    "object_full_name": full_name,
                    "alias": alias,
                    "attribute_name": attr_name,
                    "available_attributes": similar or "_у объекта нет дополнительных реквизитов_",
                },
            )
            findings.append(
                _make_finding(
                    rule,
                    query_text,
                    m.start(1),
                    m.end(1),
                    f"Реквизит «{attr_name}» не существует у «{full_name}»",
                    body,
                )
            )
    return findings


def check_register_resource_used_as_dimension(query_text: str, rule, store) -> list:
    """В виртуальной таблице регистра фильтр идёт по ресурсу, а не измерению.

    Это менее частая ошибка, но критичная — фильтр по ресурсу даёт
    непредсказуемое поведение виртуальной таблицы.
    """
    findings: list = []
    import re

    pattern = re.compile(
        r"(?im)(РегистрНакопления|РегистрБухгалтерии)"
        r"\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\."
        r"(?:Остатки|ОстаткиИОбороты)"
        r"\s*\(\s*[^,)]*,\s*([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\s*[=В]"
    )
    for m in pattern.finditer(query_text):
        kind = m.group(1)
        register = m.group(2)
        field_name = m.group(3)
        full_name = f"{kind}.{register}"
        if not store.is_object_exists(full_name):
            continue
        resources = {r.name for r in store.get_resources(full_name)}
        if field_name not in resources:
            continue
        body = _render_body(
            rule.body,
            {
                "object_full_name": full_name,
                "field_name": field_name,
                "available_dimensions": (
                    ", ".join(f"`{d.name}`" for d in store.get_dimensions(full_name))
                    or "_у регистра нет измерений_"
                ),
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                m.start(3),
                m.end(3),
                f"«{field_name}» — ресурс регистра «{full_name}», нельзя фильтровать виртуальную таблицу",
                body,
            )
        )
    return findings


def check_tabular_section_used_as_attribute(query_text: str, rule, store) -> list:
    """Обращение Х.ТабчастьИмя.Реквизит без явной указания что
    это табчасть — обычно ошибка (нужно ИЗ Документ.Х.ТабЧасть или
    ВЫБРАТЬ Х.ТабЧасть.Реквизит ИЗ ...).

    Sprint 5: ограниченный детектор — алиас.ТабЧастьИмя без последующего
    .Реквизит и без указания в FROM как табчасти.

    Это редкая проверка, но добавляет покрытие.
    """
    # Sprint 5 keeps it minimal: не реализуем эту проверку детально —
    # placeholder для будущего расширения, чтобы rule можно было загрузить
    # без NotImplemented panic.
    return []


def check_predefined_item_not_exists(query_text: str, rule, store) -> list:
    """Обращение ``ЗНАЧЕНИЕ(Kind.Object.Item)`` к несуществующему
    ПРЕДОПРЕДЕЛЁННОМУ элементу.

    Сферы применения:
        Справочник.X.Item             — предопределённый элемент справочника
        ПланСчетов.X.Item             — предопределённый счёт
        ПланВидовХарактеристик.X.Item — предопределённый вид характеристики
        ПланВидовРасчета.X.Item       — предопределённый вид расчёта

    Для ``Перечисление.X.Item`` уже есть отдельное правило
    ``enum_value_not_exists`` — здесь его не дублируем.

    Когда срабатывает: ровно тогда, когда родительский объект существует в
    конфигурации, но имени Item нет в его списке предопределённых (см.
    Predefined.xml). Если родительский объект не существует — это поймает
    ``object_not_exists``, мы остаёмся silent.

    Особый случай: если объект подходящего типа существует, но Predefined.xml
    у него **пуст** (нет ни одного предопределённого) — finding не выдаётся,
    потому что иначе любой запрос на конфигурации без явных предопределённых
    стал бы заваленным false positive'ами. Считаем такие случаи «не знаем —
    значит молчим».
    """
    findings: list = []
    import re

    # Перечисление ловит отдельный чекер; здесь не дублируем.
    KINDS = (
        "Справочник",
        "ПланСчетов",
        "ПланВидовХарактеристик",
        "ПланВидовРасчета",
    )
    kinds_alt = "|".join(KINDS)
    # ЗНАЧЕНИЕ ( Kind . Object . Item [.OptionalSubItem] )
    # ``Item`` иногда содержит подзначение через точку (для иерархических
    # предопределённых: Группа.Подгруппа). Sprint 5: проверяем только первый
    # сегмент. Subsegmenты — отдельный TODO.
    pattern = re.compile(
        rf"(?im)(?<![А-Яа-яA-Za-z0-9_])ЗНАЧЕНИЕ\s*\(\s*"
        rf"({kinds_alt})\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)\."
        rf"([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
    )
    for m in pattern.finditer(query_text):
        kind = m.group(1)
        obj_name = m.group(2)
        item_name = m.group(3)
        full_name = f"{kind}.{obj_name}"
        if not store.is_object_exists(full_name):
            continue  # object_not_exists даст свой finding
        valid_items = store.get_predefined_names(full_name)
        if not valid_items:
            # Конфигурация не предоставила список — молчим, чтобы не выдавать
            # false positives (например для справочника без предопределённых).
            continue
        if item_name in valid_items:
            continue
        # Подсказываем похожие
        similar_items = _similar_strings(item_name, valid_items, max_distance=3, limit=5)
        body = _render_body(
            rule.body,
            {
                "object_full_name": full_name,
                "item_name": item_name,
                "valid_predefined": (
                    "\n".join(f"- `{n}`" for n in similar_items)
                    if similar_items
                    else "\n".join(f"- `{n}`" for n in valid_items[:8])
                ),
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                m.start(3),
                m.end(3),
                (
                    f"Предопределённый элемент «{item_name}» не существует "
                    f"у «{full_name}»"
                ),
                body,
            )
        )
    return findings


def _similar_strings(target: str, candidates: list[str], max_distance: int, limit: int) -> list[str]:
    """Простая выборка похожих строк по Levenshtein-расстоянию.

    Используется для подсказок «возможно вы имели в виду…» в предопределённых
    элементах. Дублирует логику из ConfigurationMetadataStore._levenshtein,
    но локально — чтобы не тянуть импорт ради одной функции.
    """

    def lev(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, start=1):
            curr = [i] + [0] * len(b)
            for j, cb in enumerate(b, start=1):
                cost = 0 if ca == cb else 1
                curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            prev = curr
        return prev[-1]

    scored: list[tuple[int, str]] = []
    tl = target.lower()
    for c in candidates:
        d = lev(tl, c.lower())
        if d <= max_distance:
            scored.append((d, c))
    scored.sort(key=lambda p: (p[0], p[1]))
    return [s for _, s in scored[:limit]]


def check_constant_used_with_dot(query_text: str, rule, store) -> list:
    """Обращение Константа.Х.Поле — у констант нет полей.

    Допустимо только Константа.Х (без точки) или Константа.Х.Получить()
    в коде на BSL, но не в SDBL.
    """
    findings: list = []
    import re

    pattern = re.compile(
        r"(?<![А-Яа-яA-Za-z0-9_])Константа\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
        r"\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
    )
    for m in pattern.finditer(query_text):
        const_name = m.group(1)
        field_name = m.group(2)
        full_name = f"Константа.{const_name}"
        if not store.is_object_exists(full_name):
            continue
        body = _render_body(
            rule.body,
            {
                "object_full_name": full_name,
                "field_name": field_name,
            },
        )
        findings.append(
            _make_finding(
                rule,
                query_text,
                m.start(2),
                m.end(2),
                f"У константы «{full_name}» нет полей (обращение «.{field_name}» некорректно)",
                body,
            )
        )
    return findings


# ---- Registry ----

SemanticCheckFn = Callable[[str, "object", "object"], list]

SEMANTIC_CHECKS: dict[str, SemanticCheckFn] = {
    "object_not_exists": check_object_not_exists,
    "object_kind_misspelled": check_object_kind_misspelled,
    "virtual_table_not_supported": check_virtual_table_not_supported,
    "vyrazit_type_not_exists": check_vyrazit_type_not_exists,
    "register_dimension_or_field_missing": check_register_dimension_or_field_missing,
    "enum_value_not_exists": check_enum_value_not_exists,
    "attribute_not_exists_in_from_alias": check_attribute_not_exists_in_from_alias,
    "register_resource_used_as_dimension": check_register_resource_used_as_dimension,
    "tabular_section_used_as_attribute": check_tabular_section_used_as_attribute,
    "constant_used_with_dot": check_constant_used_with_dot,
    "predefined_item_not_exists": check_predefined_item_not_exists,
}


def run_semantic_check(query_text: str, rule, store) -> list:
    """Диспатч: вызывает чекер по rule.check_name."""
    if rule.check_name is None:
        return []
    fn = SEMANTIC_CHECKS.get(rule.check_name)
    if fn is None:
        return []
    if store is None:
        return []
    return fn(query_text, rule, store)
