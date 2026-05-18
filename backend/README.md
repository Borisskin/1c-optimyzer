# optimyzer-backend

Python sidecar для 1C-Optimyzer Module 1. JSON-RPC over stdio.

## Установка (dev)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Запуск

```powershell
python -m optimyzer_backend
```

Сидекар читает JSON-RPC 2.0 запросы из stdin, пишет ответы в stdout. Логи — в stderr.

## Сборка single-file exe

```powershell
pip install -e ".[build]"
pyinstaller --onefile --name optimyzer-backend src/optimyzer_backend/__main__.py
```
