"""T-SQL (MSSQL) antipatterns — 9 детекторов Sprint 6.

Public API:
    TSQL_DETECTORS — список callable detector(ast, is_1c_context=False)

Каталог:
    not_in_with_subquery, left_join_filtered, or_in_where, function_on_column,
    leading_wildcard_like, select_star, cross_join, implicit_convert,
    large_in_list
"""

from optimyzer_backend.sql_antipatterns.tsql.detectors import (
    TSQL_DETECTORS,
    detect_cross_join,
    detect_function_on_column,
    detect_implicit_convert,
    detect_large_in_list,
    detect_leading_wildcard_like,
    detect_left_join_filtered,
    detect_not_in_with_subquery,
    detect_or_in_where,
    detect_select_star,
)

__all__ = [
    "TSQL_DETECTORS",
    "detect_cross_join",
    "detect_function_on_column",
    "detect_implicit_convert",
    "detect_large_in_list",
    "detect_leading_wildcard_like",
    "detect_left_join_filtered",
    "detect_not_in_with_subquery",
    "detect_or_in_where",
    "detect_select_star",
]
