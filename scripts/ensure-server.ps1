#requires -version 5.1
<#
  ensure-server.ps1 - guarantees the local cloud server (FastAPI on :8001) is up and healthy.

  Why: the desktop app's AI features (logcfg wizard, plan/query explain) call the
  server at http://localhost:8001 directly. If it is not running - or wedged (port
  held but not serving HTTP) - those calls hang forever. start.bat runs this BEFORE
  the frontend so AI works with zero manual steps.

  Idempotent:
    - healthy server already on :8001  -> reuse, exit 0 fast
    - port held but /health fails      -> kill the wedged process tree, start fresh
    - port free                        -> start fresh
  The server runs detached & hidden; logs go to server\logs\server.log(.err.log).
  Never hard-fails the launcher: on error it exits 1 but start.bat keeps going so the
  app still opens for non-AI features.
#>
[CmdletBinding()]
param(
  [int]$Port = 8001,
  [int]$HealthTimeoutSec = 30
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot      # scripts\ -> repo root
$ServerDir   = Join-Path $ProjectRoot "server"
$Py          = Join-Path $ServerDir ".venv\Scripts\python.exe"
$LogDir      = Join-Path $ServerDir "logs"
$LogFile     = Join-Path $LogDir "server.log"
$ErrFile     = Join-Path $LogDir "server.err.log"
$HealthUrl   = "http://127.0.0.1:$Port/health"

function Test-ServerHealthy {
  try {
    $r = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    return ($r.StatusCode -eq 200)
  } catch {
    return $false
  }
}

# 1) Already healthy -> reuse (no duplicate spawn on repeated start.bat runs).
if (Test-ServerHealthy) {
  Write-Host "[ensure-server] :$Port already healthy - reuse."
  exit 0
}

# 2) Port held but not healthy -> wedged server. Kill owner + whole tree.
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
  foreach ($conn in $listeners) {
    $owner = [int]$conn.OwningProcess
    Write-Host "[ensure-server] :$Port held by wedged PID $owner - killing process tree."
    & taskkill /F /T /PID $owner 2>&1 | Out-String | Write-Host
  }
  Start-Sleep -Milliseconds 800
}

# 3) Start a fresh server (detached, hidden, logs to file).
if (-not (Test-Path $Py)) {
  Write-Warning "[ensure-server] venv python not found: $Py"
  Write-Warning "[ensure-server] AI server NOT started. Create venv: cd server; py -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
  exit 1
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$proc = Start-Process -FilePath $Py `
  -ArgumentList '-m','uvicorn','api.main:app','--host','127.0.0.1','--port',"$Port" `
  -WorkingDirectory $ServerDir -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $LogFile -RedirectStandardError $ErrFile
Write-Host "[ensure-server] started server PID=$($proc.Id); waiting for health (max ${HealthTimeoutSec}s)..."

# 4) Wait for health (or early exit / timeout).
$deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 700
  if (Test-ServerHealthy) {
    Write-Host "[ensure-server] :$Port is healthy now."
    exit 0
  }
  if ($proc.HasExited) {
    Write-Warning "[ensure-server] server exited early (code $($proc.ExitCode)). Last error log:"
    if (Test-Path $ErrFile) { Get-Content $ErrFile -Tail 25 | Out-String | Write-Host }
    exit 1
  }
}
Write-Warning "[ensure-server] server did not become healthy within ${HealthTimeoutSec}s. Last error log:"
if (Test-Path $ErrFile) { Get-Content $ErrFile -Tail 25 | Out-String | Write-Host }
exit 1
