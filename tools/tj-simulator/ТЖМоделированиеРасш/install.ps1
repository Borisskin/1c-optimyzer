# Установка расширения ТЖМоделированиеРасш в базу 1С через DESIGNER /LoadConfigFromFiles.
# По умолчанию подключается к Srvr=localhost:2541;Ref=Test1CProf под пользователем BVS без пароля.
#
# С Sprint 3.5 расширение НЕ обязательно для работы МоделированиеТЖ.epf — обработка всегда
# запускает воркеров через 1cv8c.exe /Execute (отдельные клиент-сессии, гарантированный
# параллелизм транзакций). Расширение оставлено для возможных будущих сценариев, где может
# понадобиться запуск воркеров через ФоновыеЗадания.Выполнить.
#
# Перед запуском: закрой Конфигуратор на этой базе (DESIGNER не может работать параллельно
# со второй сессией Конфигуратора).

param(
	[string]$Server = 'localhost:2541',
	[string]$Ref = 'Test1CProf',
	[string]$User = 'BVS',
	[string]$Password = '',
	[string]$V8Exe = 'C:\Program Files\1cv8\8.3.27.1859\bin\1cv8.exe',
	[string]$ExtensionName = 'ТЖМоделированиеРасш',
	[string]$SrcDir = (Join-Path $PSScriptRoot 'src')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $V8Exe)) {
	Write-Error "Не найден 1cv8.exe по пути: $V8Exe. Проверь -V8Exe."
	exit 1
}
if (-not (Test-Path $SrcDir)) {
	Write-Error "Не найден каталог исходников: $SrcDir"
	exit 1
}

$logFile = Join-Path $env:TEMP "install_ext_$ExtensionName.log"

$args = @(
	'DESIGNER'
	'/S' + "$Server\$Ref"
	'/N' + $User
)
if ($Password) { $args += '/P' + $Password }
$args += @(
	'/DisableStartupMessages'
	'/LoadConfigFromFiles', $SrcDir
	'-Extension', $ExtensionName
	'/UpdateDBCfg'
	'/Out', $logFile
)

Write-Host "Запуск DESIGNER для установки расширения '$ExtensionName' в базу $Server\$Ref..."
Write-Host "Команда:"
Write-Host "  $V8Exe $($args -join ' ')"
Write-Host ''

$proc = Start-Process -FilePath $V8Exe -ArgumentList $args -NoNewWindow -Wait -PassThru
$exitCode = $proc.ExitCode

Write-Host ''
Write-Host "=== DESIGNER завершился с кодом $exitCode ==="
if (Test-Path $logFile) {
	Write-Host '--- Лог ---'
	Get-Content $logFile -Encoding UTF8 | ForEach-Object { Write-Host $_ }
	Write-Host '--- Конец лога ---'
}

if ($exitCode -eq 0) {
	Write-Host ''
	Write-Host '[OK] Расширение установлено и конфигурация БД обновлена.' -ForegroundColor Green
	Write-Host '     Теперь МоделированиеТЖ.epf будет использовать ФоновыеЗадания через ВоркерыТЖ.'
} else {
	Write-Host ''
	Write-Host "[FAIL] Установка не удалась. Проверь лог: $logFile" -ForegroundColor Red
	exit $exitCode
}
