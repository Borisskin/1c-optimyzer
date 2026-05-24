SET STATISTICS XML OFF;
SET SHOWPLAN_XML ON;
GO
SELECT TOP 100 T1.[_Description]
FROM dbo.[_Reference10] T1
WHERE T1.[_Code] NOT IN (SELECT T2.[_Code] FROM dbo.[_Reference10] T2 WHERE T2.[_Description] LIKE N'A%');
GO
