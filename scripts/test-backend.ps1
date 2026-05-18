# Запускает pytest для backend.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $ProjectRoot "backend")
try {
    & ".\.venv\Scripts\python.exe" -m pytest -v
} finally {
    Pop-Location
}
