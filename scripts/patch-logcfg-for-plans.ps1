<#
.SYNOPSIS
    Включает регистрацию SQL execution plans (planSQLText) в технологическом
    журнале 1С.

.DESCRIPTION
    Правильная структура (по официальной документации 1С —
    kb.1ci.com 3.23.2.1, проверено на 1С 8.3.27.1859 + MSSQL):

        <config xmlns="http://v8.1c.ru/v8/tech-log">
            <log location="...">
                <event>...DBMSSQL...</event>     <!-- MSSQL queries -->
                <event>...DBPOSTGRS...</event>   <!-- PostgreSQL queries -->
                <property name="all"/>
                <property name="plansqltext"/>   <!-- внутри <log> -->
            </log>
            <plansql/>                            <!-- SIBLING <log> на уровне <config>! -->
        </config>

    КРИТИЧНОЕ открытие 2026-05-25: <plansql/> ОБЯЗАН быть на уровне <config>,
    а не внутри <log>. Если ставить внутрь <log> — платформа тихо его игнорирует
    и planSQLText не пишется (проверено восемью неудачными попытками).
    Атомарное property <property name="plansqltext"/> идёт внутрь <log> как
    обычная property — это безопаснее чем полагаться на <property name="all"/>.

    Sprint 8 Phase A discovery (2026-05-25): для PostgreSQL баз 1С пишет
    события под именем DBPOSTGRS, НЕ DBMSSQL. Это значит существующий
    фильтр на DBMSSQL ловит только MS SQL Server. Для PG-баз нужен
    отдельный <event> с DBPOSTGRS. Этот скрипт добавляет оба event'а
    если их ещё нет (idempotent).

    Idempotent patch:
      1. Backup logcfg.xml в logcfg.xml.backup.YYYYMMDD-HHMMSS
      2. Cleanup: удалить старые <plan>, <plansql>, <plansqltext> элементы
         (от предыдущих неудачных экспериментов на этой машине)
      3. Удалить дубликаты <property name='plansqltext'> внутри <log>
      4. Добавить <property name="plansqltext"/> внутрь <log>
      5. Добавить <plansql/> на уровне <config> как sibling <log>
      6. Save (UTF-8 без BOM, preserve whitespace)
      7. Restart 1C Server Agent (rphost перечитает logcfg)

    Self-elevation через UAC если запуск не от admin.

.PARAMETER LogcfgPath
    Путь к logcfg.xml. По умолчанию C:\Program Files\1cv8\conf\logcfg.xml.

.PARAMETER NoRestart
    Не перезапускать ragent — изменения активируются только после следующего
    рестарта вручную. Полезно если идёт работа в Конфигураторе.

.PARAMETER DryRun
    Показать что будет изменено, без записи и без рестарта.

.EXAMPLE
    .\scripts\patch-logcfg-for-plans.ps1
    Apply patch + restart ragent (UAC промпт появится автоматически).

.NOTES
    Sprint 7 Phase D — Plan Analyzer (auto-extract DBMSSQL.Plan из ТЖ).
    Проверено: 1С 8.3.27.1859 + MSSQL → planSQLText пишется в .log за секунды.
    См. docs/onboarding/enable-dbmssql-plans.md.
#>

param(
    [string]$LogcfgPath = "C:\Program Files\1cv8\conf\logcfg.xml",
    [switch]$NoRestart,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$NS = "http://v8.1c.ru/v8/tech-log"

# === Self-elevation через UAC ===
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
        Write-Error "UAC отклонён: $_"
        exit 5
    }
}

# === Проверка файла ===
if (-not (Test-Path $LogcfgPath)) {
    Write-Error "logcfg.xml не найден: $LogcfgPath"
    exit 1
}

Write-Host "logcfg.xml: $LogcfgPath" -ForegroundColor Cyan
$origSize = (Get-Item $LogcfgPath).Length
Write-Host "  исходный размер: $origSize байт"

# === Чтение XML с сохранением whitespace ===
$xml = New-Object System.Xml.XmlDocument
$xml.PreserveWhitespace = $true
$xml.Load($LogcfgPath)

