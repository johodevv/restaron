@echo off
setlocal DisableDelayedExpansion
call "%~dp0RESTARON_AVTO_SERVER.bat" %*
exit /b %errorlevel%
