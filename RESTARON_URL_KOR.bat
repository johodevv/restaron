@echo off
chcp 65001 >nul
title RestAron - Internet URL

cd /d "%~dp0"

if exist "SERVER_ONLINE_URL.txt" (
    set /p URL=<SERVER_ONLINE_URL.txt
    echo.
    echo  ================================================
    echo  RestAron Internet URL (Ofitsianlarga bering):
    echo.
    echo    %URL%
    echo.
    echo  QR kod uchun admin panelga kiring: /login
    echo  ================================================
    echo.
    echo  URL ni clipboard ga nusxalash uchun yuqoridagi
    echo  manzilni sichqoncha bilan tanlang va Ctrl+C bosing.
    echo.
) else (
    echo.
    echo  XATO: Server hali ishlamayapti yoki URL topilmadi.
    echo  Avval RESTARON_ISHGA_TUSHIR.bat ni ishga tushiring.
    echo.
)
pause