$configNode = $xml.DocumentElement
$logNode = $xml.SelectSingleNode("//*[local-name()='log']")
if (-not $logNode) {
    Write-Error "<log> элемент не найден в logcfg.xml"
    exit 2
}
Write-Host "  <log location='$($logNode.GetAttribute('location'))'> найден"

# === Cleanup: удалить старые plan-related элементы где угодно в дереве ===
$oldEls = @($xml.SelectNodes("//*[local-name()='plan' or local-name()='plansql' or local-name()='plansqltext']"))
if ($oldEls.Count -gt 0) {
    Write-Host "  Удаляю старые plan-related элементы: $($oldEls.Count)" -ForegroundColor Yellow
    foreach ($el in $oldEls) { $el.ParentNode.RemoveChild($el) | Out-Null }
}

# === Cleanup: удалить дубликаты <property name='plansqltext'> внутри <log> ===
$oldProps = @($logNode.SelectNodes("*[local-name()='property' and @name='plansqltext']"))
if ($oldProps.Count -gt 0) {
    Write-Host "  Удаляю старые <property name='plansqltext'>: $($oldProps.Count)" -ForegroundColor Yellow
    foreach ($el in $oldProps) { $logNode.RemoveChild($el) | Out-Null }
}

# === Sprint 8 Phase A — добавить <event name="DBPOSTGRS"> если его ещё нет ===
# Для PostgreSQL баз 1С пишет события под этим именем, NOT DBMSSQL.
# Idempotent: если DBPOSTGRS event уже есть — не дублируем.
$existingDbpostgrs = $logNode.SelectNodes("*[local-name()='event']/*[local-name()='eq' and @property='name' and @value='DBPOSTGRS']")
if ($existingDbpostgrs.Count -eq 0) {
    # Берём порог duration с существующего DBMSSQL event если есть, иначе 10 (100 мс)
    $existingDbmssql = $logNode.SelectSingleNode("*[local-name()='event'][./*[local-name()='eq' and @property='name' and @value='DBMSSQL']]")
    $threshold = "10"
    if ($existingDbmssql) {
        $durNode = $existingDbmssql.SelectSingleNode("*[local-name()='gt' and @property='duration']")
        if ($durNode) { $threshold = $durNode.GetAttribute("value") }
    }

    $eventNode = $xml.CreateElement("event", $NS)
    $eqNode = $xml.CreateElement("eq", $NS)
    $eqNode.SetAttribute("property", "name")
    $eqNode.SetAttribute("value", "DBPOSTGRS")
    $gtNode = $xml.CreateElement("gt", $NS)
    $gtNode.SetAttribute("property", "duration")
    $gtNode.SetAttribute("value", $threshold)
    $eventNode.AppendChild($xml.CreateWhitespace("`n            ")) | Out-Null
    $eventNode.AppendChild($eqNode) | Out-Null
    $eventNode.AppendChild($xml.CreateWhitespace("`n            ")) | Out-Null
    $eventNode.AppendChild($gtNode) | Out-Null
    $eventNode.AppendChild($xml.CreateWhitespace("`n        ")) | Out-Null

    $logNode.AppendChild($xml.CreateWhitespace("`n        ")) | Out-Null
    $logNode.AppendChild($eventNode) | Out-Null
    Write-Host "  + <event name='DBPOSTGRS' duration>$threshold/> для PostgreSQL баз" -ForegroundColor Green
} else {
    Write-Host "  = <event name='DBPOSTGRS'> уже есть, пропускаю" -ForegroundColor Gray
}

# === Шаг 1: <property name="plansqltext"/> ВНУТРИ <log> ===
# Это явная декларация что поле planSQLText должно попасть в lines events.
# Безопаснее чем полагаться на <property name="all"/> (который теоретически
# включает всё, но на практике может не включать новые поля).
$prop = $xml.CreateElement("property", $NS)
$prop.SetAttribute("name", "plansqltext")
$logNode.AppendChild($xml.CreateWhitespace("`n        ")) | Out-Null
$logNode.AppendChild($prop) | Out-Null
$logNode.AppendChild($xml.CreateWhitespace("`n    ")) | Out-Null
Write-Host "  + <property name='plansqltext'/> внутрь <log>" -ForegroundColor Green

