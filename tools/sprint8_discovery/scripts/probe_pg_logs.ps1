# Sprint 8 Phase A — PostgreSQL log files probe
# Использование: .\probe_pg_logs.ps1 [-OutDir <path>]
# Находит последние логи PG, копирует sample в pg_logs/

[CmdletBinding()]
param(
    [string]$PgLogDir = "C:\Program Files\PostgreSQL\18.1-2.1C\data\log",
    [string]$OutDir = "D:\1C-Optimyzer\tools\sprint8_discovery\pg_logs"
)

if (-not (Test-Path $PgLogDir)) {
    Write-Error "PG log dir not found: $PgLogDir"
    exit 1
}

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

Write-Host "Recent PG logs:"
Get-ChildItem $PgLogDir | Sort-Object LastWriteTime -Descending |
    Select-Object Name, Length, LastWriteTime -First 10 | Format-Table -AutoSize

# Копируем последние 3 не-пустых лога
$samples = Get-ChildItem $PgLogDir |
    Where-Object { $_.Length -gt 0 } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 3

foreach ($f in $samples) {
    $dst = Join-Path $OutDir $f.Name
    Copy-Item $f.FullName $dst -Force
    Write-Host "Copied: $($f.Name) ($([math]::Round($f.Length / 1KB, 1)) KB)"
}

Write-Host "`nFormat overview (last log):"
if ($samples) {
    $first = $samples[0]
    Get-Content $first.FullName -TotalCount 5
}
