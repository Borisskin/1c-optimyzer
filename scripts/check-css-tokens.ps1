# Sprint 9 Phase D.2 — CSS design token lint check
#
# Запрет hardcoded hex-цветов в CSS modules (кроме #000, #fff, transparent).
# Использовать только var(--o-*) design tokens.
#
# Запуск:
#   pwsh scripts/check-css-tokens.ps1
#   npm run lint:css   (вызывает этот скрипт через package.json)
#
# Exit code: 0 = clean, 1 = violations found
#
# Whitelist: #000, #000000, #fff, #ffffff, transparent
# Исключение: строки где hex используется внутри определения переменной --o-*

param(
    [string]$Path = $null,
    [switch]$Fix = $false  # зарезервировано на будущее
)

# Resolve path relative to the script's own location (not CWD)
if (-not $Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Path = Join-Path $ScriptDir "..\frontend\src"
}

$violations = [System.Collections.ArrayList]::new()
$fileCount = 0
$allowedHex = @('#000', '#000000', '#fff', '#ffffff')

Get-ChildItem -Path $Path -Recurse -Filter "*.module.css" | ForEach-Object {
    $fileCount++
    $filePath = $_.FullName
    $content = Get-Content $filePath -Raw -Encoding UTF8

    # Ищем hex-цвета: #XXX, #XXXXXX, #XXXXXXXX (3, 6 или 8 hex digits)
    $hexPattern = [regex]'#[0-9a-fA-F]{3,8}\b'
    $matches = $hexPattern.Matches($content)

    foreach ($match in $matches) {
        $color = $match.Value.ToLower()

        # Whitelist: #000, #fff и их 6-digit эквиваленты
        if ($color -in $allowedHex) { continue }

        # Разрешаем hex внутри CSS переменной --o-*
        # (строка определения переменной, например: --o-brand: #1a2b3c;)
        $lineStart = $content.LastIndexOf("`n", $match.Index)
        if ($lineStart -lt 0) { $lineStart = 0 } else { $lineStart += 1 }
        $lineEnd = $content.IndexOf("`n", $match.Index)
        if ($lineEnd -lt 0) { $lineEnd = $content.Length }
        $line = $content.Substring($lineStart, $lineEnd - $lineStart).Trim()

        if ($line -match '--o-') { continue }  # в определении token'а — разрешено

        # Violation!
        $relPath = $filePath.Replace((Get-Location).Path + "\", "").Replace("\", "/")
        $lineNum = ($content.Substring(0, $match.Index) -split "`n").Count
        [void]$violations.Add([PSCustomObject]@{
            File    = $relPath
            Line    = $lineNum
            Color   = $color
            Context = ($line -replace '\s+', ' ')
        })
    }
}

Write-Host "CSS token lint: checked $fileCount .module.css files"

if ($violations.Count -gt 0) {
    Write-Host ""
    Write-Error "Found $($violations.Count) hardcoded color(s) in CSS modules:"
    Write-Host ""
    foreach ($v in $violations) {
        Write-Host "  $($v.File):$($v.Line)  $($v.Color)  in: $($v.Context)" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Fix: replace hardcoded colors with var(--o-*) design tokens." -ForegroundColor Yellow
    Write-Host "See: frontend/src/App.css for available tokens." -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: No hardcoded colors found in CSS modules." -ForegroundColor Green
exit 0
