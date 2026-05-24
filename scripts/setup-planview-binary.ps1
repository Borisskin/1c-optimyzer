# Sprint 7 — Setup bundled PerformanceStudio binary для Tauri build.
#
# Скачивает PerformanceStudio CLI (Erik Darling Data, MIT) в
# frontend/src-tauri/binaries/planview/ перед `tauri build`.
# Бинарь содержит self-contained .NET 10 runtime (~70 MB после распаковки),
# поэтому отдельный SDK на машине пользователя не требуется.
#
# Использование:
#   PS> .\scripts\setup-planview-binary.ps1                # обычный режим
#   PS> .\scripts\setup-planview-binary.ps1 -Force          # пересоздать
#
# Зависимости: Windows PowerShell 5.1+ или PowerShell 7+, доступ к интернету.

[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Версия PerformanceStudio (PlanViewer.Cli) — синхронизировано с Sprint 7 docs.
$PlanViewVersion = "1.11.2"
$ZipName = "PerformanceStudio-win-x64.zip"

# Размещение бинарника — в frontend/src-tauri/binaries/ (gitignored).
$RepoRoot = Split-Path $PSScriptRoot -Parent
$BinariesRoot = Join-Path $RepoRoot "frontend\src-tauri\binaries"
$PlanviewDir = Join-Path $BinariesRoot "planview"
$ExeName = "PlanViewer.Cli.exe"

function Write-Step($msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

Write-Step "PerformanceStudio CLI v$PlanViewVersion"

$exePath = Join-Path $PlanviewDir $ExeName
if ((Test-Path $exePath) -and -not $Force) {
    Write-Host "  Already installed: $exePath" -ForegroundColor Green
    $sizeMb = [math]::Round((Get-ChildItem $PlanviewDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
    Write-Host "  Total size of planview/: $sizeMb MB" -ForegroundColor Green
    return
}

New-Item -ItemType Directory -Path $PlanviewDir -Force | Out-Null

$url = "https://github.com/erikdarlingdata/PerformanceStudio/releases/download/v$PlanViewVersion/$ZipName"
$tmpZip = Join-Path $env:TEMP "PerformanceStudio-win-x64-$PlanViewVersion.zip"

if ((-not (Test-Path $tmpZip)) -or $Force) {
    Write-Host "  Downloading: $url"
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $url -OutFile $tmpZip -UseBasicParsing
    $zipSize = [math]::Round((Get-Item $tmpZip).Length / 1MB, 1)
    Write-Host "  Downloaded: $zipSize MB" -ForegroundColor Green
} else {
    Write-Host "  Cached download: $tmpZip" -ForegroundColor Green
}

Write-Host "  Extracting..."
$tmpExtract = Join-Path $env:TEMP "planview-extracted-$([guid]::NewGuid().Guid)"
Expand-Archive -Path $tmpZip -DestinationPath $tmpExtract -Force

# Зип содержит файлы прямо на корне (PlanViewer.Cli.exe + .dll). Копируем всё.
Remove-Item -Recurse -Force $PlanviewDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $PlanviewDir | Out-Null
Get-ChildItem $tmpExtract -Force | ForEach-Object {
    Move-Item -Path $_.FullName -Destination $PlanviewDir
}
Remove-Item -Recurse -Force $tmpExtract

if (-not (Test-Path $exePath)) {
    throw "После распаковки не найден $ExeName. Проверь содержимое архива."
}

Write-Host "  Installed: $PlanviewDir" -ForegroundColor Green

# Verify integration — простая проверка что бинарь запускается.
Write-Step "Verifying PlanViewer.Cli"
try {
    $versionOut = & $exePath --version 2>&1 | Select-Object -First 3
    if ($versionOut) {
        Write-Host "  $versionOut" -ForegroundColor Green
    } else {
        $helpOut = & $exePath --help 2>&1 | Select-Object -First 1
        Write-Host "  ${helpOut}" -ForegroundColor Green
    }
} catch {
    Write-Warning "Не удалось запустить $ExeName — возможно нужны runtime dependencies"
}

Write-Host ""
$totalMb = [math]::Round((Get-ChildItem $PlanviewDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "Setup complete. Total size of planview/: $totalMb MB" -ForegroundColor Cyan
