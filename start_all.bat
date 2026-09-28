@echo off
title RestAron System Launcher
echo ========================================================
echo          RESTARON - SMART RESTAURANT SYSTEM
echo ========================================================
echo.
echo 1. Backend server ishga tushirilmoqda (Port 8000)...
start "RestAron Backend Server" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start_backend.ps1"

timeout /t 3 /nobreak >nul

echo 2. Frontend server ishga tushirilmoqda (Port 5173)...
start "RestAron Frontend Server" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start_frontend.ps1"

echo.
echo ========================================================
echo Barcha serverlar yangi oynalarda ishga tushirildi!
echo Backend:  http://localhost:8000 (API: /docs)
echo Frontend: http://localhost:5173
echo ========================================================
pause
