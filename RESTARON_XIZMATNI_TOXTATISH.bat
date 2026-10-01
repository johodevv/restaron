@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Xizmatni To'xtatish
color 0C

REM  Avtomatik ishga tushadigan RestAron xizmatini to'xtatadi.
REM  Ma'lumotlar bazasi (backend\restaron.db) O'CHIRILMAYDI.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  XATO: Administrator huquqi kerak.
    echo  O'ng tugma -^> "Run as administrator".
    pause
    exit /b 1
)

cd /d "%~dp0"

echo.
echo  RestAron xizmati to'xtatilmoqda...
echo.

REM Rejalashtirilgan vazifani to'xtatish
schtasks /End /TN "RestAron Server" >nul 2>&1
schtasks /Delete /TN "RestAron Server" /F >nul 2>&1

REM Jarayonlarni yopish
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq RestAron*" >nul 2>&1
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr PID') do (
    taskkill /F /PID %%p >nul 2>&1
)
taskkill /F /IM cloudflared.exe /T >nul 2>&1

echo  Xizmat to'xtatildi va avtomatik ishga tushish o'chirildi.
echo.
echo  Ma'lumotlar saqlanib qoldi: backend\restaron.db
echo.
echo  Qayta yoqish uchun: 2_SERVERNI_ORNATISH.bat
echo.
pause
