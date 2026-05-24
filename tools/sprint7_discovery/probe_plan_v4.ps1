$outDir = 'D:\1C-Optimyzer\tools\sprint7_discovery\sqlplans'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

function Capture-Plan {
    param([string]$Name, [string]$Sql)
    $tmpFile = Join-Path $outDir "$Name.sql"
    $outFile = Join-Path $outDir "$Name.sqlplan"
    $rawFile = Join-Path $outDir "$Name.raw.txt"
    $full = @"
SET SHOWPLAN_XML ON;
GO
$Sql
GO
"@
    Set-Content -Path $tmpFile -Value $full -Encoding UTF8
    sqlcmd -S localhost -E -d Test1CProf -i $tmpFile -o $rawFile -y 0 -h -1 -m -1 | Out-Null
    if (-not (Test-Path $rawFile)) {
        Write-Host "$Name : NO OUTPUT"
        return
    }
    $raw = Get-Content $rawFile -Raw
    $xmlMatch = [regex]::Match($raw, '<ShowPlanXML[\s\S]*</ShowPlanXML>')
    if ($xmlMatch.Success) {
        Set-Content -Path $outFile -Value $xmlMatch.Value -Encoding UTF8
        $kb = [math]::Round((Get-Item $outFile).Length/1KB, 2)
        Write-Host ("{0,-30}  {1,6} KB  XML extracted" -f $Name, $kb)
    } else {
        $kb = [math]::Round((Get-Item $rawFile).Length/1KB, 2)
        Write-Host ("{0,-30}  {1,6} KB  RAW only (preview):" -f $Name, $kb)
        ($raw -split "`n" | Select-Object -First 5) | ForEach-Object { "    $_" } | Write-Host
    }
}

Capture-Plan -Name 'test01_sys_tables' -Sql 'SELECT TOP 100 t.[name], t.[create_date] FROM sys.[tables] t INNER JOIN sys.[schemas] s ON t.[schema_id] = s.[schema_id] WHERE s.[name] = N''dbo'' ORDER BY t.[create_date] DESC;'

Capture-Plan -Name 'test02_like_wildcard' -Sql 'SELECT TOP 50 T1.[_Description] FROM dbo.[_Reference10] T1 WHERE T1.[_Description] LIKE N''%test%'';'

Capture-Plan -Name 'test03_join_group_by' -Sql 'SELECT TOP 50 COUNT(*) AS cnt, t.[_Description] FROM dbo.[_Reference10] t INNER JOIN dbo.[_Reference10] t2 ON t.[_Code] = t2.[_Code] GROUP BY t.[_Description];'

Capture-Plan -Name 'test04_not_in_subquery' -Sql 'SELECT TOP 100 T1.[_Description] FROM dbo.[_Reference10] T1 WHERE T1.[_Code] NOT IN (SELECT T2.[_Code] FROM dbo.[_Reference10] T2 WHERE T2.[_Description] LIKE N''A%'');'

Capture-Plan -Name 'test05_function_on_column' -Sql 'SELECT TOP 100 T1.[_Description] FROM dbo.[_Reference10] T1 WHERE UPPER(T1.[_Code]) = N''ABC'';'

Write-Host ""
Write-Host "Total .sqlplan files generated:"
Get-ChildItem $outDir -Filter '*.sqlplan' | Format-Table Name, @{N='KB'; E={[math]::Round($_.Length/1KB,2)}} -AutoSize
