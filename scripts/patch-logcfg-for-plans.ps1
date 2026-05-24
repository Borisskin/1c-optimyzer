<#
.SYNOPSIS
    Включает регистрацию SQL execution plans (planSQLText) в технологическом
    журнале 1С — добавляет <plan/> в logcfg.xml.

.DESCRIPTION
    Idempotent patch для logcfg.xml: добавляет <plan/> элемент внутрь <log>,
    если его ещё нет. После перезапуска ragent в DBMSSQL событиях ТЖ
    появится поле planSQLText (текстовое представление execution plan).

    Шаги:
      1. Backup logcfg.xml в logcfg.xml.backup.YYYYMMDD-HHMMSS
      2. Проверка наличия <plan/> в namespace http://v8.1c.ru/v8/tech-log
      3. Добавление <plan/> внутрь первого <log> элемента (sibling от <event>)
      4. Save обратно в logcfg.xml (UTF-8 без BOM)
      5. Restart "1C:Enterprise 8.3 Server Agent (x86-64)" (если -NoRestart не задан)

    Запускать с admin elevation (правка Program Files + restart сервиса).

.PARAMETER LogcfgPath
    Путь к logcfg.xml. По умолчанию C:\Program Files\1cv8\conf\logcfg.xml.

.PARAMETER NoRestart
    Не перезапускать ragent — изменение в logcfg.xml активируется только
    после следующего рестарта (вручную или по расписанию). Полезно если
    сейчас идёт работа в Конфигураторе и нельзя рвать сессии.

.PARAMETER DryRun
    Показать что будет сделано, но не менять файл и не рестартить сервис.

.EXAMPLE
    pwsh -File scripts\patch-logcfg-for-plans.ps1
    Стандартный запуск: patch + restart с дефолтным путём.

.EXAMPLE
    pwsh -File scripts\patch-logcfg-for-plans.ps1 -DryRun
    Только показать diff без изменений.

.EXAMPLE
    pwsh -File scripts\patch-logcfg-for-plans.ps1 -NoRestart
    Применить patch, но не дёргать сервис — рестартить вручную позже.

.NOTES
    Sprint 7 Phase D — Plan Analyzer (auto-extract DBMSSQL.Plan из ТЖ).
    См. docs/onboarding/enable-dbmssql-plans.md для полной инструкции.
#>

