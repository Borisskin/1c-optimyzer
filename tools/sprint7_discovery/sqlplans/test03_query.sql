SET STATISTICS XML OFF;
SET SHOWPLAN_XML ON;
GO
SELECT TOP 50 COUNT(*) AS cnt, t.[_Description]
FROM dbo.[_Reference10] t
INNER JOIN dbo.[_Reference10] t2 ON t.[_Code] = t2.[_Code]
GROUP BY t.[_Description];
GO
