SET STATISTICS XML OFF;
SET SHOWPLAN_XML ON;
GO
SELECT TOP 50 T1.[_Description]
FROM dbo.[_Reference10] T1
WHERE T1.[_Description] LIKE N'%test%';
GO
