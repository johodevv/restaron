@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Buyurtmalarni Tozalash
color 0E

REM  Buyurtmalar, cheklar arxivi, qarzlar va hisobotlarni o'chiradi.
REM  Menyu, stollar, QR kodlar, xodimlar va sozlamalar SAQLANADI.

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
echo  ============================================================
echo    RestAron - BUYURTMA / CHEK / QARZLARNI TOZALASH
echo  ============================================================
echo.
echo    O'CHIRILADI:  buyurtmalar, cheklar arxivi, qarzlar,
echo                  smena hisobotlari, bildirishnomalar
echo.
echo    SAQLANADI:    menyu, stollar, QR kodlar, xodimlar, sozlamalar
echo.
echo    Zaxira nusxa avtomatik olinadi: backend\zaxira\
echo  ============================================================
echo.
set "OK="
set /p OK="  Davom etasizmi? (ha / yoq): "
if /i not "!OK!"=="ha" (
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

echo  [2/3] Ma'lumotlar tozalanmoqda...
pushd "%~dp0backend"
"!PY!" tozalash.py buyurtmalar
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
) else (
    echo  Server ishga tushirildi.
)

echo.
echo  ============================================================
echo    TUGADI - endi noldan ish boshlashingiz mumkin.
echo  ============================================================
echo.
pause
