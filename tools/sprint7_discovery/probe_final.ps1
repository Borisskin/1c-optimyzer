Write-Host "=== Node / NPM ===" -ForegroundColor Cyan
$nodeOK = $false
try { node -v 2>&1 | ForEach-Object { Write-Host "node: $_"; $nodeOK = $true } } catch { Write-Host "node: NOT FOUND" }
try { npm -v 2>&1 | ForEach-Object { Write-Host "npm: $_" } } catch { Write-Host "npm: NOT FOUND" }

Write-Host "`n=== .NET SDK / Runtime ===" -ForegroundColor Cyan
dotnet --list-sdks 2>&1 | Select-Object -First 5

Write-Host "`n=== SSMS 21 ===" -ForegroundColor Cyan
$ssms = Get-ChildItem 'C:\Program Files\Microsoft SQL Server Management Studio 21' -Recurse -Filter 'Ssms.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ssms) { Write-Host "SSMS: $($ssms.FullName)" } else { Write-Host "SSMS Ssms.exe NOT FOUND" }

Write-Host "`n=== Java versions ===" -ForegroundColor Cyan
java -version 2>&1 | Select-Object -First 3
Get-ChildItem 'C:\Program Files\Axiom' -Directory -ErrorAction SilentlyContinue | Select-Object Name
Get-ChildItem 'C:\Program Files\Java' -Directory -ErrorAction SilentlyContinue | Select-Object Name
Get-ChildItem 'D:\1C-Optimyzer\frontend\src-tauri\binaries' -Recurse -Filter 'java.exe' -ErrorAction SilentlyContinue | Select-Object FullName -First 3

Write-Host "`n=== research/ folder breakdown ===" -ForegroundColor Cyan
Get-ChildItem 'D:\1C-Optimyzer\research' -Directory | ForEach-Object {
    $sumMB = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 2)
    [PSCustomObject]@{ Name = $_.Name; SizeMB = $sumMB }
} | Sort-Object SizeMB -Descending | Format-Table -AutoSize

Write-Host "`n=== .claude/skills/ first 5 SKILL.md ===" -ForegroundColor Cyan
Get-ChildItem 'D:\1C-Optimyzer\.claude\skills' -Directory | Select-Object -First 5 | ForEach-Object {
    $skill = $_
    $md = Get-ChildItem $skill.FullName -Recurse -Filter '*.md' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($md) {
        Write-Host "--- $($skill.Name) ---"
        Get-Content $md.FullName -TotalCount 8 | ForEach-Object { "  $_" } | Write-Host
    }
}

Write-Host "`n=== .claude/skills/ count by namespace ===" -ForegroundColor Cyan
Get-ChildItem 'D:\1C-Optimyzer\.claude\skills' -Directory | Group-Object { ($_.Name -split '-')[0] } | Select-Object Count, Name | Sort-Object Count -Descending | Format-Table -AutoSize

Write-Host "`n=== AI explainer setup ===" -ForegroundColor Cyan
Get-ChildItem 'D:\1C-Optimyzer\server\services' -Filter '*.py' -ErrorAction SilentlyContinue | Select-Object Name | Format-Table -AutoSize

Write-Host "`n=== pev2 / Postgres plan visualizer ===" -ForegroundColor Cyan
Get-ChildItem 'D:\1C-Optimyzer\research' -Filter 'pev2*' -Recurse -Directory -ErrorAction SilentlyContinue | Select-Object FullName

Write-Host "`n=== Docker ===" -ForegroundColor Cyan
try { docker --version 2>&1 } catch { Write-Host "Docker: NOT FOUND" }
