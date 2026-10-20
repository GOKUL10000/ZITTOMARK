@echo off
call "%~dp0Install.cmd" --creative %*
exit /b %ERRORLEVEL%
