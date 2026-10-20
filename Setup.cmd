@echo off
call "%~dp0Install.cmd" --basic %*
exit /b %ERRORLEVEL%
