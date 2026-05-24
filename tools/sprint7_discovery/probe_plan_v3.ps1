$outDir = 'D:\1C-Optimyzer\tools\sprint7_discovery\sqlplans'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

# Test 02 — single statement to file
$sql02 = @"
SET STATISTICS XML OFF;
SET SHOWPLAN_XML ON;
GO
SELECT TOP 50 T1.[_Description]
FROM dbo.[_Reference10] T1
WHERE T1.[_Description] LIKE N'%test%';
GO
"@

$tmpFile = Join-Path $outDir 'test02_query.sql'
Set-Content -Path $tmpFile -Value $sql02 -Encoding UTF8

$out02 = Join-Path $outDir 'test02_plan.txt'
sqlcmd -S localhost -E -d Test1CProf -i $tmpFile -o $out02 -W -y 65535
$bytes = (Get-Item $out02).Length
Write-Host "test02 output: $bytes bytes"
Get-Content $out02 -TotalCount 3

# Test 03 — JOIN with group by
$sql03 = @"
SET STATISTICS XML OFF;
SET SHOWPLAN_XML ON;
GO
SELECT TOP 50 COUNT(*) AS cnt, t.[_Description]
FROM dbo.[_Reference10] t
INNER JOIN dbo.[_Reference10] t2 ON t.[_Code] = t2.[_Code]
GROUP BY t.[_Description];
GO
"@
$tmpFile3 = Join-Path $outDir 'test03_query.sql'
Set-Content -Path $tmpFile3 -Value $sql03 -Encoding UTF8

$out03 = Join-Path $outDir 'test03_plan.txt'
sqlcmd -S localhost -E -d Test1CProf -i $tmpFile3 -o $out03 -W -y 65535
$bytes3 = (Get-Item $out03).Length
Write-Host "test03 output: $bytes3 bytes"
Get-Content $out03 -TotalCount 3

# Test 04 — NOT IN
$sql04 = @"
SET STATISTICS XML OFF;
SET SHOWPLAN_XML ON;
GO
SELECT TOP 100 T1.[_Description]
FROM dbo.[_Reference10] T1
WHERE T1.[_Code] NOT IN (SELECT T2.[_Code] FROM dbo.[_Reference10] T2 WHERE T2.[_Description] LIKE N'A%');
GO
"@
$tmpFile4 = Join-Path $outDir 'test04_query.sql'
Set-Content -Path $tmpFile4 -Value $sql04 -Encoding UTF8

$out04 = Join-Path $outDir 'test04_plan.txt'
sqlcmd -S localhost -E -d Test1CProf -i $tmpFile4 -o $out04 -W -y 65535
$bytes4 = (Get-Item $out04).Length
Write-Host "test04 output: $bytes4 bytes"
Get-Content $out04 -TotalCount 3
