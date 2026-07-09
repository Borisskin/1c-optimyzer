# Собирает Python sidecar в standalone exe (PyInstaller onedir) и кладёт
# его в frontend/src-tauri/binaries/backend/ — оттуда tauri.conf.json
# bundle.resources упаковывает его в .msi. Конечному пользователю Python
# после этого не нужен (см. frontend/src-tauri/src/sidecar.rs).
#
# Запускать перед `npm run tauri build`, если менялся код backend/.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$TargetDir = Join-Path $ProjectRoot "frontend\src-tauri\binaries\backend"

Push-Location $Backend
try {
    if (-not (Test-Path ".venv")) {
        throw "backend/.venv не найден. Сначала: pwsh scripts/setup-backend.ps1"
    }
    & ".\.venv\Scripts\python.exe" -m pip show pyinstaller *> $null
    if ($LASTEXITCODE -ne 0) {
        & ".\.venv\Scripts\python.exe" -m pip install pyinstaller
    }

    & ".\.venv\Scripts\python.exe" -m PyInstaller `
        --name optimyzer_backend --onedir --noconfirm --clean `
        --collect-all duckdb --collect-all pyarrow --collect-all sqlglot `
        -p src `
        src/optimyzer_backend/__main__.py

    if (Test-Path $TargetDir) {
        Remove-Item -Recurse -Force $TargetDir
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $TargetDir) | Out-Null
    Copy-Item -Recurse "dist\optimyzer_backend" $TargetDir

    Write-Host "`nGotovo: $TargetDir\optimyzer_backend.exe"
} finally {
    Pop-Location
}
