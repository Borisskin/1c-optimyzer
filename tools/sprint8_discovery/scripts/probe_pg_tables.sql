-- Sprint 8 Phase A — pgBase tables/schemas probe
-- Использование:
--   psql -U postgres -h localhost -d pgBase -f probe_pg_tables.sql > probe_pg_tables.txt
-- (заранее $env:PGPASSWORD = '1111')

\echo === Schemas ===
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast')
ORDER BY schema_name;

\echo === Tables count ===
SELECT COUNT(*) AS public_tables
FROM pg_tables
WHERE schemaname='public';

\echo === Top-30 largest tables ===
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename))) AS size
FROM pg_tables
WHERE schemaname='public'
ORDER BY pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename)) DESC
LIMIT 30;

\echo === 1C table prefix distribution ===
SELECT
    split_part(tablename, '_', 1)||'_'||regexp_replace(split_part(tablename, '_', 2), '[0-9]+', '*') AS prefix,
    COUNT(*) AS cnt
FROM pg_tables
WHERE schemaname='public' AND tablename LIKE '\_%'
GROUP BY 1
ORDER BY cnt DESC
LIMIT 25;

\echo === Custom 1C types (mchar / mvarchar) ===
SELECT typname, typtype, typcategory
FROM pg_type
WHERE typname IN ('mchar', 'mvarchar')
   OR typname LIKE 'mchar%'
   OR typname LIKE 'mvarchar%'
ORDER BY typname;

\echo === Custom 1C functions on mchar/mvarchar ===
SELECT n.nspname AS schema, p.proname AS function, pg_get_function_arguments(p.oid) AS args
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.proname LIKE 'mchar_%' OR p.proname LIKE 'mvarchar_%'
   OR p.proname LIKE 'fasttrun%' OR p.proname LIKE 'full_eq%'
ORDER BY p.proname
LIMIT 50;

\echo === Sample table structure (_document201) ===
\d+ _document201

\echo === Sample table indexes (_document201) ===
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname='public' AND tablename = '_document201'
ORDER BY indexname;
