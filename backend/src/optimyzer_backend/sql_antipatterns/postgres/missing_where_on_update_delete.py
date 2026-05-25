"""PG antipattern #14 — UPDATE/DELETE без WHERE.

Pattern: UPDATE tbl SET ... | DELETE FROM tbl (без WHERE)
Severity: CRITICAL
1С-aware: False (1С никогда не делает UPDATE/DELETE без WHERE)

Затронет все строки таблицы — критическая ошибка.
"""

from __future__ import annotations

from sqlglot import exp

from optimyzer_backend.sql_antipatterns.models import (
    AntipatternSeverity,
    SqlAntipattern,
)


def detect_missing_where_on_update_delete(
    ast: exp.Expression, is_1c_context: bool = False
) -> list[SqlAntipattern]:
    findings: list[SqlAntipattern] = []

    # UPDATE без WHERE
    for upd in ast.find_all(exp.Update):
        where = upd.args.get("where")
        if where is None:
            target = upd.args.get("this")
            tbl_name = target.name if target is not None and hasattr(target, "name") else "?"
            findings.append(
                SqlAntipattern(
                    code="missing_where_on_update_delete",
                    title=f"UPDATE без WHERE на таблице `{tbl_name}`",
                    description=(
                        f"UPDATE {tbl_name} без WHERE затронет ВСЕ строки таблицы. "
                        "Это почти наверняка баг — критическая ошибка данных."
                    ),
                    severity=AntipatternSeverity.CRITICAL,
                    dialect="postgres",
                    snippet=f"UPDATE {tbl_name} SET ...",
                    rationale=(
                        "Missing WHERE clause — самая частая причина случайной "
                        "перезаписи данных. PostgreSQL не предупреждает."
                    ),
                    recommendation=(
                        "Добавьте WHERE с явным фильтром. Перед запуском проверьте "
                        "тот же запрос как SELECT — оцените количество строк."
                    ),
                )
            )
            return findings  # критичный — возвращаем сразу

    # DELETE без WHERE
    for dlt in ast.find_all(exp.Delete):
        where = dlt.args.get("where")
        if where is None:
            target = dlt.args.get("this")
            tbl_name = target.name if target is not None and hasattr(target, "name") else "?"
            findings.append(
                SqlAntipattern(
                    code="missing_where_on_update_delete",
                    title=f"DELETE без WHERE на таблице `{tbl_name}`",
                    description=(
                        f"DELETE FROM {tbl_name} без WHERE удалит ВСЕ строки "
                        "таблицы. Критическая ошибка — обычно нужно TRUNCATE "
                        "(быстрее и явнее) или явный WHERE."
                    ),
                    severity=AntipatternSeverity.CRITICAL,
                    dialect="postgres",
                    snippet=f"DELETE FROM {tbl_name}",
                    rationale="Аналогично UPDATE без WHERE — массовое удаление.",
                    recommendation=(
                        "Если действительно нужно очистить — используйте TRUNCATE "
                        "(быстрее и явнее). Если выборочно — добавьте WHERE."
                    ),
                )
            )
            return findings
    return findings


__all__ = ["detect_missing_where_on_update_delete"]
