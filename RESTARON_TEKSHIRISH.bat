@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo RestAron - yangi kompyuterni tekshirish
if not exist "%~dp0tools\windows_diagnostics.ps1" goto missing
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_diagnostics.ps1"
set "result=%errorlevel%"
goto finish
:missing
echo XATO: tools\windows_diagnostics.ps1 topilmadi.
echo ZIP ichidagi BAT va tools papkasini RestAron papkasiga birga oching.
set "result=1"
:finish
echo.
if /i "%~1"=="--no-pause" exit /b %result%
pause
exit /b %result%