param(
    [string]$LogcfgPath = "C:\Program Files\1cv8\conf\logcfg.xml",
    [switch]$NoRestart,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# === 0. Self-elevation через UAC ===
# logcfg.xml лежит в Program Files → правка требует admin. Restart-Service
# для system service — тоже. Чтобы пользователю не пришлось вручную открывать
# admin-консоль, делаем re-launch текущего скрипта через Verb=RunAs (UAC).
# Появится стандартный диалог «Разрешить приложению вносить изменения?» → Yes.
$currentUser = New-Object System.Security.Principal.WindowsPrincipal(
    [System.Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $currentUser.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Требуется admin elevation — сейчас появится UAC промпт..." -ForegroundColor Yellow
    $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    if ($DryRun)    { $argList += "-DryRun" }
    if ($NoRestart) { $argList += "-NoRestart" }
    if ($LogcfgPath -ne "C:\Program Files\1cv8\conf\logcfg.xml") {
        $argList += @("-LogcfgPath", "`"$LogcfgPath`"")
    }
    try {
        $proc = Start-Process powershell -Verb RunAs -ArgumentList $argList -PassThru -Wait
        exit $proc.ExitCode
    } catch {
        Write-Error "UAC отклонён или не появился: $_"
        Write-Host "Запусти PowerShell от админа и выполни:" -ForegroundColor Yellow
        Write-Host "  & '$PSCommandPath'" -ForegroundColor Cyan
        exit 5
    }
}

# === 1. Проверка существования ===
if (-not (Test-Path $LogcfgPath)) {
    Write-Error "logcfg.xml не найден: $LogcfgPath"
    Write-Host "Проверь путь к 1С Enterprise: на твоей машине может быть другой" -ForegroundColor Yellow
    exit 1
}

Write-Host "logcfg.xml: $LogcfgPath" -ForegroundColor Cyan
$origSize = (Get-Item $LogcfgPath).Length
Write-Host "  размер: $origSize байт"

# === 2. Парсинг с учётом 1С namespace ===
# PreserveWhitespace=true критично: без него XmlDocument теряет все отступы
# и комментарии (точнее — теряет whitespace между элементами как nodes).
# В результате save → весь файл в одну строку, гигантский diff. Хотим
# сохранить оригинальное форматирование, изменив только нужное.
$xml = New-Object System.Xml.XmlDocument
$xml.PreserveWhitespace = $true
$xml.Load($LogcfgPath)
$ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace("tl", "http://v8.1c.ru/v8/tech-log")

# Проверяем существующий <plan/> на любом уровне внутри <config>.
$existingPlan = $xml.SelectSingleNode("//tl:plan", $ns)
if ($existingPlan) {
    Write-Host "<plan/> уже присутствует в logcfg.xml — изменений не требуется" -ForegroundColor Green
    Write-Host "  parent: $($existingPlan.ParentNode.LocalName)"
    exit 0
}

# Находим первый <log> — туда положим <plan/>.
$logNode = $xml.SelectSingleNode("//tl:log", $ns)
if (-not $logNode) {
    Write-Error "<log> элемент не найден в logcfg.xml — структура неожиданная"
    exit 2
}

# === 3. Создаём <plan/> в том же namespace + leading whitespace ===
# Существующий <log> заканчивается на "    </log>" с 4-space indent. Хочется
# чтобы <plan/> встал в той же стилистике как соседние <event>: с newline
# перед тегом и indent 8 spaces (sibling от <event>).
$indent = $xml.CreateWhitespace("`n        ")
$planElement = $xml.CreateElement("plan", "http://v8.1c.ru/v8/tech-log")
$logNode.AppendChild($indent) | Out-Null
$logNode.AppendChild($planElement) | Out-Null
# Финальный newline + 4 spaces чтобы </log> остался на своей строке с indent.
$tail = $xml.CreateWhitespace("`n    ")
$logNode.AppendChild($tail) | Out-Null

Write-Host "Создан <plan/> внутри <log> (location='$($logNode.GetAttribute('location'))')" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "" -ForegroundColor Cyan
    Write-Host "=== DRY RUN — изменения НЕ применены ===" -ForegroundColor Yellow
    Write-Host "Финальный фрагмент <log>:"
    Write-Host $logNode.OuterXml.Substring(0, [Math]::Min(500, $logNode.OuterXml.Length)) -ForegroundColor Gray
    exit 0
}

# === 4. Backup ДО записи ===
$backup = "$LogcfgPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $LogcfgPath $backup -Force
Write-Host "Backup: $backup" -ForegroundColor Cyan

# === 5. Save (UTF-8 без BOM, 1С парсер требователен к encoding) ===
# XmlDocument.Save через FileStream + XmlWriter с UTF8NoBOM, иначе .NET
# пишет UTF-8 с BOM, что в некоторых версиях платформы ломает чтение.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$xmlSettings = New-Object System.Xml.XmlWriterSettings
# Indent=$false критично: с PreserveWhitespace мы уже храним оригинальный
# whitespace как nodes; если Indent=$true — XmlWriter переформатирует всё
# заново, ломая комментарии и сжимая файл.
$xmlSettings.Indent = $false
$xmlSettings.Encoding = $utf8NoBom
$xmlSettings.OmitXmlDeclaration = $false

$writer = [System.Xml.XmlWriter]::Create($LogcfgPath, $xmlSettings)
try {
    $xml.Save($writer)
} finally {
    $writer.Close()
}

$newSize = (Get-Item $LogcfgPath).Length
Write-Host "Сохранено: $LogcfgPath ($newSize байт, было $origSize)" -ForegroundColor Green

# === 6. Restart 1C Server Agent ===
if ($NoRestart) {
    Write-Host ""
    Write-Host "Skip restart (-NoRestart). ВАЖНО: перезапусти ragent вручную для активации." -ForegroundColor Yellow
    Write-Host "  Get-Service '1C:Enterprise 8.3 Server Agent (x86-64)' | Restart-Service -Force"
    exit 0
}

$serviceName = "1C:Enterprise 8.3 Server Agent (x86-64)"
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Warning "Сервис '$serviceName' не найден."
    Write-Host "  Возможно у тебя другая редакция (x86 / другая версия). Перезапусти ragent вручную." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Перезапуск '$serviceName'..." -ForegroundColor Cyan
Write-Host "  ВНИМАНИЕ: все открытые 1С-сессии в Предприятии и Конфигураторе будут разорваны!" -ForegroundColor Yellow

try {
    Restart-Service $service.Name -Force -ErrorAction Stop
    Start-Sleep -Seconds 3
    $afterStatus = (Get-Service -Name $serviceName).Status
    if ($afterStatus -eq "Running") {
        Write-Host "Сервис снова работает (Status=$afterStatus)" -ForegroundColor Green
    } else {
        Write-Warning "После рестарта Status=$afterStatus — проверь руками"
        exit 3
    }
} catch {
    Write-Error "Ошибка рестарта: $_"
    Write-Host "Backup logcfg сохранён в: $backup" -ForegroundColor Yellow
    Write-Host "Чтобы откатиться: Copy-Item '$backup' '$LogcfgPath' -Force" -ForegroundColor Yellow
    exit 4
}

Write-Host ""
Write-Host "=== Готово ===" -ForegroundColor Green
Write-Host "В следующих DBMSSQL событиях ТЖ появится поле planSQLText."
Write-Host "Проверить — выполнить любой длительный SQL запрос (например через"
Write-Host "tj-simulator кнопку 5) и посмотреть свежий .log файл в:"
Write-Host "  $($logNode.GetAttribute('location'))" -ForegroundColor Cyan
