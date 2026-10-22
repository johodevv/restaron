@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Avtomatik zaxira nusxalash jadvali
color 0B

REM ============================================================
REM   RESTARON - AVTOMATIK ZAXIRA JADVALI O'RNATISH (SCHTASKS)
REM   Har soatda backup_db.py ni ishga tushiradigan Windows vazifasi.
REM   Parol ishlatilmaydi (NT AUTHORITY\SYSTEM orqali ishlaydi).
REM ============================================================

REM 1. Administrator huquqini tekshirish
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  ============================================================
    echo    ADMINISTRATOR HUQUQI TALAB QILINADI
    echo  ============================================================
    echo.
    echo    Windows vazifalar rejalashtiruvchisida (Task Scheduler)
    echo    soatlik avtomatik zaxiralash vazifasini yaratish uchun
    echo    administrator huquqi kerak bo'ladi.
    echo.
    echo    UAC oynasi ochilmoqda, iltimos "Ha" (Yes) tugmasini bosing...
    echo  ============================================================
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

REM 2. Python va skript yo'lini aniqlash
set "PY=%~dp0backend\.venv\Scripts\python.exe"
if not exist "!PY!" (
    set "PY=python"
)
set "SCRIPT=%~dp0backend\tools\backup_db.py"

if not exist "!SCRIPT!" (
    echo.
    echo  XATOLIK: backup_db.py skripti topilmadi:
    echo  !SCRIPT!
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo    RESTARON - AVTOMATIK ZAXIRA VAZIFASI YARATILMOQDA...
echo  ============================================================
echo.
echo    Vazifa nomi:    RestAron-Zaxira
echo    Davriyligi:     Har 1 soatda (Hourly)
echo    Bajariluvchi:   "!PY!" "!SCRIPT!"
echo.

REM 3. schtasks orqali vazifani yaratish (parolsiz, SYSTEM hisobida)
schtasks /create /tn "RestAron-Zaxira" /tr "\"!PY!\" \"!SCRIPT!\"" /sc hourly /mo 1 /ru "SYSTEM" /f >nul 2>&1

if %errorLevel% neq 0 (
    REM Agar SYSTEM ruxsat bermasa, joriy foydalanuvchi hisobida parolsiz urinib ko'ramiz
    schtasks /create /tn "RestAron-Zaxira" /tr "\"!PY!\" \"!SCRIPT!\"" /sc hourly /mo 1 /f >nul 2>&1
)

if %errorLevel% equ 0 (
    echo.
    echo  ============================================================
    echo    MUVAFFAQIYATLI O'RNATILDI!
    echo  ============================================================
    echo.
    echo    "RestAron-Zaxira" vazifasi Windows jadvaliga muvaffaqiyatli
    echo    qo'shildi va har soatda avtomatik ishga tushadi.
    echo.
    echo    SAQLASH QOIDALARI:
    echo      - Oxirgi 48 soat: barcha soatlik nusxalar saqlanadi.
    echo      - 14 kungacha:    har kun uchun 1 ta nusxa saqlanadi.
    echo      - 14 kundan eski: eskilari avtomatik tozalanadi.
    echo      - BACKUP_EXTRA_DIR bo'lsa: boshqa disk/USB ga ham ko'chiriladi.
    echo.
    echo    FOYDALI BUYRUQLAR:
    echo      - Vazifa holatini ko'rish:
    echo          schtasks /query /tn "RestAron-Zaxira"
    echo      - Hoziroq sinab ko'rish:
    echo          schtasks /run /tn "RestAron-Zaxira"
    echo      - Jadvaldan o'chirish:
    echo          schtasks /delete /tn "RestAron-Zaxira" /f
    echo.
    echo  ============================================================
) else (
    echo.
    echo  XATOLIK: Vazifani yaratib bo'lmadi (errorLevel: %errorLevel%).
    echo  Iltimos, cmd oynasini Administrator sifatida ochib qayta urining.
    echo.
)

pause
