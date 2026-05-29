@echo off
REM 1C-Optimyzer dev launcher.
REM Lifecycle is tied to this window: launch -> AI server (:8001) + app run together;
REM close the app window -> the server is stopped too. Nothing is left running.
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

REM 1) AI server on :8001 - reuse if healthy, kill if wedged, start if down.
REM    Without this the AI screens (logcfg builder, plan/query explain) just hang.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-server.ps1"

REM 2) Clean orphaned backend-sidecar python from previous sessions.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\kill-zombie-python.ps1" -Apply

REM 3) Run the app. `call` is REQUIRED so this script resumes after the app window
REM    is closed (npm is a .cmd; without `call` control would not return here).
cd /d "%~dp0frontend"
call npm run tauri dev

REM 4) App window closed -> stop the AI server so nothing keeps running in background.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-server.ps1"
