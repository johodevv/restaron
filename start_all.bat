@echo off
title RestAron Asosiy Restoran Serveri
color 0A
echo =======================================================================
echo          🍽️ RESTARON - SMART RESTAURANT SERVER (MAHALLIY SERVER)
echo =======================================================================
echo.
echo 1. Kompyuter tarmog'i va IP manzili tekshirilmoqda...

for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.254*' } | Select-Object -First 1).IPAddress"') do set LOCAL_IP=%%a

if "%LOCAL_IP%"=="" set LOCAL_IP=127.0.0.1

echo.
echo [OK] Kompyuteringizning Wi-Fi IP manzili: %LOCAL_IP%
echo.
echo 2. Backend server ishga tushirilmoqda (Python FastAPI / Port 8000)...
start "RestAron Backend Server" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start_backend.ps1"

timeout /t 3 /nobreak >nul

echo 3. Frontend dev server ishga tushirilmoqda (Vite React / Port 5173)...
start "RestAron Frontend Server" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start_frontend.ps1"

timeout /t 2 /nobreak >nul

echo.
echo =======================================================================
echo               🎉 RESTARON SERVER ISHGA TUSHDI!
echo =======================================================================
echo.
echo  * USHBU KOMPYUTERDA (Kassa / Admin):
echo      - Asosiy tizim (Admin panel): http://localhost:5173
echo      - Backend va Kassa POS:       http://localhost:8000
echo      - API Hujjatlari:             http://localhost:8000/docs
echo.
echo  * OFITSIANTLAR UCHUN TELEFONDA OCHISH (Bir xil Wi-Fi tarmog'ida):
echo      - Havola: http://%LOCAL_IP%:5173
echo      - Yoki:   http://%LOCAL_IP%:8000
echo.
echo  * CHEK PRINTERLARI:
echo      - 1-Printer (Kassa / Hisob cheki)
echo      - 2-Printer (1-Oshxona - Qozon taomlari)
echo      - 3-Printer (2-Oshxona - Baliq va Somsa)
echo.
echo  (Eslatma: Ushbu qora oynalarni yopmang, ular yopilsa server to'xtaydi)
echo =======================================================================
echo.
pause
