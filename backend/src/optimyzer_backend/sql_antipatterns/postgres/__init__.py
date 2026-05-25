"""PostgreSQL antipatterns — 15 детекторов Sprint 8 Phase C.

Каталог:
    1.  offset_without_limit          — OFFSET без LIMIT
    2.  large_offset_pagination       — OFFSET > 1000
    3.  ilike_without_trgm            — ILIKE '%text%' без pg_trgm GIN
    4.  like_with_leading_wildcard    — LIKE '%text' (1С-aware)
    5.  not_in_with_subquery          — NOT IN с подзапросом
    6.  jsonb_without_gin             — JSONB операции без GIN индекса
    7.  cast_in_where_predicate       — CAST/функция на колонке (1С-aware mchar)
    8.  union_instead_of_union_all    — UNION (с implicit SORT+UNIQUE)
    9.  subquery_in_select_list       — correlated subquery в SELECT
    10. distinct_on_large_result      — DISTINCT + JOIN heuristic
    11. implicit_type_cast            — '123' vs 123 неявный cast (1С-aware)
    12. select_star_with_join         — SELECT * + JOIN (1С-aware: skip)
    13. order_by_random_with_limit    — ORDER BY RANDOM() LIMIT N
    14. missing_where_on_update_delete — UPDATE/DELETE без WHERE (CRITICAL)
    15. mchar_vs_text_comparison      — 1С-specific: mchar/text mismatch

Public API:
    POSTGRES_DETECTORS — список callable detector(ast, is_1c_context=False)
    detect_1c_context(sql) — heuristic для определения 1С-context
"""

from optimyzer_backend.sql_antipatterns.postgres._helpers import detect_1c_context
from optimyzer_backend.sql_antipatterns.postgres.cast_in_where_predicate import (
    detect_cast_in_where_predicate,
)
from optimyzer_backend.sql_antipatterns.postgres.distinct_on_large_result import (
    detect_distinct_on_large_result,
)
from optimyzer_backend.sql_antipatterns.postgres.ilike_without_trgm import (
    detect_ilike_without_trgm,
)
from optimyzer_backend.sql_antipatterns.postgres.implicit_type_cast import (
    detect_implicit_type_cast,
)
from optimyzer_backend.sql_antipatterns.postgres.jsonb_without_gin import (
    detect_jsonb_without_gin,
)
from optimyzer_backend.sql_antipatterns.postgres.large_offset_pagination import (
    detect_large_offset_pagination,
)
from optimyzer_backend.sql_antipatterns.postgres.like_with_leading_wildcard import (
    detect_like_with_leading_wildcard,
)
from optimyzer_backend.sql_antipatterns.postgres.mchar_vs_text_comparison import (
    detect_mchar_vs_text_comparison,
)
from optimyzer_backend.sql_antipatterns.postgres.missing_where_on_update_delete import (
    detect_missing_where_on_update_delete,
)
from optimyzer_backend.sql_antipatterns.postgres.not_in_with_subquery import (
    detect_not_in_with_subquery_pg,
)
from optimyzer_backend.sql_antipatterns.postgres.offset_without_limit import (
    detect_offset_without_limit,
)
from optimyzer_backend.sql_antipatterns.postgres.order_by_random_with_limit import (
    detect_order_by_random_with_limit,
)
from optimyzer_backend.sql_antipatterns.postgres.select_star_with_join import (
    detect_select_star_with_join,
)
from optimyzer_backend.sql_antipatterns.postgres.subquery_in_select_list import (
    detect_subquery_in_select_list,
)
from optimyzer_backend.sql_antipatterns.postgres.union_instead_of_union_all import (
    detect_union_instead_of_union_all,
)

POSTGRES_DETECTORS = [
    detect_missing_where_on_update_delete,  # CRITICAL — первым в списке
    detect_offset_without_limit,
    detect_large_offset_pagination,
    detect_order_by_random_with_limit,
    detect_ilike_without_trgm,
    detect_like_with_leading_wildcard,
    detect_not_in_with_subquery_pg,
    detect_cast_in_where_predicate,
    detect_implicit_type_cast,
    detect_subquery_in_select_list,
    detect_mchar_vs_text_comparison,
    detect_jsonb_without_gin,
    detect_union_instead_of_union_all,
    detect_distinct_on_large_result,
    detect_select_star_with_join,
]

__all__ = [
    "POSTGRES_DETECTORS",
    "detect_1c_context",
    "detect_cast_in_where_predicate",
    "detect_distinct_on_large_result",
    "detect_ilike_without_trgm",
    "detect_implicit_type_cast",
    "detect_jsonb_without_gin",
    "detect_large_offset_pagination",
    "detect_like_with_leading_wildcard",
    "detect_mchar_vs_text_comparison",
    "detect_missing_where_on_update_delete",
    "detect_not_in_with_subquery_pg",
    "detect_offset_without_limit",
    "detect_order_by_random_with_limit",
    "detect_select_star_with_join",
    "detect_subquery_in_select_list",
    "detect_union_instead_of_union_all",
]
