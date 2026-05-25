# Sprint 8 Phase A — PostgreSQL environment audit
# Использование: .\probe_pg_env.ps1 [-OutDir <path>]
# Сохраняет .txt отчёты по версии PG, extensions, GUC параметрам, custom types pgBase.

[CmdletBinding()]
param(
    [string]$OutDir = "D:\1C-Optimyzer\tools\sprint8_discovery\probe_results",
    [string]$PgPassword = "1111",
    [string]$PsqlPath = "C:\Program Files\PostgreSQL\18.1-2.1C\bin\psql.exe"
)

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
if (-not (Test-Path $PsqlPath)) {
    Write-Error "psql.exe not found at: $PsqlPath"
    exit 1
}

$env:PGPASSWORD = $PgPassword

function Run-Probe {
    param([string]$Db, [string]$Name, [string]$Sql)
    $out = Join-Path $OutDir "$Name.txt"
    & $PsqlPath -U postgres -h localhost -d $Db -c $Sql 2>&1 | Out-File -FilePath $out -Encoding utf8
    Write-Host "Saved: $out"
}

# --- Cat 1: PostgreSQL environment ---
Run-Probe -Db "postgres" -Name "01_version" -Sql "SELECT version();"
Run-Probe -Db "postgres" -Name "02a_installed_extensions_postgres" -Sql "SELECT name, default_version, installed_version FROM pg_available_extensions WHERE installed_version IS NOT NULL ORDER BY name;"
# ВАЖНО: 1С устанавливает свои extensions (mchar, fulleq, fasttrun) в РАБОЧУЮ базу, а не в postgres.
# Проверяем pgBase отдельно.
Run-Probe -Db "pgBase" -Name "02b_installed_extensions_pgBase" -Sql "SELECT extname, extversion FROM pg_extension ORDER BY extname;"
Run-Probe -Db "postgres" -Name "03_available_extensions" -Sql "SELECT name, default_version FROM pg_available_extensions ORDER BY name;"
Run-Probe -Db "postgres" -Name "04_key_guc" -Sql "SHOW shared_buffers; SHOW effective_cache_size; SHOW work_mem; SHOW max_connections; SHOW log_min_duration_statement; SHOW track_io_timing; SHOW config_file; SHOW log_directory; SHOW log_filename; SHOW logging_collector;"
Run-Probe -Db "postgres" -Name "05_databases" -Sql "SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size FROM pg_database WHERE datistemplate = false ORDER BY pg_database_size(datname) DESC;"

# --- Cat 2: pgBase schema (1С custom types & functions) ---
Run-Probe -Db "pgBase" -Name "10_pgbase_schemas" -Sql "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast') ORDER BY schema_name;"
Run-Probe -Db "pgBase" -Name "11_pgbase_table_count" -Sql "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
Run-Probe -Db "pgBase" -Name "12_pgbase_top_tables" -Sql "SELECT tablename, pg_size_pretty(pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename))) AS size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename)) DESC LIMIT 30;"
Run-Probe -Db "pgBase" -Name "13_pgbase_prefix_distribution" -Sql "SELECT split_part(tablename, '_', 1)||'_'||regexp_replace(split_part(tablename, '_', 2), '[0-9]+', '*') AS prefix, COUNT(*) AS cnt FROM pg_tables WHERE schemaname='public' AND tablename LIKE '\_%' GROUP BY 1 ORDER BY cnt DESC LIMIT 20;"
Run-Probe -Db "pgBase" -Name "14_pgbase_custom_types" -Sql "SELECT typname, typtype, typcategory FROM pg_type WHERE typname IN ('mchar','mvarchar') OR typname LIKE 'mchar%' OR typname LIKE 'mvarchar%' ORDER BY typname;"
Run-Probe -Db "pgBase" -Name "15_pgbase_custom_functions" -Sql "SELECT n.nspname AS schema, p.proname AS function, pg_get_function_arguments(p.oid) AS args FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE p.proname LIKE 'mchar_%' OR p.proname LIKE 'mvarchar_%' OR p.proname LIKE 'fasttrun%' OR p.proname LIKE 'full_eq%' ORDER BY p.proname;"
Run-Probe -Db "pgBase" -Name "16_pgbase_sample_table_struct" -Sql "\d+ _document201"
Run-Probe -Db "pgBase" -Name "17_pgbase_sample_indexes" -Sql "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname='public' AND tablename = '_document201' ORDER BY indexname;"

Write-Host "`nAll probes saved to: $OutDir"
