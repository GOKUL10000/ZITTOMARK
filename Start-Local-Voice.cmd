@echo off
setlocal
if defined OVS_RUNTIME_ROOT (set "OVS_LAUNCH_RUNTIME=%OVS_RUNTIME_ROOT%") else (set "OVS_LAUNCH_RUNTIME=%LOCALAPPDATA%\Zittomark\runtime")
if not exist "%OVS_LAUNCH_RUNTIME%\.venv\Scripts\python.exe" (
  echo Run Install.cmd first. The private speech runtime is not installed.
  pause
  exit /b 1
)
"%OVS_LAUNCH_RUNTIME%\.venv\Scripts\python.exe" "%~dp0launcher.py" start %*
if errorlevel 1 pause
