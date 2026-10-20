@echo off
setlocal
if defined OVS_RUNTIME_ROOT (set "OVS_LAUNCH_RUNTIME=%OVS_RUNTIME_ROOT%") else (set "OVS_LAUNCH_RUNTIME=%LOCALAPPDATA%\Zittomark\runtime")
if not exist "%OVS_LAUNCH_RUNTIME%\.venv\Scripts\python.exe" (
  echo No private speech runtime found. No process was stopped.
  exit /b 0
)
"%OVS_LAUNCH_RUNTIME%\.venv\Scripts\python.exe" "%~dp0launcher.py" stop
if errorlevel 1 pause
