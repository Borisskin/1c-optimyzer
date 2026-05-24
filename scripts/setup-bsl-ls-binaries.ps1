# Sprint 6 — Setup bundled binaries для Tauri build.
#
# Скачивает Eclipse Temurin JRE 21 + bsl-language-server JAR в
# frontend/src-tauri/binaries/ перед `tauri build` (или `tauri dev` если нужен
# реальный bsl-LS subprocess).
#
# Использование:
#   PS> .\scripts\setup-bsl-ls-binaries.ps1                  # обычный режим
#   PS> .\scripts\setup-bsl-ls-binaries.ps1 -Force            # пересоздать всё
#   PS> .\scripts\setup-bsl-ls-binaries.ps1 -SkipJre          # JRE уже есть
#
# Зависимости: Windows PowerShell 5.1+ или PowerShell 7+, доступ к интернету.

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipJre,
    [switch]$SkipBsl
)

$ErrorActionPreference = "Stop"

# Конфигурация версий — синхронизировано с docs/sales_sprint/SPRINT_6_PROMT.md.
$BslLsVersion = "0.29.0"
$JreTag = "jdk-21.0.11+10"
$JreShortVer = "21.0.11_10"

# SHA256 (с https://github.com/adoptium/temurin21-binaries/releases).
$JreSha256 = "be26677aaa20b39a62edcaab4c8857a8b76673b0f45abc0b6143b142b62717e4"

# Размещение бинарников — в frontend/src-tauri/binaries/ (gitignored).
$RepoRoot = Split-Path $PSScriptRoot -Parent
$BinariesRoot = Join-Path $RepoRoot "frontend\src-tauri\binaries"
$BslLsDir = Join-Path $BinariesRoot "bsl-ls"
$JreDir = Join-Path $BinariesRoot "jre-21"

function Write-Step($msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Test-Sha256($filePath, $expectedHash) {
    $actual = (Get-FileHash $filePath -Algorithm SHA256).Hash.ToLower()
    return $actual -eq $expectedHash.ToLower()
}

# ---- bsl-language-server JAR ----

if (-not $SkipBsl) {
    Write-Step "bsl-language-server $BslLsVersion"
    $jarName = "bsl-language-server-$BslLsVersion-exec.jar"
    $jarPath = Join-Path $BslLsDir $jarName

    if ((Test-Path $jarPath) -and -not $Force) {
        Write-Host "  Already installed: $jarPath" -ForegroundColor Green
    } else {
        New-Item -ItemType Directory -Path $BslLsDir -Force | Out-Null
        $url = "https://github.com/1c-syntax/bsl-language-server/releases/download/v$BslLsVersion/$jarName"
        Write-Host "  Downloading: $url"
        Invoke-WebRequest -Uri $url -OutFile $jarPath -UseBasicParsing
        $size = [math]::Round((Get-Item $jarPath).Length / 1MB, 1)
        Write-Host "  Saved: $jarPath ($size MB)" -ForegroundColor Green
    }
}

# ---- Eclipse Temurin JRE 21 ----

if (-not $SkipJre) {
    Write-Step "Eclipse Temurin JRE $JreTag"
    $javaExe = Join-Path $JreDir "bin\java.exe"

    if ((Test-Path $javaExe) -and -not $Force) {
        Write-Host "  Already installed: $javaExe" -ForegroundColor Green
    } else {
        $zipName = "OpenJDK21U-jre_x64_windows_hotspot_$JreShortVer.zip"
        $tagEnc = $JreTag.Replace("+", "%2B")
        $url = "https://github.com/adoptium/temurin21-binaries/releases/download/$tagEnc/$zipName"
        $tmpZip = Join-Path $env:TEMP $zipName
        Write-Host "  Downloading: $url"
        Invoke-WebRequest -Uri $url -OutFile $tmpZip -UseBasicParsing

        Write-Host "  Verifying SHA256..."
        if (-not (Test-Sha256 $tmpZip $JreSha256)) {
            Remove-Item $tmpZip -Force
            throw "SHA256 mismatch для JRE — отменяю установку"
        }
        Write-Host "  SHA256 OK" -ForegroundColor Green

        $tmpExtract = Join-Path $env:TEMP "jre-21-extracted-$([guid]::NewGuid().Guid)"
        Expand-Archive -Path $tmpZip -DestinationPath $tmpExtract -Force
        $innerDir = (Get-ChildItem $tmpExtract -Directory)[0].FullName
        Remove-Item -Recurse -Force $JreDir -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path $JreDir | Out-Null
        Get-ChildItem $innerDir | ForEach-Object {
            Move-Item -Path $_.FullName -Destination $JreDir
        }
        Remove-Item -Recurse -Force $tmpExtract, $tmpZip

        Write-Host "  Installed: $JreDir" -ForegroundColor Green
    }

    # Verify integration с bsl-LS jar.
    Write-Step "Verifying JRE + bsl-LS integration"
    $jarPath = Join-Path $BslLsDir "bsl-language-server-$BslLsVersion-exec.jar"
    if (-not (Test-Path $jarPath)) {
        Write-Warning "bsl-LS jar отсутствует ($jarPath) — пропускаю integration test"
    } else {
        $version = & $javaExe -jar $jarPath --version 2>&1 | Select-String "version:" | Select-Object -Last 1
        if ($version) {
            Write-Host "  $version" -ForegroundColor Green
        } else {
            Write-Warning "Не удалось получить bsl-LS версию — что-то не так"
        }
    }
}

Write-Host ""
Write-Host "Setup complete. Total size of binaries/:" -ForegroundColor Cyan
$totalMb = [math]::Round((Get-ChildItem $BinariesRoot -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "  $totalMb MB" -ForegroundColor Green
