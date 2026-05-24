"""SQLite-индекс метаданных конфигурации 1С (Sprint 5 Phase A).

Сохраняет результаты парсинга XML выгрузки в `data/config_metadata.db`
(или другой путь по выбору). Реализует hash-based invalidation:
повторная индексация только если содержимое корневой папки выгрузки
изменилось (mtime + size всех XML файлов).

API верхнего уровня (для query analyzer и RPC):
    - is_indexed() — проверка что индекс готов
    - is_object_exists(full_name) — есть ли объект 'Справочник.Контрагенты'
    - get_object(full_name) — полные метаданные объекта
    - get_attributes(full_name) — реквизиты
    - get_dimensions(full_name) — измерения (для регистров)
    - get_resources(full_name) — ресурсы (для регистров)
    - get_virtual_tables(full_name) — список валидных виртуальных таблиц
    - search_similar_objects(name, max_distance) — Levenshtein-подсказки

Sprint 6 placeholders (raise NotImplementedError):
    - find_module_by_context(tj_context)
    - extract_sdbl_from_module(module_location, line)

ADR-029: persistence через SQLite, отдельный файл от
`data/explainer_cache.db` (Sprint 4 cache).
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from optimyzer_backend.configuration_metadata.parser import (
    ConfigurationObject,
    ConfigurationParser,
    Attribute,
    TabularSection,
    VIRTUAL_TABLES_BY_KIND_AND_TYPE,
)

logger = logging.getLogger(__name__)


# Версия схемы — bumped при breaking changes в DDL.
# v2 — добавлена таблица predefined_items (Sprint 5 hotfix: валидация
# ЗНАЧЕНИЕ(Справочник.X.ИмяПредопределённого) и аналогично для планов
# счетов / видов характеристик / видов расчёта).
SCHEMA_VERSION = "2"


# Sprint 6 placeholder типы — Sprint 5 их не реализует, но API должен быть.
class ModuleLocation:
    """Sprint 6 placeholder — location в .bsl модуле."""

    pass


class ConfigurationMetadataStore:
    """SQLite-индекс метаданных конфигурации.

    Использование::

        store = ConfigurationMetadataStore(db_path=Path("data/config_metadata.db"))
        result = store.index_configuration(Path("C:/BUFFER/SCHEME"))
        # result: {"status": "indexed", "object_count": 1647, ...}

        if store.is_object_exists("Справочник.Контрагенты"):
            attrs = store.get_attributes("Справочник.Контрагенты")
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ---- internal: schema ----

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        """Создаёт таблицы если их нет. Хранит SCHEMA_VERSION в meta."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS objects (
                    full_name      TEXT PRIMARY KEY,
                    kind_ru        TEXT NOT NULL,
                    name           TEXT NOT NULL,
                    synonym_ru     TEXT,
                    register_type  TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_objects_kind ON objects(kind_ru);
                CREATE INDEX IF NOT EXISTS idx_objects_name ON objects(name);

                CREATE TABLE IF NOT EXISTS attributes (
                    object_full_name  TEXT NOT NULL,
                    attribute_kind    TEXT NOT NULL,
                    -- attribute_kind: 'attribute' | 'dimension' | 'resource' | 'ts_attribute'
                    section_name      TEXT NOT NULL DEFAULT '',
                    -- для 'ts_attribute' — имя табчасти; для остальных ''
                    name              TEXT NOT NULL,
                    type_repr         TEXT,
                    ord               INTEGER NOT NULL,
                    PRIMARY KEY (object_full_name, attribute_kind, section_name, name),
                    FOREIGN KEY (object_full_name) REFERENCES objects(full_name) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attr_object ON attributes(object_full_name);
                CREATE INDEX IF NOT EXISTS idx_attr_name   ON attributes(name);

                CREATE TABLE IF NOT EXISTS tabular_sections (
                    object_full_name  TEXT NOT NULL,
                    name              TEXT NOT NULL,
                    ord               INTEGER NOT NULL,
                    PRIMARY KEY (object_full_name, name),
                    FOREIGN KEY (object_full_name) REFERENCES objects(full_name) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS enum_values (
                    object_full_name  TEXT NOT NULL,
                    value_name        TEXT NOT NULL,
                    ord               INTEGER NOT NULL,
                    PRIMARY KEY (object_full_name, value_name),
                    FOREIGN KEY (object_full_name) REFERENCES objects(full_name) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS predefined_items (
                    object_full_name  TEXT NOT NULL,
                    item_name         TEXT NOT NULL,
                    ord               INTEGER NOT NULL,
                    PRIMARY KEY (object_full_name, item_name),
                    FOREIGN KEY (object_full_name) REFERENCES objects(full_name) ON DELETE CASCADE
                );
                """
            )
            # SCHEMA_VERSION management. Если был старый индекс (v1) — сносим
            # данные и заставляем переиндексировать (миграции для v0.5.x не
            # делаем — это локальный кеш, переиндексация занимает секунды).
            row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                    (SCHEMA_VERSION,),
                )
            elif row[0] != SCHEMA_VERSION:
                # Bumped — снести старые данные. Сохраняем только новый ключ.
                conn.executescript(
                    """
                    DELETE FROM attributes;
                    DELETE FROM tabular_sections;
                    DELETE FROM enum_values;
                    DELETE FROM predefined_items;
                    DELETE FROM objects;
                    DELETE FROM meta;
                    """
                )
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                    (SCHEMA_VERSION,),
                )

    # ---- index / re-index ----

    @staticmethod
    def _compute_source_hash(root_path: Path) -> str:
        """Хеш папки выгрузки: имена + размер + mtime всех XML файлов.

        Чувствителен к изменению любого XML — пересохранение из Конфигуратора
        даёт другой хеш. Не зависит от полного содержимого (быстро).
        """
        h = hashlib.sha256()
        # Сортируем для детерминизма
        files = sorted(root_path.rglob("*.xml"))
        for f in files:
            try:
                stat = f.stat()
            except OSError:
                continue
            rel = f.relative_to(root_path).as_posix()
            h.update(f"{rel}|{stat.st_size}|{int(stat.st_mtime_ns)}|".encode("utf-8"))
        return h.hexdigest()

    def index_configuration(self, root_path: Path) -> dict[str, Any]:
        """Индексирует выгрузку. Если хеш не изменился — возвращает 'already_indexed'.

        Returns:
            {"status": "indexed" | "already_indexed",
             "object_count": int,
             "by_kind": {"Справочник": 262, ...},
             "configuration": {"name": ..., "synonym_ru": ..., "vendor": ..., "version": ...}}
        """
        root_path = Path(root_path)
        new_hash = self._compute_source_hash(root_path)
        existing_hash = self.get_meta("source_hash")

        if existing_hash == new_hash and self.count_objects() > 0:
            return {
                "status": "already_indexed",
                "object_count": self.count_objects(),
                "by_kind": self.stats_by_kind(),
                "configuration": {
                    "name": self.get_meta("config_name") or "",
                    "synonym_ru": self.get_meta("config_synonym_ru") or "",
                    "vendor": self.get_meta("config_vendor") or "",
                    "version": self.get_meta("config_version") or "",
                },
            }

        parser = ConfigurationParser(root_path)
        config_info = parser.get_configuration_info()
        objects = parser.parse()

        self._truncate()

        # Bulk insert
        with self._connect() as conn:
            conn.execute("BEGIN")
            for obj in objects:
                self._insert_object(conn, obj)
            conn.commit()

        # Сохраняем meta
        self.set_meta("source_hash", new_hash)
        self.set_meta("source_path", str(root_path))
        self.set_meta("indexed_at", datetime.now(timezone.utc).isoformat())
        self.set_meta("config_name", config_info.get("name", ""))
        self.set_meta("config_synonym_ru", config_info.get("synonym_ru", ""))
        self.set_meta("config_vendor", config_info.get("vendor", ""))
        self.set_meta("config_version", config_info.get("version", ""))

        return {
            "status": "indexed",
            "object_count": len(objects),
            "by_kind": self.stats_by_kind(),
            "configuration": config_info,
        }

    def _insert_object(self, conn: sqlite3.Connection, obj: ConfigurationObject) -> None:
        conn.execute(
            "INSERT INTO objects(full_name, kind_ru, name, synonym_ru, register_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (obj.full_name, obj.kind_ru, obj.name, obj.synonym_ru, obj.register_type),
        )
        for ord_idx, attr in enumerate(obj.attributes):
            conn.execute(
                "INSERT INTO attributes(object_full_name, attribute_kind, section_name, name, type_repr, ord) "
                "VALUES (?, 'attribute', '', ?, ?, ?)",
                (obj.full_name, attr.name, attr.type_repr, ord_idx),
            )
        for ord_idx, dim in enumerate(obj.dimensions):
            conn.execute(
                "INSERT INTO attributes(object_full_name, attribute_kind, section_name, name, type_repr, ord) "
                "VALUES (?, 'dimension', '', ?, ?, ?)",
                (obj.full_name, dim.name, dim.type_repr, ord_idx),
            )
        for ord_idx, res in enumerate(obj.resources):
            conn.execute(
                "INSERT INTO attributes(object_full_name, attribute_kind, section_name, name, type_repr, ord) "
                "VALUES (?, 'resource', '', ?, ?, ?)",
                (obj.full_name, res.name, res.type_repr, ord_idx),
            )
        for ord_ts, ts in enumerate(obj.tabular_sections):
            conn.execute(
                "INSERT INTO tabular_sections(object_full_name, name, ord) VALUES (?, ?, ?)",
                (obj.full_name, ts.name, ord_ts),
            )
            for ord_attr, ts_attr in enumerate(ts.attributes):
                conn.execute(
                    "INSERT INTO attributes(object_full_name, attribute_kind, section_name, name, type_repr, ord) "
                    "VALUES (?, 'ts_attribute', ?, ?, ?, ?)",
                    (obj.full_name, ts.name, ts_attr.name, ts_attr.type_repr, ord_attr),
                )
        for ord_ev, ev in enumerate(obj.enum_values):
            conn.execute(
                "INSERT INTO enum_values(object_full_name, value_name, ord) VALUES (?, ?, ?)",
                (obj.full_name, ev, ord_ev),
            )
        for ord_pi, pname in enumerate(obj.predefined_names):
            conn.execute(
                "INSERT OR IGNORE INTO predefined_items(object_full_name, item_name, ord) "
                "VALUES (?, ?, ?)",
                (obj.full_name, pname, ord_pi),
            )

    def _truncate(self) -> None:
        """Удаляет все объекты из индекса (но сохраняет meta)."""
        with self._connect() as conn:
            conn.executescript(
                """
                DELETE FROM attributes;
                DELETE FROM tabular_sections;
                DELETE FROM enum_values;
                DELETE FROM predefined_items;
                DELETE FROM objects;
                """
            )

    def clear(self) -> None:
        """Полная очистка: объекты + meta. Не удаляет сам db-файл."""
        self._truncate()
        with self._connect() as conn:
            conn.execute("DELETE FROM meta WHERE key != 'schema_version'")
            conn.commit()

    # ---- meta ----

    def get_meta(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_source_path(self) -> Path | None:
        """Sprint 6 Phase C: путь к XML конфигурации для bsl-LS configurationRoot.

        Возвращает Path к корню индексированной XML выгрузки (`C:\\BUFFER\\SCHEME` и т.п.)
        или None если выгрузка не подключена / путь не существует.
        """
        raw = self.get_meta("source_path")
        if not raw:
            return None
        path = Path(raw)
        if not path.is_dir():
            # Путь сохранён но папка удалена/перемещена — graceful degradation
            return None
        return path

    def get_configuration_info(self) -> dict[str, str]:
        """Sprint 6 Phase C: метаданные подключённой конфы для UI badge."""
        return {
            "name": self.get_meta("config_name") or "",
            "synonym_ru": self.get_meta("config_synonym_ru") or "",
            "vendor": self.get_meta("config_vendor") or "",
            "version": self.get_meta("config_version") or "",
            "source_path": self.get_meta("source_path") or "",
            "indexed_at": self.get_meta("indexed_at") or "",
            "object_count": self.count_objects(),
        }

    # ---- stats / counts ----

    def is_indexed(self) -> bool:
        """True если индекс заполнен (есть хотя бы один объект)."""
        return self.count_objects() > 0

    def count_objects(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM objects").fetchone()
            return int(row[0]) if row else 0

    def stats_by_kind(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT kind_ru, COUNT(*) FROM objects GROUP BY kind_ru ORDER BY kind_ru"
            ).fetchall()
            return {k: int(v) for k, v in rows}

    # ---- high-level query API ----

    def is_object_exists(self, full_name: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM objects WHERE full_name = ? LIMIT 1", (full_name,)
            ).fetchone()
            return row is not None

    def get_object_kind(self, full_name: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT kind_ru FROM objects WHERE full_name = ?", (full_name,)
            ).fetchone()
            return row[0] if row else None

    def get_object(self, full_name: str) -> ConfigurationObject | None:
        """Полная реконструкция объекта из БД (используется тестами)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT kind_ru, name, synonym_ru, register_type FROM objects "
                "WHERE full_name = ?",
                (full_name,),
            ).fetchone()
            if row is None:
                return None
            kind_ru, name, synonym_ru, register_type = row

            attributes: list[Attribute] = []
            dimensions: list[Attribute] = []
            resources: list[Attribute] = []
            ts_attrs: dict[str, list[Attribute]] = {}

            attr_rows = conn.execute(
                "SELECT attribute_kind, section_name, name, type_repr FROM attributes "
                "WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            for attr_kind, section_name, attr_name, type_repr in attr_rows:
                attr = Attribute(name=attr_name, type_repr=type_repr or "")
                if attr_kind == "attribute":
                    attributes.append(attr)
                elif attr_kind == "dimension":
                    dimensions.append(attr)
                elif attr_kind == "resource":
                    resources.append(attr)
                elif attr_kind == "ts_attribute" and section_name:
                    ts_attrs.setdefault(section_name, []).append(attr)

            tabular_sections: list[TabularSection] = []
            ts_rows = conn.execute(
                "SELECT name FROM tabular_sections WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            for (ts_name,) in ts_rows:
                tabular_sections.append(
                    TabularSection(name=ts_name, attributes=ts_attrs.get(ts_name, []))
                )

            enum_values: list[str] = []
            ev_rows = conn.execute(
                "SELECT value_name FROM enum_values WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            enum_values = [r[0] for r in ev_rows]

            predefined_rows = conn.execute(
                "SELECT item_name FROM predefined_items "
                "WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            predefined_names = [r[0] for r in predefined_rows]

            return ConfigurationObject(
                kind_ru=kind_ru,
                name=name,
                synonym_ru=synonym_ru or "",
                register_type=register_type,
                attributes=attributes,
                dimensions=dimensions,
                resources=resources,
                tabular_sections=tabular_sections,
                enum_values=enum_values,
                predefined_names=predefined_names,
            )

    def get_attributes(self, full_name: str) -> list[Attribute]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, type_repr FROM attributes "
                "WHERE object_full_name = ? AND attribute_kind = 'attribute' "
                "ORDER BY ord",
                (full_name,),
            ).fetchall()
            return [Attribute(name=n, type_repr=t or "") for n, t in rows]

    def get_dimensions(self, full_name: str) -> list[Attribute]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, type_repr FROM attributes "
                "WHERE object_full_name = ? AND attribute_kind = 'dimension' "
                "ORDER BY ord",
                (full_name,),
            ).fetchall()
            return [Attribute(name=n, type_repr=t or "") for n, t in rows]

    def get_resources(self, full_name: str) -> list[Attribute]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, type_repr FROM attributes "
                "WHERE object_full_name = ? AND attribute_kind = 'resource' "
                "ORDER BY ord",
                (full_name,),
            ).fetchall()
            return [Attribute(name=n, type_repr=t or "") for n, t in rows]

    def get_tabular_section_names(self, full_name: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM tabular_sections WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            return [r[0] for r in rows]

    def get_enum_values(self, full_name: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT value_name FROM enum_values WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            return [r[0] for r in rows]

    def get_predefined_names(self, full_name: str) -> list[str]:
        """Имена ПРЕДОПРЕДЕЛЁННЫХ элементов объекта.

        Заполнено для Справочник / ПланСчетов / ПланВидовХарактеристик /
        ПланВидовРасчета (из Predefined.xml). Для остальных типов всегда
        пустой список (логически у регистров и документов нет
        предопределённых, у перечисления значения лежат в enum_values).
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT item_name FROM predefined_items "
                "WHERE object_full_name = ? ORDER BY ord",
                (full_name,),
            ).fetchall()
            return [r[0] for r in rows]

    def get_virtual_tables(self, full_name: str) -> list[str]:
        """Список SDBL-имён виртуальных таблиц этого объекта (для регистров)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT kind_ru, register_type FROM objects WHERE full_name = ?",
                (full_name,),
            ).fetchone()
            if row is None:
                return []
            kind_ru, register_type = row
            key = (kind_ru, register_type)
            if key in VIRTUAL_TABLES_BY_KIND_AND_TYPE:
                return list(VIRTUAL_TABLES_BY_KIND_AND_TYPE[key])
            key2 = (kind_ru, None)
            if key2 in VIRTUAL_TABLES_BY_KIND_AND_TYPE:
                return list(VIRTUAL_TABLES_BY_KIND_AND_TYPE[key2])
            return []

    def search_similar_objects(
        self, full_name: str, max_distance: int = 3, limit: int = 5
    ) -> list[str]:
        """Поиск похожих имён через Levenshtein (для подсказок rule).

        Сравнивает только локальную часть после точки — 'Справочник.Контрагенты'
        → 'Контрагенты', и ищет другие справочники с близким именем. Если в
        full_name нет точки — сравниваем всё имя.
        """
        if "." in full_name:
            kind_ru, _, target_name = full_name.partition(".")
        else:
            kind_ru = ""
            target_name = full_name
        if not target_name:
            return []

        # Ищем кандидатов того же типа (если kind_ru задан)
        with self._connect() as conn:
            if kind_ru:
                rows = conn.execute(
                    "SELECT full_name, name FROM objects WHERE kind_ru = ?", (kind_ru,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT full_name, name FROM objects").fetchall()

        scored: list[tuple[int, str]] = []
        for cand_full, cand_name in rows:
            d = _levenshtein(target_name.lower(), cand_name.lower())
            if d <= max_distance and cand_full != full_name:
                scored.append((d, cand_full))
        scored.sort(key=lambda p: (p[0], p[1]))
        return [full for _, full in scored[:limit]]

    # ---- Sprint 6 placeholders ----

    def find_module_by_context(self, tj_context: str) -> ModuleLocation | None:
        """Sprint 6 placeholder — будет искать .bsl модуль по stack trace из
        DBMSSQL.Context."""
        raise NotImplementedError(
            "find_module_by_context — Sprint 6 feature, не реализовано в Sprint 5"
        )

    def extract_sdbl_from_module(
        self, module_location: ModuleLocation, line: int
    ) -> str | None:
        """Sprint 6 placeholder — будет извлекать SDBL из строкового
        литерала в .bsl модуле."""
        raise NotImplementedError(
            "extract_sdbl_from_module — Sprint 6 feature, не реализовано в Sprint 5"
        )


def _levenshtein(a: str, b: str) -> int:
    """Levenshtein distance — для подсказок 'возможно вы имели в виду...'."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Iterative DP с одной строкой
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(
                curr[j - 1] + 1,      # вставка
                prev[j] + 1,           # удаление
                prev[j - 1] + cost,    # замена
            )
        prev = curr
    return prev[-1]
