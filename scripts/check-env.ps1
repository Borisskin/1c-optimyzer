# Pre-flight check: проверка окружения разработки.

$ErrorActionPreference = "Continue"

function Probe($label, $cmd) {
    try {
        $out = & cmd /c $cmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host ("  [OK]  {0,-12} {1}" -f $label, ($out -join ' ').Trim())
        } else {
            Write-Host ("  [!!]  {0,-12} FAILED: {1}" -f $label, $out) -ForegroundColor Yellow
        }
    } catch {
        Write-Host ("  [!!]  {0,-12} not found" -f $label) -ForegroundColor Red
    }
}

Write-Host "1C-Optimyzer — environment check`n"
Probe "node"   "node --version"
Probe "npm"    "npm --version"
Probe "python" "python --version"
Probe "cargo"  "cargo --version"
Probe "rustc"  "rustc --version"
Probe "git"    "git --version"

Write-Host "`nBackend venv:"
if (Test-Path "backend\.venv\Scripts\python.exe") {
    Write-Host "  [OK]  backend\.venv exists"
} else {
    Write-Host "  [!!]  backend\.venv missing — run scripts/setup-backend.ps1" -ForegroundColor Yellow
}

Write-Host "`nFrontend node_modules:"
if (Test-Path "frontend\node_modules") {
    Write-Host "  [OK]  frontend\node_modules exists"
} else {
    Write-Host "  [!!]  frontend\node_modules missing — cd frontend && npm install" -ForegroundColor Yellow
}
