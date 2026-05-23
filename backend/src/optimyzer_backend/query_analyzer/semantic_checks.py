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

    # Для каждого alias ищем alias.X
    for alias, full_name in aliases:
        attr_pattern = re.compile(
            rf"(?<![А-Яа-яA-Za-z0-9_]){re.escape(alias)}\.([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)"
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

        for m in attr_pattern.finditer(query_text):
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
