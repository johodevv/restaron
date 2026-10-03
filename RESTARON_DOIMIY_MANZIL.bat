@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Doimiy Internet Manzili
color 0B

REM  Cloudflare "named tunnel" sozlamasi: internet manzili o'zgarmaydigan
REM  bo'lib qoladi, shuning uchun stollardagi QR kodlar hech qachon buzilmaydi.

cd /d "%~dp0"
set "CFG=%~dp0tunnel_sozlama.txt"

echo.
echo  ============================================================
echo    RESTARON - DOIMIY INTERNET MANZILI
echo  ============================================================
echo.
echo    Hozir manzil har safar o'zgaradi (bepul trycloudflare).
echo    Shuning uchun stollardagi QR kodlarni qayta chop etish kerak.
echo.
echo    Doimiy manzil uchun KERAK BO'LADI:
echo      1. Cloudflare hisobi (bepul)       - dash.cloudflare.com
echo      2. O'z domeningiz (yiliga ~10-15 $) - Cloudflare ga qo'shilgan
echo.
echo    SO'NG Cloudflare panelida:
echo      Zero Trust -^> Networks -^> Tunnels -^> Create a tunnel
echo      Connector: Cloudflared  -^>  TOKEN ni nusxalang
echo      Public hostname: restoran.sizningdomen.uz
echo                       Service: HTTP  localhost:8000
echo.
echo  ============================================================
echo.

if exist "%CFG%" (
    echo  Hozirgi sozlama mavjud: tunnel_sozlama.txt
    echo.
)

echo  Davom etasizmi? Bekor qilish uchun oynani yoping.
echo.
set "TOKEN="
set /p TOKEN="  1) TOKEN ni shu yerga joylang: "
if "!TOKEN!"=="" (
    echo.
    echo  TOKEN kiritilmadi. Bekor qilindi.
    pause
    exit /b 1
)

set "MANZIL="
set /p MANZIL="  2) Doimiy manzil (masalan restoran.sizningdomen.uz): "
if "!MANZIL!"=="" (
    echo.
    echo  Manzil kiritilmadi. Bekor qilindi.
    pause
    exit /b 1
)

> "%CFG%" echo # RestAron doimiy internet manzili (Cloudflare named tunnel)
>>"%CFG%" echo # Bu faylni o'chirsangiz - yana bepul, o'zgaruvchan manzilga qaytadi.
>>"%CFG%" echo TOKEN=!TOKEN!
>>"%CFG%" echo MANZIL=!MANZIL!

echo.
echo  Saqlandi: tunnel_sozlama.txt
echo.
echo  Endi server qayta ishga tushirilishi kerak.
set "QAYTA="
set /p QAYTA="  Hoziroq qayta ishga tushiraymi? (ha / yoq): "
if /i "!QAYTA!"=="ha" (
    net session >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  Administrator huquqi kerak. Bu faylni o'ng tugma bilan bosib
        echo  "Run as administrator" orqali qayta ishga tushiring,
        echo  yoki 2_SERVERNI_ORNATISH.bat ni administrator nomidan oching.
    ) else (
        echo  Server qayta ishga tushirilmoqda...
        schtasks /End /TN "RestAron Server" >nul 2>&1
        timeout /t 3 /nobreak >nul
        schtasks /Run /TN "RestAron Server" >nul 2>&1
        echo  Tayyor.
    )
)

echo.
echo  ============================================================
echo    Doimiy manzilingiz:
echo      !MANZIL!
echo.
echo    1-2 daqiqadan keyin shu manzil orqali sayt ochiladi.
echo    Admin panelga kirib QR kodlarni QAYTA CHOP ETING -
echo    endi ular hech qachon buzilmaydi.
echo  ============================================================
echo.
pause
