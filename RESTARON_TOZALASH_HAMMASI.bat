@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - HAMMASINI Tozalash (Noldan boshlash)
color 0C

REM  BUTUN ma'lumotlar bazasini o'chiradi va noldan yaratadi.
REM  Zaxira nusxa avval backend\zaxira\ ga saqlanadi.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  XATO: Administrator huquqi kerak.
    echo  O'ng tugma -^> "Run as administrator".
    pause
    exit /b 1
)

cd /d "%~dp0"
set "PY=%~dp0backend\.venv\Scripts\python.exe"

echo.
echo  ############################################################
echo  #                                                          #
echo  #   DIQQAT! HAMMA MA'LUMOT O'CHIRILADI!                    #
echo  #                                                          #
echo  ############################################################
echo.
echo    O'CHIRILADI:
echo      - menyu (barcha taomlar va kategoriyalar)
echo      - stollar va ularning QR kodlari
echo      - xodimlar va parollar
echo      - buyurtmalar, cheklar arxivi, qarzlar, hisobotlar
echo      - printer va restoran sozlamalari
echo.
echo    MUHIM: stollarning QR kodlari YANGIDAN yaratiladi.
echo    Ya'ni stollarda turgan eski chop etilgan QR kodlar
echo    ISHLAMAY QOLADI - ularni qayta chop etishingiz kerak.
echo.
echo    Keyin admin logini: maqsad / 01020307m
echo.
echo    Zaxira nusxa olinadi: backend\zaxira\
echo  ============================================================
echo.
set "OK="
set /p OK="  Rostdan hammasini o'chirasizmi? Tasdiq uchun TOZALA deb yozing: "
if /i not "!OK!"=="TOZALA" (
    echo.
    echo  Bekor qilindi. Hech narsa o'chirilmadi.
    pause
    exit /b 0
)

if not exist "!PY!" (
    echo.
    echo  XATO: Python topilmadi: !PY!
    echo  Avval 1_BIRINCHI_ORNATISH.bat ni ishga tushiring.
    pause
    exit /b 1
)

echo.
echo  [1/3] Server to'xtatilmoqda...
schtasks /End /TN "RestAron Server" >nul 2>&1
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr PID') do (
    taskkill /F /PID %%p >nul 2>&1
)
taskkill /F /IM cloudflared.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul

echo  [2/3] Ma'lumotlar bazasi o'chirilmoqda...
pushd "%~dp0backend"
"!PY!" tozalash.py hammasi
set "RC=!ERRORLEVEL!"
popd
if not "!RC!"=="0" (
    echo.
    echo  XATO: Tozalash bajarilmadi.
    pause
    exit /b 1
)

echo  [3/3] Server qayta ishga tushirilmoqda...
schtasks /Run /TN "RestAron Server" >nul 2>&1
if errorlevel 1 (
    echo  Eslatma: xizmat topilmadi. 2_SERVERNI_ORNATISH.bat ni
    echo  administrator nomidan ishga tushiring.
    echo.
    pause
    exit /b 0
)

echo.
echo  Baza qaytadan yaratilmoqda, kuting...
timeout /t 15 /nobreak >nul
set "HEALTH="
for /f "delims=" %%r in ('powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 5).StatusCode}catch{0}"') do set "HEALTH=%%r"
if "!HEALTH!"=="200" (
    echo  Server tayyor: http://localhost:8000
) else (
    echo  Server hali javob bermayapti. 30 soniyadan keyin
    echo  http://localhost:8000 ni brauzerda ochib ko'ring.
)

echo.
echo  ============================================================
echo    TUGADI - tizim butunlay yangi holatda.
echo    Admin: maqsad / 01020307m
echo    Eslatma: stollarning QR kodlarini qayta chop eting.
echo  ============================================================
echo.
pause
