@echo off
chcp 65001 >nul
REM Delayed expansion: `set /p` bilan o'qilgan qiymat `if (...)` bloki
REM ichida %VAR% orqali ko'rinmaydi, shuning uchun !VAR! ishlatiladi.
setlocal enabledelayedexpansion
title RestAron - Server Ishga Tushmoqda...
color 0A

echo.
echo  RestAron Restaurant System
echo  ===========================
echo.

cd /d "%~dp0"

set PYTHON_PATH=%~dp0backend\.venv\Scripts\python.exe

if not exist "%PYTHON_PATH%" (
    echo  XATO: Python virtual environment topilmadi!
    echo  Avval: cd backend ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Eski jarayonlarni tozalash
echo  Eski server to'xtatilmoqda...
taskkill /F /IM cloudflared.exe /T >nul 2>&1
"%PYTHON_PATH%" "%~dp0server_manager.py" stop >nul 2>&1
timeout /t 3 /nobreak >nul

REM server_manager.py ni mustaqil jarayon sifatida ishga tushirish
echo  Yangi server ishga tushmoqda (fonda)...
echo  Bu bir necha soniya kutadi...
echo.

REM start /b: yangi jarayon sifatida (cmd dan alohida), lekin bir xil konsolda
start "RestAron-Backend" /min "%PYTHON_PATH%" "%~dp0server_manager.py" start

REM Server tayyor bo'lishini kutish (javob berishi bilan davom etamiz)
echo  Server tayyor bo'lishi kutilmoqda...
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 45;$i++){ try { if((Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200){ $ok=$true; break } } catch {}; Start-Sleep -Seconds 2 }; if($ok){ exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo  DIQQAT: Server javob bermadi. server.log ni tekshiring.
) else (
    echo  Server tayyor. Sayt brauzerda ochilmoqda...
    start "" "http://localhost:8000"
)

REM URL ni ko'rsatish
if exist "%~dp0SERVER_ONLINE_URL.txt" (
    set /p SERVER_URL=<"%~dp0SERVER_ONLINE_URL.txt"
    echo.
    echo  ================================================================
    echo  RestAron Server TAYYOR!
    echo  ================================================================
    echo.
    echo    Internet URL ^(4G/Wi-Fi^):
    echo    !SERVER_URL!
    echo.
    echo    Lokal:  http://localhost:8000
    echo.
    echo  ================================================================
    echo  Bu manzilni ofitsianlarga yuboring!
    echo  Kompyuteringizni odatdagidek ishlatishingiz mumkin.
    echo  Server FONDA ishlamoqda.
    echo  ================================================================
    echo.
    echo  To'xtatish: RESTARON_TOXTAT.bat
    echo.
) else (
    echo.
    echo  DIQQAT: Server hali tayyor emas yoki xatolik bor.
    echo  server.log faylini tekshiring.
    echo.
)

pause
