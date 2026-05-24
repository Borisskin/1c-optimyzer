<#
.SYNOPSIS
    Включает регистрацию SQL execution plans (planSQLText) в технологическом
    журнале 1С — добавляет <plan><event>...</event></plan> в logcfg.xml.

.IMPORTANT
    KNOWN ISSUE на 2026-05-25: на 1С 8.3.27.1859 + MSSQL ни один из 6
    проверенных синтаксисов logcfg (<plan/>, <plansql/>, <property name='*plan*'/>)
    не активирует запись planSQLText. См. docs/sales_sprint/SPRINT_7_KNOWN_ISSUE_planSQLText.md
    для деталей расследования и гипотез (SHOWPLAN permissions, изменения в 8.3.27,
    Performance Studio Extension). Скрипт делает то что должно работать ПО ДОКУМЕНТАЦИИ;
    если ты на 8.3.27 — после прогона убедись что planSQLText реально появился
    в C:\1C-TechLog\rphost_*/.log, иначе нужна доп. диагностика.

.DESCRIPTION
    ВАЖНО: ранее (Sprint 7 Phase D первая версия) скрипт вставлял пустой <plan/>.
    Это БЕСПОЛЕЗНО: согласно ИТС, <plan> работает как контейнер-фильтр, ему нужен
    вложенный <event> блок с критериями отбора, иначе планы для нулевого набора
    событий = ни для чего. Версия 2 вставляет правильную структуру.

    Idempotent patch для logcfg.xml:
      1. Backup logcfg.xml в logcfg.xml.backup.YYYYMMDD-HHMMSS
      2. Detect конфликтные состояния (несколько <plan>, пустой <plan/>, мусорные
         комментарии от предыдущих экспериментов). Если найдены — restore из
         последнего backup'а (если есть), потом patch.
      3. Если <plan> с правильным <event>DBMSSQL</event> уже есть — ничего не
         меняем (idempotent).
      4. Иначе добавляем правильный <plan><event>...</event></plan> внутрь <log>.
      5. Save (UTF-8 без BOM, preserve original whitespace и комментарии).
      6. Restart 1C Server Agent (если -NoRestart не задан).

    Default фильтр в <plan><event>: DBMSSQL duration > 10 (100 мс). Это покрывает
    тестовый сценарий tj-simulator кнопка 5 (запросы > 200мс) и не раздувает
    архив до неприемлемых размеров на нормальной нагрузке.

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
    [switch]$DryRun,
    # Длительность в сотых секунды (centiseconds). 10 = 100 мс, 100 = 1 сек.
    # Меньше число — больше планов в архиве. На тестовой нагрузке 10 ОК.
    [int]$DurationThreshold = 10,
    # Принудительно восстановить из последнего backup перед patch'ем.
    # Используется когда файл в chaos state (несколько <plan>, мусор-комментарии).
    [switch]$Restore
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
    if ($Restore)   { $argList += "-Restore" }
    $argList += @("-DurationThreshold", $DurationThreshold)
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

# === 1.5. Если -Restore — восстановить из последнего backup перед patch ===
$NS = "http://v8.1c.ru/v8/tech-log"
function Restore-FromBackup {
    param([string]$Target)
    $backupDir = Split-Path $Target -Parent
    $backupName = (Split-Path $Target -Leaf) + ".backup.*"
    $latest = Get-ChildItem -Path $backupDir -Filter $backupName -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        Write-Warning "Нет backup'ов для restore (искал $backupDir\$backupName)"
        return $false
    }
    Write-Host "Восстанавливаю из backup: $($latest.Name) ($(($latest.Length)) байт)" -ForegroundColor Yellow
    if (-not $DryRun) {
        Copy-Item $latest.FullName $Target -Force
    }
    return $true
}

# === 2. Парсинг + detect конфликтного состояния ===
# PreserveWhitespace=true критично: без него XmlDocument теряет все отступы
# и комментарии. С ним мы можем редактировать только нужный участок.
function Read-Logcfg([string]$Path) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.PreserveWhitespace = $true
    $doc.Load($Path)
    return $doc
}

# local-name() XPath — независим от namespace prefix registration (выявленный
# flapping баг XmlNamespaceManager на PS 5.1: иногда //tl:log возвращает null
# даже когда `<log>` физически есть в файле). local-name() стабилен 100%.
function Find-AllPlans([System.Xml.XmlDocument]$Doc) {
    return $Doc.SelectNodes("//*[local-name()='plan']")
}
function Find-Log([System.Xml.XmlDocument]$Doc) {
    return $Doc.SelectSingleNode("//*[local-name()='log']")
}
function Has-InnerEvent([System.Xml.XmlNode]$PlanNode) {
    return ($PlanNode.SelectSingleNode("*[local-name()='event']") -ne $null)
}

