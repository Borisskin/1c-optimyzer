# Удаление расширения ТЖМоделированиеРасш из базы.
# После удаления МоделированиеТЖ.epf переключится на fallback-режим (1cv8c.exe + WScript).

param(
	[string]$Server = 'localhost:2541',
	[string]$Ref = 'Test1CProf',
	[string]$User = 'BVS',
	[string]$Password = '',
	[string]$V8Exe = 'C:\Program Files\1cv8\8.3.27.1859\bin\1cv8.exe',
	[string]$ExtensionName = 'ТЖМоделированиеРасш'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $V8Exe)) {
	Write-Error "Не найден 1cv8.exe: $V8Exe"
	exit 1
}

$logFile = Join-Path $env:TEMP "uninstall_ext_$ExtensionName.log"

$args = @(
	'DESIGNER'
	'/S' + "$Server\$Ref"
	'/N' + $User
)
if ($Password) { $args += '/P' + $Password }
$args += @(
	'/DisableStartupMessages'
	'/DeleteCfg', '-Extension', $ExtensionName
	'/UpdateDBCfg'
	'/Out', $logFile
)

Write-Host "Удаление расширения '$ExtensionName' из базы $Server\$Ref..."
$proc = Start-Process -FilePath $V8Exe -ArgumentList $args -NoNewWindow -Wait -PassThru

if (Test-Path $logFile) {
	Get-Content $logFile -Encoding UTF8 | ForEach-Object { Write-Host $_ }
}

if ($proc.ExitCode -eq 0) {
	Write-Host "[OK] Расширение удалено." -ForegroundColor Green
} else {
	Write-Host "[FAIL] Код $($proc.ExitCode). Лог: $logFile" -ForegroundColor Red
	exit $proc.ExitCode
}
