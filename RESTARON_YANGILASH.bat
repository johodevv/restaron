@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if /i "%~1"=="--check" goto check
if not exist "%~dp0tools\windows_update.ps1" goto missing
echo RestAron - GitHub dan xavfsiz yangilash
echo Mahalliy kod zaxiralanib, GitHub versiyasi bilan almashtiriladi.
echo Baza va ishchi sozlamalar GitHub dan olinmaydi.
echo Savdo tugagach bajaring. Yangilash vaqtida ulanish qisqa uziladi.
REM The entire block is parsed before launch, so replacing this BAT is safe.
(
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_update.ps1"
call set "result=%%errorlevel%%"
echo.
call echo Yakuniy kod: %%result%%. Yuqoridagi xabar va jurnalni tekshiring.
pause
call exit /b %%result%%
)
:check
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_update.ps1" -CheckOnly
exit /b %errorlevel%
:missing
echo XATO: tools\windows_update.ps1 topilmadi.
echo YANGILASH ZIP ichidagi BAT va tools papkasini birga RestAron ichiga oching.
pause
exit /b 1