# === Шаг 2: <plansql/> на уровне <config> КАК SIBLING <log> ===
# КРИТИЧНО: <plansql/> ДОЛЖЕН быть child of <config>, не <log>!
# Это master-switch который включает сам механизм сбора планов. Если он
# не на уровне config — платформа тихо игнорирует.
$plansql = $xml.CreateElement("plansql", $NS)
$configNode.AppendChild($xml.CreateWhitespace("`n    ")) | Out-Null
$configNode.AppendChild($plansql) | Out-Null
$configNode.AppendChild($xml.CreateWhitespace("`n")) | Out-Null
Write-Host "  + <plansql/> в <config> как sibling <log>" -ForegroundColor Green

# === DryRun — показать diff и выйти ===
if ($DryRun) {
    Write-Host ""
    Write-Host "=== DRY RUN — изменения НЕ применены ===" -ForegroundColor Yellow
    Write-Host "Финальный <config> (последние 600 символов):"
    $outer = $configNode.OuterXml
    Write-Host $outer.Substring([Math]::Max(0, $outer.Length - 600)) -ForegroundColor Gray
    exit 0
}

# === Backup ===
$backup = "$LogcfgPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $LogcfgPath $backup -Force
Write-Host "  Backup: $backup" -ForegroundColor Cyan

# === Save (UTF-8 без BOM, без auto-indent) ===
$utf8 = New-Object System.Text.UTF8Encoding($false)
$settings = New-Object System.Xml.XmlWriterSettings
$settings.Indent = $false    # PreserveWhitespace уже хранит оригинальное форматирование
$settings.Encoding = $utf8
$settings.OmitXmlDeclaration = $false

$writer = [System.Xml.XmlWriter]::Create($LogcfgPath, $settings)
try { $xml.Save($writer) } finally { $writer.Close() }

$newSize = (Get-Item $LogcfgPath).Length
Write-Host "  Сохранено: $newSize байт (было $origSize, +$($newSize - $origSize))" -ForegroundColor Green

# === Restart 1C Server Agent ===
if ($NoRestart) {
    Write-Host ""
    Write-Host "Skip restart (-NoRestart). Чтобы активировать — перезапусти ragent вручную:" -ForegroundColor Yellow
    Write-Host "  Restart-Service '1C:Enterprise 8.3 Server Agent (x86-64)' -Force"
    exit 0
}

$serviceName = "1C:Enterprise 8.3 Server Agent (x86-64)"
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Warning "Сервис '$serviceName' не найден. Перезапусти 1С Server Agent вручную."
    exit 0
}

Write-Host ""
Write-Host "Перезапуск '$serviceName'..." -ForegroundColor Cyan
Write-Host "  ВНИМАНИЕ: открытые 1С-сессии будут разорваны!" -ForegroundColor Yellow
try {
    Restart-Service $service.Name -Force -ErrorAction Stop
    Start-Sleep -Seconds 3
    $st = (Get-Service -Name $serviceName).Status
    if ($st -eq "Running") {
        Write-Host "  Сервис работает (Status=$st)" -ForegroundColor Green
    } else {
        Write-Warning "После рестарта Status=$st — проверь руками"
        exit 3
    }
} catch {
    Write-Error "Ошибка рестарта: $_"
    Write-Host "Backup сохранён в: $backup" -ForegroundColor Yellow
    exit 4
}

Write-Host ""
Write-Host "=== Готово ===" -ForegroundColor Green
Write-Host "В следующих DBMSSQL событиях ТЖ появится поле planSQLText."
Write-Host "Проверить — выполнить любой длительный SQL запрос и через 5-10 секунд"
Write-Host "посмотреть свежий .log файл в $($logNode.GetAttribute('location'))"
Write-Host ""
Write-Host "Быстрая проверка:"
Write-Host "  Get-ChildItem '$($logNode.GetAttribute('location'))' -Recurse -Filter '*.log' |"
Write-Host "      Where-Object {`$_.LastWriteTime -gt (Get-Date).AddMinutes(-5)} |"
Write-Host "      Select-String -Pattern 'planSQLText' -List | Select-Object -First 3"
