@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Boshqa kompyuterga nusxa olish
color 0B

REM  Boshqa kompyuterga ko'chirish uchun TOZA ZIP tayyorlaydi.
REM  Administrator huquqi kerak emas.

cd /d "%~dp0"
set "PY=%~dp0backend\.venv\Scripts\python.exe"

echo.
echo  ============================================================
echo    RESTARON - BOSHQA KOMPYUTERGA NUSXA OLISH
echo  ============================================================
echo.
echo    ZIP ichiga KIRADI:
echo      - butun dastur kodi
echo      - menyu, stollar, xodimlar, buyurtmalar, cheklar arxivi
echo      - taom suratlari va QR rasmlari
echo      - sozlamalar ^(printerlar, xizmat haqi, chek shrifti^)
echo.
echo    ZIP ichiga KIRMAYDI ^(yangi kompyuterda qaytadan yaratiladi^):
echo      - backend\.venv       ^(ichida eski kompyuter yo'llari bor^)
echo      - frontend\node_modules
echo      - jurnal fayllari va vaqtinchalik manzillar
echo.
echo  ============================================================
echo.

set "STAMP=%DATE:~-4%-%DATE:~3,2%-%DATE:~0,2%"
set "STAMP=%STAMP: =0%"
set "OUT=%USERPROFILE%\Desktop\RestAron_nusxa_%STAMP%.zip"
set "TMPDIR=%TEMP%\RestAron_nusxa"

if exist "%TMPDIR%" rd /s /q "%TMPDIR%" >nul 2>&1
mkdir "%TMPDIR%" >nul 2>&1

echo  [1/4] Fayllar yig'ilmoqda...
robocopy "%~dp0." "%TMPDIR%" /E /NFL /NDL /NJH /NJS /NP ^
  /XD ".venv" "node_modules" "__pycache__" "zaxira" "dist" ^
  /XF "*.log" "SERVER_ONLINE_URL.txt" "tunnel_sozlama.txt" "_xizmat_ishga_tushirish.cmd" "_saytni_ochish.cmd" "*.pid" >nul
if %errorLevel% geq 8 (
    echo        XATO: fayllarni ko'chirib bo'lmadi.
    pause
    exit /b 1
)
echo        Tayyor.

echo  [2/4] Ma'lumotlar bazasi xavfsiz ko'chirilmoqda...
if exist "!PY!" (
    "!PY!" "%~dp0backend\nusxa.py" "%~dp0backend\restaron.db" "%TMPDIR%\backend\restaron.db"
) else (
    echo        Eslatma: Python topilmadi, baza oddiy ko'chirildi.
)

echo  [3/4] ZIP yaratilmoqda ^(1-2 daqiqa^)...
if exist "%OUT%" del /f /q "%OUT%" >nul 2>&1
powershell -NoProfile -Command "Compress-Archive -Path '%TMPDIR%\*' -DestinationPath '%OUT%' -CompressionLevel Optimal -Force"
if not exist "%OUT%" (
    echo        XATO: ZIP yaratilmadi.
    pause
    exit /b 1
)

echo  [4/4] Tozalanmoqda...
rd /s /q "%TMPDIR%" >nul 2>&1

for %%F in ("%OUT%") do set "SIZE=%%~zF"
set /a SIZEMB=!SIZE!/1048576

echo.
echo  ============================================================
echo    TAYYOR
echo  ============================================================
echo.
echo    Fayl:   %OUT%
echo    Hajmi:  !SIZEMB! MB
echo.
echo    YANGI KOMPYUTERDA:
echo      1. ZIP ni O'NG tugma -^> Properties -^> "Unblock" -^> OK
echo      2. Shundan KEYIN oching, C:\RestAron ga chiqaring
echo      3. Python 3.11 va Node.js LTS o'rnating
echo      4. 1_BIRINCHI_ORNATISH.bat        ^(ikki marta bosing^)
echo      5. 2_SERVERNI_ORNATISH.bat        ^(administrator nomidan^)
echo.
echo    DIQQAT: stollardagi eski QR kodlar yangi kompyuterning
echo    manziliga ishora qilmaydi - admin panelda QR manzilini
echo    sozlab, QR kodlarni QAYTA CHOP ETING.
echo  ============================================================
echo.
explorer /select,"%OUT%"
pause
