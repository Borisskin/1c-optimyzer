SET STATISTICS XML ON;
GO
SELECT TOP 100 t.[name], t.[create_date]
FROM sys.[tables] t
INNER JOIN sys.[schemas] s ON t.[schema_id] = s.[schema_id]
WHERE s.[name] = N'dbo'
ORDER BY t.[create_date] DESC;
GO
SET STATISTICS XML OFF;
GO
