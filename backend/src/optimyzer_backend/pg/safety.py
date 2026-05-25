"""Sprint 8 Phase B — safety check для re-EXPLAIN service.

Главная задача: определить безопасно ли выполнить EXPLAIN (FORMAT JSON, ANALYZE, ...)
повторно для данного SQL. PG EXPLAIN ANALYZE на DML запросах **выполняет реальную
модификацию** (INSERT/UPDATE/DELETE), что недопустимо.

Безопасно (re-EXPLAIN можно):
  - SELECT (включая CTE, UNION, JOIN, window functions, subqueries)
  - WITH ... SELECT ... (CTE на верхнем уровне)

Небезопасно (re-EXPLAIN запрещён):
  - INSERT / UPDATE / DELETE / MERGE / TRUNCATE
  - CREATE / ALTER / DROP / GRANT / REVOKE
  - CALL (хранимые процедуры могут модифицировать)
  - BEGIN / COMMIT / ROLLBACK / SAVEPOINT
  - SET (изменяет session state)
  - VACUUM / ANALYZE / REINDEX (maintenance commands)
  - WITH ... INSERT/UPDATE/DELETE (modifying CTE)

Реализация — простой regex-based check. Не парсим SQL полноценно (sqlglot бы
дал точнее, но overkill для safety check). На false-negative предпочитаем deny
(если сомневаемся — не разрешаем).
"""

from __future__ import annotations

import re


# Удалить SQL-comments перед проверкой — комментарии могут содержать ключевые
# слова которые не должны влиять на classification. PG поддерживает:
#   - однострочные: -- ...
#   - многострочные: /* ... */ (могут быть вложены, но мы не учитываем).
_LINE_COMMENT = re.compile(r"--[^\n]*", re.MULTILINE)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

# String literals — PG поддерживает single-quoted 'string' с escape '' внутри.
# Также есть dollar-quoted $$ ... $$ (для функций), и E'...' escape strings.
# Для safety check нам нужно не учитывать keyword'ы из строк (юзер может иметь
# 'INSERT INTO archive' как имя кнопки в Description колонке справочника).
_STRING_LITERAL = re.compile(r"[Ee]?'(?:[^']|'')*'")
_DOLLAR_QUOTED = re.compile(r"\$([A-Za-z0-9_]*)\$.*?\$\1\$", re.DOTALL)


# Опасные keyword'ы, наличие которых на верхнем уровне (после первого слова)
# делает запрос небезопасным даже если он начинается с WITH.
# Используем word-boundary чтобы не матчить substrings ("FORINSERT").
_DML_KEYWORDS = [
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "MERGE ",
    "TRUNCATE ",
    "DROP ",
    "ALTER ",
    "CREATE ",
    "GRANT ",
    "REVOKE ",
    "CALL ",
    "VACUUM ",
    "REINDEX ",
    "REFRESH MATERIALIZED",
    "CLUSTER ",
    "COMMENT ON ",
    "LOCK TABLE",
    "PREPARE ",
    "EXECUTE ",
    "DEALLOCATE ",
]

# Transaction control / session state — для re-EXPLAIN бессмысленны и небезопасны.
_TX_KEYWORDS = [
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "RELEASE SAVEPOINT",
    "SET ",
    "RESET ",
    "DISCARD ",
    "COPY ",   # COPY может писать на диск / читать произвольные файлы — небезопасно
    "LISTEN ",
    "NOTIFY ",
    "UNLISTEN ",
]

# Allowed первое слово (после комментариев) — SELECT или WITH.
_ALLOWED_FIRST = re.compile(r"^\s*(SELECT|WITH|EXPLAIN|TABLE|VALUES)\b", re.IGNORECASE)


class UnsafeQueryError(ValueError):
    """SQL не прошёл safety check — re-EXPLAIN запрещён.

    Используется RPC слоем для возврата явной ошибки UI с пояснением
    почему этот запрос нельзя пере-проанализировать.
    """


def strip_sql_comments(sql: str) -> str:
    """Удаляет SQL комментарии (-- и /* */) перед classification.

    Не trim'ит whitespace — это работа caller'а.
    """
    s = _BLOCK_COMMENT.sub(" ", sql)
    s = _LINE_COMMENT.sub("", s)
    return s


def mask_string_literals(sql: str) -> str:
    """Заменяет содержимое string literals на пробелы той же длины.

    Сохраняет длину чтобы regex-positions не сдвигались, но keywords внутри
    строк (например `'INSERT INTO foo'` в WHERE description = 'INSERT INTO foo')
    не матчили DML check. Это критично для safety check на запросах от 1С где
    у Справочника может быть Description со словами типа "INSERT" / "UPDATE".

    Dollar-quoted strings ($$ ... $$) тоже маскируем — они используются внутри
    PL/pgSQL функций.
    """
    def _replace(m: re.Match[str]) -> str:
        return " " * len(m.group(0))

    s = _STRING_LITERAL.sub(_replace, sql)
    s = _DOLLAR_QUOTED.sub(_replace, s)
    return s


def is_safe_to_re_explain(sql: str) -> bool:
    """Returns True если SQL safe для re-EXPLAIN (FORMAT JSON, ANALYZE, ...).

    Алгоритм:
        1. Strip SQL комментарии (могут содержать INSERT/UPDATE словесно)
        2. Mask string literals (DML keyword внутри строки — не настоящий DML)
        3. Должно начинаться с SELECT / WITH / TABLE / VALUES (или EXPLAIN —
           юзер уже передал готовый EXPLAIN ... SELECT, мы переоборачиваем)
        4. Не должно содержать DML/DDL keywords на верхнем уровне
        5. Не должно содержать transaction control / SET commands

    False-positive (запрещаем безопасный запрос) лучше false-negative (разрешаем
    опасный). При сомнении — deny.
    """
    if not sql or not sql.strip():
        return False
    no_comments = strip_sql_comments(sql).strip()
    if not no_comments:
        return False

    # Должно начинаться с разрешённого keyword'а.
    # Проверяем ДО маскирования literals — first keyword не должен быть в строке.
    if not _ALLOWED_FIRST.match(no_comments):
        return False

    # Маскируем string literals чтобы keyword'ы внутри them не матчили.
    masked = mask_string_literals(no_comments)
    upper = masked.upper()

    # Проверка на DML/DDL keywords. Включает modifying CTE — WITH x AS (UPDATE ...).
    for kw in _DML_KEYWORDS:
        if kw in upper:
            return False

    # Transaction control / session state.
    for kw in _TX_KEYWORDS:
        if _word_boundary_contains(upper, kw):
            return False

    return True


def _word_boundary_contains(text: str, keyword: str) -> bool:
    """True если keyword встречается в text с word boundary с обеих сторон.

    Просто `in` даёт ложные срабатывания: "RESET " в "FORESET ..." (вряд ли,
    но для надёжности). Используем простой scan: keyword должен стоять
    после whitespace/начала строки и до whitespace/end/(.
    """
    kw_stripped = keyword.rstrip()  # уберём trailing space если есть
    pattern = r"(?:^|[\s\(;])" + re.escape(kw_stripped) + r"(?:[\s\(;]|$)"
    return bool(re.search(pattern, text))
