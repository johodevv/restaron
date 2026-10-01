@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - 1-QADAM: Dasturni Tayyorlash
color 0B

REM ===================================================================
REM  RestAron — BIRINCHI O'RNATISH (1-qadam)
REM
REM  Bu skript:
REM    1. Python va Node.js borligini tekshiradi
REM    2. Backend kutubxonalarini o'rnatadi (virtual muhitga)
REM    3. Frontend (sayt) ni yig'adi
REM
REM  Administrator huquqi KERAK EMAS. Oddiy ikki marta bosing.
REM  Tugagach 2-qadam: 2_SERVERNI_ORNATISH.bat
REM ===================================================================

cd /d "%~dp0"

echo.
echo  ================================================================
echo   RESTARON - 1-QADAM: DASTURNI TAYYORLASH
echo  ================================================================
echo.

REM ---------- Python tekshiruvi ----------
echo  [1/5] Python tekshirilmoqda...
set PY_CMD=
where py >nul 2>&1 && set PY_CMD=py -3
if "!PY_CMD!"=="" ( where python >nul 2>&1 && set PY_CMD=python )

if "!PY_CMD!"=="" (
    echo.
    echo   XATO: Python topilmadi!
    echo.
    echo   Python 3.11 ni yuklab o'rnating:
    echo     https://www.python.org/downloads/release/python-3119/
    echo.
    echo   MUHIM: o'rnatishda "Add Python to PATH" katagiga BELGI qo'ying!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('!PY_CMD! --version 2^>^&1') do set PYVER=%%v
echo        Topildi: Python !PYVER!

REM ---------- Node.js tekshiruvi ----------
echo  [2/5] Node.js tekshirilmoqda...
where node >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo   XATO: Node.js topilmadi!
    echo.
    echo   Node.js LTS ni yuklab o'rnating:
    echo     https://nodejs.org/
    echo.
    echo   O'rnatgach shu faylni QAYTA ishga tushiring.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do set NODEVER=%%v
echo        Topildi: Node.js !NODEVER!

REM ---------- Backend muhiti ----------
echo  [3/5] Backend kutubxonalari o'rnatilmoqda (2-5 daqiqa)...
if not exist "backend\.venv\Scripts\python.exe" (
    !PY_CMD! -m venv "backend\.venv"
    if !errorLevel! neq 0 (
        echo        XATO: virtual muhit yaratilmadi.
        pause
        exit /b 1
    )
)
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"backend\.venv\Scripts\pip.exe" install -r "backend\requirements.txt" --quiet
if !errorLevel! neq 0 (
    echo        XATO: kutubxonalarni o'rnatib bo'lmadi.
    echo        Internet aloqasini tekshiring va qayta urinib ko'ring.
    pause
    exit /b 1
)
REM USB printer uchun pywin32 ni ro'yxatdan o'tkazish (xato bo'lsa ham davom etadi)
"backend\.venv\Scripts\python.exe" -m pywin32_postinstall -install >nul 2>&1
echo        Tayyor.

REM ---------- Frontend ----------
echo  [4/5] Sayt yig'ilmoqda (1-3 daqiqa)...
pushd frontend
call npm install --no-audit --no-fund --silent
if !errorLevel! neq 0 (
    echo        XATO: npm install bajarilmadi.
    popd
    pause
    exit /b 1
)
call npm run build --silent
if !errorLevel! neq 0 (
    echo        XATO: saytni yig'ib bo'lmadi.
    popd
    pause
    exit /b 1
)
popd
echo        Tayyor.

REM ---------- Tekshiruv ----------
echo  [5/5] Natija tekshirilmoqda...
if not exist "frontend\dist\index.html" (
    echo        XATO: sayt yig'ilmadi (frontend\dist topilmadi).
    pause
    exit /b 1
)
echo        Hammasi joyida.

echo.
echo  ================================================================
echo   1-QADAM TUGADI
echo  ================================================================
echo.
echo   Endi 2-QADAM ni bajaring:
echo.
echo     2_SERVERNI_ORNATISH.bat  faylini
echo     O'NG tugma bilan bosing -^> "Run as administrator"
echo.
echo   U serverni doimiy ishlaydigan qilib sozlaydi.
echo  ================================================================
echo.
pause
