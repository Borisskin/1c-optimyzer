"""SQL Validator (ADR-019).

Single defense-line на parse stage: только SELECT / WITH разрешены. Любые DDL
(CREATE/DROP/ALTER/TRUNCATE), DML (INSERT/UPDATE/DELETE/MERGE), а также
ATTACH/COPY/PRAGMA/SET — отклоняются с понятным сообщением.

Second defense — read-only DuckDB connection в SQLExecutor.
"""

from __future__ import annotations

import re


class SQLValidationError(ValueError):
    """Запрос отклонён валидатором."""


ALLOWED_TOP_LEVEL: set[str] = {"SELECT", "WITH"}

BLOCKED_KEYWORDS: tuple[str, ...] = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "TRUNCATE",
    "CREATE",
    "DROP",
    "ALTER",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "COPY",
    "EXPORT",
    "IMPORT",
    "PRAGMA",
    "CALL",
    "EXECUTE",
    "REPLACE",
    "VACUUM",
    "CHECKPOINT",
    "INSTALL",
    "LOAD",
)

_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE_RE = re.compile(r"--[^\n]*")
_BLOCKED_WORD_RE = re.compile(
    r"\b(?:" + "|".join(BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)
_FIRST_WORD_RE = re.compile(r"\b(\w+)\b")


def _strip_strings_and_comments(sql: str) -> str:
    """Уберём строковые литералы и комментарии — они не должны влиять на проверку."""
    no_block = _COMMENT_BLOCK_RE.sub(" ", sql)
    no_line = _COMMENT_LINE_RE.sub(" ", no_block)
    no_strings = _STRING_LITERAL_RE.sub("''", no_line)
    return no_strings


def _count_statements(sql_stripped: str) -> int:
    """Считаем top-level statements по неэкранированным ';'.

    После _strip_strings_and_comments(...) ';' внутри литералов/комментариев уже
    не появляются, поэтому достаточно простого split.
    """
    parts = [p.strip() for p in sql_stripped.split(";")]
    return sum(1 for p in parts if p)


def validate_sql(sql: str) -> tuple[bool, str | None]:
    """Returns (is_valid, error_message)."""
    if not sql or not sql.strip():
        return False, "Пустой запрос"

    stripped = _strip_strings_and_comments(sql)

    # Multi-statement (даже SELECT;SELECT) — отклоняем чтобы избежать bypass.
    if _count_statements(stripped) > 1:
        return False, "Поддерживается только один SQL-запрос за раз"

    blocked = _BLOCKED_WORD_RE.search(stripped)
    if blocked:
        word = blocked.group(0).upper()
        return False, f"Запрещённое ключевое слово: {word}. Разрешены только SELECT."

    first = _FIRST_WORD_RE.search(stripped)
    if first is None:
        return False, "Не удалось определить тип запроса"

    first_kw = first.group(1).upper()
    if first_kw not in ALLOWED_TOP_LEVEL:
        return False, f"Запрос должен начинаться с SELECT или WITH (найдено: {first_kw})"

    return True, None
