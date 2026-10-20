@echo off
setlocal
title ZITTOMARK Installer
if /i "%~1"=="--plan" goto plan
if /i "%~1"=="--check-only" goto plan
set "OVS_BOOTSTRAP_APPROVED="
for %%A in (%*) do if /i "%%~A"=="--yes" set "OVS_BOOTSTRAP_APPROVED=1"
echo ZITTOMARK - Local Voice Studio
echo.
echo This installs private Python, English/Tamil speech, creative English and AI-tool support.
echo It downloads verified files from Astral/GitHub, PyPI, PyTorch and Hugging Face.
echo Full setup needs an NVIDIA GPU, internet and about 40 GB of free space.
echo No administrator access, Git installation or PowerShell policy changes are needed.
echo Use --basic to skip creative English, or --agents-only for just the AI-tool adapter.
echo Review SECURITY.md before installing third-party code.
if defined OVS_BOOTSTRAP_APPROVED goto approved
"%SystemRoot%\System32\choice.exe" /c YN /n /m "Continue with downloads and installation? [Y/N] "
if errorlevel 2 exit /b 0
set "OVS_BOOTSTRAP_APPROVED=1"
:approved
for /f "tokens=1 delims==" %%V in ('set UV_ 2^>nul') do set "%%V="
set "PYTHONHOME="
set "PYTHONPATH="
if defined OVS_RUNTIME_ROOT (set "OVS_INSTALL_RUNTIME=%OVS_RUNTIME_ROOT%") else (set "OVS_INSTALL_RUNTIME=%LOCALAPPDATA%\Zittomark\runtime")
if not "%OVS_INSTALL_RUNTIME:~1,2%"==":\" goto invalid_runtime
set "OVS_UV=%OVS_INSTALL_RUNTIME%\bootstrap\uv-0.11.7\uv.exe"
set "OVS_ARCHIVE=%OVS_INSTALL_RUNTIME%\bootstrap\uv-0.11.7.zip"
set "UV_CACHE_DIR=%OVS_INSTALL_RUNTIME%\uv-cache"
set "UV_PYTHON_INSTALL_DIR=%OVS_INSTALL_RUNTIME%\python"
if not exist "%OVS_INSTALL_RUNTIME%\bootstrap\uv-0.11.7" mkdir "%OVS_INSTALL_RUNTIME%\bootstrap\uv-0.11.7"
if not exist "%OVS_INSTALL_RUNTIME%\bootstrap\uv-0.11.7" goto failed
if exist "%OVS_ARCHIVE%" goto verify_archive
:download
echo Downloading the pinned installer helper...
"%SystemRoot%\System32\curl.exe" --fail --location --proto "=https" --proto-redir "=https" --tlsv1.2 --retry 2 --output "%OVS_ARCHIVE%.partial" "https://github.com/astral-sh/uv/releases/download/0.11.7/uv-x86_64-pc-windows-msvc.zip"
if errorlevel 1 goto failed
"%SystemRoot%\System32\certutil.exe" -hashfile "%OVS_ARCHIVE%.partial" SHA256 | "%SystemRoot%\System32\findstr.exe" /i /x "fe0c7815acf4fc45f8a5eff58ed3cf7ae2e15c3cf1dceadbd10c816ec1690cc1" >nul
if errorlevel 1 goto checksum_failed
move /y "%OVS_ARCHIVE%.partial" "%OVS_ARCHIVE%" >nul
if errorlevel 1 goto failed
:verify_archive
"%SystemRoot%\System32\certutil.exe" -hashfile "%OVS_ARCHIVE%" SHA256 | "%SystemRoot%\System32\findstr.exe" /i /x "fe0c7815acf4fc45f8a5eff58ed3cf7ae2e15c3cf1dceadbd10c816ec1690cc1" >nul
if errorlevel 1 goto download
"%SystemRoot%\System32\tar.exe" -xf "%OVS_ARCHIVE%" -C "%OVS_INSTALL_RUNTIME%\bootstrap\uv-0.11.7"
if errorlevel 1 goto failed
"%SystemRoot%\System32\certutil.exe" -hashfile "%OVS_UV%" SHA256 | "%SystemRoot%\System32\findstr.exe" /i /x "831730243cf7bbd496ff96353dcdba6f5d4dcbd22576af398130381ab44ac160" >nul
if errorlevel 1 goto checksum_failed
echo Installing private Python 3.11.15. Existing Python installations are left unchanged.
"%OVS_UV%" --no-config python install 3.11.15 --no-bin --no-registry --no-progress
if errorlevel 1 goto failed
"%OVS_UV%" --no-config run --no-project --managed-python --python 3.11.15 --no-python-downloads "%~dp0installer.py" %*
set "OVS_INSTALL_EXIT=%ERRORLEVEL%"
if not "%OVS_INSTALL_EXIT%"=="0" goto failed
echo.
echo Finished. Open Start-Local-Voice.cmd. AI connection instructions are in docs\AGENT_INTEGRATION.md.
if defined OVS_NO_PAUSE exit /b 0
pause
exit /b 0
:checksum_failed
echo Integrity check failed. The downloaded file will not be executed.
goto failed
:invalid_runtime
echo OVS_RUNTIME_ROOT must be an absolute local path, such as C:\VoiceRuntime. Network/relative paths are not supported.
:failed
echo Installation could not finish. Review the message above and data\logs\install.log, then retry.
if defined OVS_NO_PAUSE exit /b 1
pause
exit /b 1
:plan
echo Full install: private Python 3.11.15, pinned speech and MCP packages, verified models.
echo Requires Windows 10/11 x64, NVIDIA driver, internet, about 40 GB free.
echo No Python, Git, admin rights, PowerShell policy changes or public server are required.
echo Choices: --basic or --agents-only. --yes accepts the displayed install plan.
echo --plan does not download or change anything.
exit /b 0
