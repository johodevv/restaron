@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if /i "%~1"=="--check" goto check
echo RestAron va https://dunyochoyxona.uz avtomatik serverini o'rnatish
echo Windows ruxsat oynasi chiqsa, Ha / Yes ni bosing.
echo O'rnatish vaqtida server qisqa muddat qayta ishga tushadi.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_autostart.ps1"
set "result=%errorlevel%"
echo.
if not "%result%"=="0" echo Natija kodi: %result%. Yuqoridagi xabarni tekshiring.
pause
exit /b %result%
:check
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_autostart.ps1" -CheckOnly
exit /b %errorlevel%
