@echo off
REM Запуск Tauri dev с автоматической активацией MSVC окружения.
REM Использование: двойной клик или из любого терминала: scripts\tauri-dev.cmd

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 (
    echo [ERROR] vcvars64.bat failed. Check Visual Studio Build Tools installation.
    pause
    exit /b 1
)

cd /d "%~dp0..\frontend"
echo.
echo === Starting Tauri dev (first build takes 5-15 min) ===
echo.
npm run tauri dev
pause
