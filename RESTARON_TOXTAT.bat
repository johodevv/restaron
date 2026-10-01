@echo off
chcp 65001 >nul
title RestAron - Serverni Toxtatish
color 0C

echo.
echo  RestAron Server Toxtatilmoqda...
echo.

cd /d "%~dp0"

set PYTHON_PATH=%~dp0backend\.venv\Scripts\python.exe

if exist "%PYTHON_PATH%" (
    "%PYTHON_PATH%" "%~dp0server_manager.py" stop
) else (
    taskkill /F /IM uvicorn.exe /T >nul 2>&1
    taskkill /F /IM cloudflared.exe /T >nul 2>&1
    echo  Server jarayonlari toxtatildi.
)

echo.
echo  Server toxtatildi. Yana ishga tushirish uchun
echo  RESTARON_ISHGA_TUSHIR.bat faylini ishga tushiring.
echo.
timeout /t 3 /nobreak >nul
