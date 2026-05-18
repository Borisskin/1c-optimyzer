# Запускает Tauri dev mode (frontend + Rust shell + Python sidecar).
# Перед запуском убедитесь:
#   - backend\.venv с установленными dependencies (scripts/setup-backend.ps1)
#   - frontend\node_modules (npm install)
#   - python в PATH (sidecar пока запускается через `python -m optimyzer_backend`)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $ProjectRoot "frontend")
try {
    npm run tauri dev
} finally {
    Pop-Location
}
