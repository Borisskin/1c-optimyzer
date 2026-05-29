#requires -version 5.1
<#
  stop-server.ps1 - stops the local cloud server (uvicorn api.main:app on :8001).

  Called by start.bat right after the app window is closed, so the AI server does
  NOT outlive the app. Model: launch start.bat -> server runs; close app -> server stops.
  Targets ONLY our uvicorn cloud server (by command line) - never other python
  (MCP, backend sidecar, etc.). Safe no-op when nothing is running.
#>
[CmdletBinding()]
param([int]$Port = 8001)

$ErrorActionPreference = "Continue"

$killed = @()
$servers = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'api\.main:app' }
foreach ($p in $servers) {
  & taskkill /F /T /PID $p.ProcessId 2>$null | Out-Null
  $killed += $p.ProcessId
}

Start-Sleep -Milliseconds 400
$still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($still) {
  Write-Host "[stop-server] :$Port still held by PID $($still.OwningProcess) (not our cloud server) - left as is."
} elseif ($killed.Count) {
  Write-Host "[stop-server] stopped cloud server (PID $($killed -join ', ')). :$Port is free."
} else {
  Write-Host "[stop-server] nothing to stop. :$Port is free."
}