$xml = Read-Logcfg $LogcfgPath

$allPlans = Find-AllPlans $xml
$planCount = if ($allPlans) { $allPlans.Count } else { 0 }
Write-Host "  Найдено <plan> элементов: $planCount" -ForegroundColor Cyan

# Определяем — есть ли уже правильный <plan> (с вложенным <event>).
$validPlanExists = $false
foreach ($p in $allPlans) {
    if (Has-InnerEvent $p) {
        $validPlanExists = $true
        break
    }
}
Write-Host "  Уже есть правильный <plan> с <event>: $validPlanExists" -ForegroundColor Cyan

# Детектим chaos: > 1 plan, или есть только пустые <plan/>.
$needsRestore = $Restore -or ($planCount -gt 1) -or ($planCount -ge 1 -and -not $validPlanExists)

if ($needsRestore) {
    Write-Host "Detected chaos в logcfg.xml — будет clean restore + patch" -ForegroundColor Yellow
    if ($planCount -gt 1) { Write-Host "  причина: $planCount <plan> элементов (должен быть 1)" }
    if ($planCount -ge 1 -and -not $validPlanExists) {
        Write-Host "  причина: <plan> без вложенного <event> (пустой = бесполезный)"
    }
    if ($Restore) { Write-Host "  причина: явный -Restore флаг" }

    if (-not (Restore-FromBackup $LogcfgPath)) {
        Write-Error "Не могу восстановить — backup'а нет. Поправь файл вручную."
        exit 6
    }
    # Перечитываем после restore
    $xml = Read-Logcfg $LogcfgPath
    $allPlans = Find-AllPlans $xml
    $planCount = if ($allPlans) { $allPlans.Count } else { 0 }
    Write-Host "  После restore <plan> элементов: $planCount" -ForegroundColor Cyan

    $validPlanExists = $false
    foreach ($p in $allPlans) {
        if (Has-InnerEvent $p) { $validPlanExists = $true; break }
    }
}

if ($validPlanExists) {
    Write-Host "<plan> с вложенным <event> уже есть — изменений не требуется (idempotent)" -ForegroundColor Green
    exit 0
}

# Находим первый <log> — туда положим <plan>.
$logNode = Find-Log $xml
Write-Host "  <log> найден: $($logNode -ne $null)" -ForegroundColor Cyan
if (-not $logNode) {
    Write-Error "<log> элемент не найден в logcfg.xml — структура неожиданная"
    exit 2
}

# === 3. Создаём правильный <plan><event>DBMSSQL duration>$DurationThreshold</event></plan> ===
# Структура (per ИТС):
#   <plan>
#       <event>
#           <eq property="name" value="DBMSSQL"/>
#           <gt property="duration" value="$DurationThreshold"/>
#       </event>
#   </plan>
$planElement = $xml.CreateElement("plan", $NS)

$eventElement = $xml.CreateElement("event", $NS)

$eqElement = $xml.CreateElement("eq", $NS)
$eqElement.SetAttribute("property", "name")
$eqElement.SetAttribute("value", "DBMSSQL")
$eventElement.AppendChild($xml.CreateWhitespace("`n                ")) | Out-Null
$eventElement.AppendChild($eqElement) | Out-Null

$gtElement = $xml.CreateElement("gt", $NS)
$gtElement.SetAttribute("property", "duration")
$gtElement.SetAttribute("value", "$DurationThreshold")
$eventElement.AppendChild($xml.CreateWhitespace("`n                ")) | Out-Null
$eventElement.AppendChild($gtElement) | Out-Null
$eventElement.AppendChild($xml.CreateWhitespace("`n            ")) | Out-Null

$planElement.AppendChild($xml.CreateWhitespace("`n            ")) | Out-Null
$planElement.AppendChild($eventElement) | Out-Null
$planElement.AppendChild($xml.CreateWhitespace("`n        ")) | Out-Null

# Вставляем <plan> в <log> с leading whitespace (8 spaces — sibling от <event>).
$logNode.AppendChild($xml.CreateWhitespace("`n        ")) | Out-Null
$logNode.AppendChild($planElement) | Out-Null
$logNode.AppendChild($xml.CreateWhitespace("`n    ")) | Out-Null

Write-Host "Создан <plan> с <event>DBMSSQL duration>$DurationThreshold ($([math]::Round($DurationThreshold*10)) мс)</event>" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host ""
    Write-Host "=== DRY RUN — изменения НЕ применены ===" -ForegroundColor Yellow
    Write-Host "Финальный фрагмент <log>:"
    Write-Host $logNode.OuterXml.Substring([Math]::Max(0, $logNode.OuterXml.Length - 800)) -ForegroundColor Gray
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
