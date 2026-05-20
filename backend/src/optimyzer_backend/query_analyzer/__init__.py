"""Sprint 4 — Query Analyzer.

Анализирует SDBL-запросы 1С на типичные антипаттерны производительности
по методике ЦУП 2.13.4 и Раздела 10 курса 1С:Эксперт. Возвращает findings
с line/col ranges + AI-переписанный вариант через Claude.

Архитектурное решение Sprint 4 (см. ADR-025):
    Sprint 4 использует ТОЛЬКО native rule engine. BSL Language Server
    выбран как НЕ-зависимость потому что он работает с языком BSL
    (`Процедура Х() Конец`), а SDBL (`ВЫБРАТЬ ... ИЗ ...`) — это отдельный
    embedded язык. Standalone SDBL парсинг через BSL LS требует hack-обёртки
    и не даёт преимуществ перед прямым regex/AST matching.

    Подробное обоснование: docs/BSL_LS_GAP_ANALYSIS.md

Public entry points:
    aggregator.analyze_query(query_text) -> dict
    ai_rewriter.QueryRewriter.rewrite(query_text, findings)
"""
