@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo RestAron serverini to'xtatish va avtomatik ishga tushishni bekor qilish.
echo Faqat shu loyihaning jarayonlari yopiladi. Baza va buyurtmalar saqlanadi.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_autostart.ps1" -Remove
set "result=%errorlevel%"
pause
exit /b %result%
