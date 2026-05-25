# Чистит «осиротевших» python.exe от нашего uvicorn-sidecar.
# Таргетит ТОЛЬКО процессы, принадлежащие D:\1C-Optimyzer (uvicorn api.main:app --port 8001
# или optimyzer_backend). Чужие python (MCP, bsl-atlas, http.server, oauth_proxy_80.py) не трогает.
#
# Активный sidecar на :8001 определяется через Get-NetTCPConnection и исключается из выборки
# вместе со своими родителем/детьми.
#
# Использование:
#   .\scripts\kill-zombie-python.ps1                    # dry-run, печатает список и выходит
#   .\scripts\kill-zombie-python.ps1 -Apply             # реальное убийство
#   .\scripts\kill-zombie-python.ps1 -OlderThanMinutes 30 -Apply
#                                                       # убить только тех, кто старше 30 минут
#   .\scripts\kill-zombie-python.ps1 -ExcludePid 1320,28668 -Apply
#                                                       # явно исключить PID (для случая когда :8001 в reload-цикле)

[CmdletBinding()]
param(
    [switch]$Apply,
    [int]$OlderThanMinutes = 0,
    [int[]]$ExcludePid = @()
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\1C-Optimyzer"
$VenvPython  = Join-Path $ProjectRoot "server\.venv\Scripts\python.exe"

# 1) Активный sidecar — тот, кто реально слушает :8001. Его и его parent/child исключаем.
$ProtectedPids = New-Object System.Collections.Generic.HashSet[int]
foreach ($id in $ExcludePid) { [void]$ProtectedPids.Add($id) }

try {
    $listeners = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction Stop
    foreach ($conn in $listeners) {
        [void]$ProtectedPids.Add([int]$conn.OwningProcess)
    }
} catch {
    # Никто не слушает 8001 — это нормально, сервер может быть выключен.
}

# Расширяем защиту на родителей и детей активного PID (uvicorn запускает worker-child).
$allPy = Get-CimInstance Win32_Process -Filter "Name='python.exe'"
$expanded = $true
while ($expanded) {
    $expanded = $false
    foreach ($p in $allPy) {
        $pid_ = [int]$p.ProcessId
        $parent = [int]$p.ParentProcessId
        if ($ProtectedPids.Contains($pid_) -and -not $ProtectedPids.Contains($parent)) {
            [void]$ProtectedPids.Add($parent); $expanded = $true
        }
        if ($ProtectedPids.Contains($parent) -and -not $ProtectedPids.Contains($pid_)) {
            [void]$ProtectedPids.Add($pid_); $expanded = $true
        }
    }
}

# 2) Кандидаты — только наши uvicorn / optimyzer_backend.
$now = Get-Date
$candidates = foreach ($p in $allPy) {
    $cmd  = [string]$p.CommandLine
    $exe  = [string]$p.ExecutablePath
    $pid_ = [int]$p.ProcessId

    if ($ProtectedPids.Contains($pid_)) { continue }

    $isOurs =
        ($exe -and $exe.StartsWith($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) -or
        ($cmd -match '\boptimyzer_backend\b') -or
        ($cmd -match 'uvicorn' -and $cmd -match 'api\.main:app' -and $cmd -match '--port\s+8001')

    if (-not $isOurs) { continue }

    $start = $null
    try { $start = [Management.ManagementDateTimeConverter]::ToDateTime($p.CreationDate) } catch {}
    if ($OlderThanMinutes -gt 0 -and $start) {
        if (($now - $start).TotalMinutes -lt $OlderThanMinutes) { continue }
    }

    [pscustomobject]@{
        ProcId      = $pid_
        Parent      = [int]$p.ParentProcessId
        StartTime   = $start
        AgeMin      = if ($start) { [math]::Round(($now - $start).TotalMinutes, 1) } else { $null }
        Exe         = $exe
        CommandLine = $cmd
    }
}

if (-not $candidates) {
    Write-Host "[kill-zombie-python] no zombie sidecars to clean. Protected PIDs: $($ProtectedPids -join ', ')"
    exit 0
}

Write-Host "[kill-zombie-python] protected PIDs (active :8001 + family + explicit excludes): $($ProtectedPids -join ', ')"
Write-Host "[kill-zombie-python] candidates:"
$candidates | Format-Table ProcId, Parent, StartTime, AgeMin, Exe -AutoSize | Out-String | Write-Host

if (-not $Apply) {
    Write-Host "[kill-zombie-python] DRY-RUN -- add -Apply to really kill them."
    exit 0
}

foreach ($c in $candidates) {
    $cpid = $c.ProcId
    try {
        Stop-Process -Id $cpid -Force -ErrorAction Stop
        Write-Host ("[kill-zombie-python] killed PID {0}" -f $cpid)
    } catch {
        $err = $_.Exception.Message
        Write-Warning ("[kill-zombie-python] failed to kill PID {0}: {1}" -f $cpid, $err)
    }
}
