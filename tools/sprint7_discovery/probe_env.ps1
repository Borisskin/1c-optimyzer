param()
$ErrorActionPreference = 'Continue'

Write-Host "=== TJ logs total ===" -ForegroundColor Cyan
$logs = Get-ChildItem 'D:\1C-Optimyzer\logs' -Recurse -Filter '*.log'
$totalMB = [math]::Round(($logs | Measure-Object Length -Sum).Sum / 1MB, 2)
Write-Host "Files: $($logs.Count)  Total MB: $totalMB"

Write-Host "`n=== Per-process folders ===" -ForegroundColor Cyan
Get-ChildItem 'D:\1C-Optimyzer\logs' -Directory | ForEach-Object {
    $folder = $_
    $files = Get-ChildItem $folder.FullName -File
    $sumMB = [math]::Round(($files | Measure-Object Length -Sum).Sum / 1MB, 2)
    [PSCustomObject]@{ Folder = $folder.Name; Files = $files.Count; SizeMB = $sumMB }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

Write-Host "`n=== SCHEME XML folder ===" -ForegroundColor Cyan
if (Test-Path 'C:\BUFFER\SCHEME') {
    $scheme = Get-ChildItem 'C:\BUFFER\SCHEME' -Recurse -File
    $schemeMB = [math]::Round(($scheme | Measure-Object Length -Sum).Sum / 1MB, 2)
    Write-Host "Files: $($scheme.Count)  Total MB: $schemeMB"
} else {
    Write-Host "MISSING"
}

Write-Host "`n=== research/PerformanceStudio test plans ===" -ForegroundColor Cyan
$ps = Get-ChildItem 'D:\1C-Optimyzer\research\PerformanceStudio' -Recurse -Filter '*.sqlplan' -ErrorAction SilentlyContinue
Write-Host "PerformanceStudio .sqlplan files: $($ps.Count)"

$hp = Get-ChildItem 'D:\1C-Optimyzer\research\html-query-plan' -Recurse -Filter '*.sqlplan' -ErrorAction SilentlyContinue
Write-Host "html-query-plan .sqlplan files: $($hp.Count)"
