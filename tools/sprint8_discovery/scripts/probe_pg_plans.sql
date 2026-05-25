-- Sprint 8 Phase A — EXPLAIN format probes on pgBase
-- Цель: собрать реальные JSON/TEXT outputs от PG 18.1-2.1C для понимания структуры
-- что должен парсить наш будущий PG plan analyzer.

-- =============================================================================
-- Test 1: Simple SELECT с фильтром по primary key
-- _reference68 — справочник, ~150 строк типично
-- =============================================================================
EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT * FROM _reference68 LIMIT 100;

-- =============================================================================
-- Test 2: JOIN двух таблиц (документ + справочник по ссылке)
-- _document201 (Реализация) + _reference68 (один из справочников)
-- _fld5340rref — поле-ссылка в документе
-- =============================================================================
EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT d._idrref, d._date_time, d._number, r._idrref AS ref_id
FROM _document201 d
LEFT JOIN _reference68 r ON d._fld5340rref = r._idrref
WHERE d._fld11355 = E'\\x00\\x00\\x00\\x01'::bytea
  AND d._date_time >= '2024-01-01'::timestamp
LIMIT 100;

-- =============================================================================
-- Test 3: GROUP BY с агрегацией (типичный отчёт)
-- Подсчёт документов по дате
-- =============================================================================
EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT
    date_trunc('day', _date_time)::date AS doc_day,
    COUNT(*) AS docs_count,
    SUM(CASE WHEN _posted THEN 1 ELSE 0 END) AS posted_count
FROM _document201
WHERE _fld11355 = E'\\x00\\x00\\x00\\x01'::bytea
GROUP BY date_trunc('day', _date_time)::date
ORDER BY doc_day DESC
LIMIT 30;
