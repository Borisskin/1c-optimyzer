@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\kill-zombie-python.ps1" -Apply

:: Запускаем AI-сервер в отдельном окне (порт 8001)
start "Optimyzer AI Server" cmd /k "cd /d %~dp0server && .venv\Scripts\uvicorn.exe api.main:app --port 8001"

cd /d "%~dp0frontend"
npm run tauri dev
