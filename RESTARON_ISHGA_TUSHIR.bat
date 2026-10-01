@echo off
chcp 65001 >nul
title RestAron - Serverni Ishga Tushirish
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║          RestAron Restaurant System - Server            ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  [1/3] Python tekshirilmoqda...

cd /d "%~dp0"

set PYTHON_PATH=%~dp0backend\.venv\Scripts\python.exe
if not exist "%PYTHON_PATH%" (
    echo  XATO: Python venv topilmadi!
    echo  Yo'l: %PYTHON_PATH%
    pause
    exit /b 1
)

echo  [2/3] Eski server to'xtatilmoqda (agar mavjud bo'lsa)...
taskkill /F /IM uvicorn.exe /T >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo  [3/3] Server ishga tushmoqda...
echo.
echo  Bu oyna yopilgandan keyin server FONDA ishlaydi.
echo  Kompyuteringizni odatdagidek ishlatishingiz mumkin.
echo.

"%PYTHON_PATH%" "%~dp0server_manager.py" start

echo.
echo  ════════════════════════════════════════════════════════
echo  Server natijasi yuqorida ko'rsatildi.
echo.
echo  SERVER_ONLINE_URL.txt faylini oching - u yerda
echo  ofitsianlarga berish uchun URL manzil yozilgan.
echo  ════════════════════════════════════════════════════════
echo.
pause
