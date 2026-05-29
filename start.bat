@echo off
REM 1C-Optimyzer dev launcher - brings up the whole local stack in one command.
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

REM 1) AI server on :8001 - reuse if healthy, kill if wedged, start if down.
REM    Without this the AI screens (logcfg builder, plan/query explain) just hang.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-server.ps1"

REM 2) Clean orphaned backend-sidecar python from previous sessions.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\kill-zombie-python.ps1" -Apply

REM 3) Frontend: Tauri dev (webview + backend sidecar for DuckDB/parsing).
cd /d "%~dp0frontend"
npm run tauri dev
