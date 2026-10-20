@echo off
call "%~dp0Install.cmd" --agents-only %*
exit /b %ERRORLEVEL%
