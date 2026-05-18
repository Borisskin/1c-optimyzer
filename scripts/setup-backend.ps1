# Создаёт backend venv и устанавливает dependencies.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $ProjectRoot "backend")
try {
    if (-not (Test-Path ".venv")) {
        py -3.11 -m venv .venv
    }
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
    Write-Host "`nBackend готов. Запуск sidecar:"
    Write-Host "  cd backend; .\.venv\Scripts\Activate.ps1; python -m optimyzer_backend"
} finally {
    Pop-Location
}
