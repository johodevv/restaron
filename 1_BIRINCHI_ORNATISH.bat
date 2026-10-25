@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
title RestAron - 1-QADAM: Dasturni Tayyorlash
color 0B

REM ===================================================================
REM  RestAron - BIRINCHI O'RNATISH (1-qadam)
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
set "PY_CMD=py -3.12"
%PY_CMD% -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 1)" >nul 2>&1
if not errorlevel 1 goto python_ready
set "PY_CMD=python"
%PY_CMD% -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 1)" >nul 2>&1
if not errorlevel 1 goto python_ready
echo.
echo XATO: Python 3.12 64-bit topilmadi. Shu loyiha uchun Python 3.12 kerak.
echo Yuklab olish: https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
echo O'rnatishda Add python.exe to PATH belgisini qo'ying.
echo So'ng shu BAT faylini qayta oching.
goto failed
:python_ready
%PY_CMD% --version

REM ---------- Node.js tekshiruvi ----------
echo  [2/5] Node.js tekshirilmoqda...
where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo   XATO: Node.js topilmadi!
    echo.
    echo   Node.js LTS ni yuklab o'rnating:
    echo     https://nodejs.org/
    echo.
    echo   O'rnatgach shu faylni QAYTA ishga tushiring.
    echo.
    goto failed
)
node --version
if errorlevel 1 goto failed
where npm.cmd >nul 2>&1
if errorlevel 1 goto npm_missing

if not exist "backend\requirements.txt" goto files_missing
if not exist "frontend\package.json" goto files_missing
if not exist "backend\.venv" goto environment_ready
if not exist "backend\.venv\Scripts\python.exe" goto environment_invalid
"backend\.venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 1)" >nul 2>&1
if errorlevel 1 goto environment_invalid
:environment_ready
if /i "%~1"=="--check" goto check_ok

REM ---------- Backend muhiti ----------
echo  [3/5] Backend kutubxonalari o'rnatilmoqda (2-5 daqiqa)...
if not exist "backend\.venv\Scripts\python.exe" (
    %PY_CMD% -m venv "backend\.venv"
    if errorlevel 1 (
        echo        XATO: virtual muhit yaratilmadi.
        goto failed
    )
)
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
    echo        XATO: kutubxonalarni o'rnatib bo'lmadi.
    echo        Internet aloqasini tekshiring va qayta urinib ko'ring.
    goto failed
)
REM USB printer uchun pywin32 ni ro'yxatdan o'tkazish (xato bo'lsa ham davom etadi)
"backend\.venv\Scripts\python.exe" -m pywin32_postinstall -install >nul 2>&1
echo        Tayyor.

REM ---------- Frontend ----------
echo  [4/5] Sayt yig'ilmoqda (1-3 daqiqa)...
pushd frontend
call npm ci --no-audit --no-fund
if errorlevel 1 (
    echo        XATO: npm install bajarilmadi.
    popd
    goto failed
)
call npm run build
if errorlevel 1 (
    echo        XATO: saytni yig'ib bo'lmadi.
    popd
    goto failed
)
popd
echo        Tayyor.

REM ---------- Tekshiruv ----------
echo  [5/5] Natija tekshirilmoqda...
if not exist "frontend\dist\index.html" (
    echo        XATO: sayt yig'ilmadi ^(frontend\dist topilmadi^).
    goto failed
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
exit /b 0

:environment_invalid
echo.
echo XATO: backend\.venv eski kompyuterga tegishli yoki Python versiyasi 3.12 emas.
echo Backend ichidagi .venv papkasini .venv_eski2 deb qayta nomlang.
echo Keyin shu BAT faylini qayta ishga tushiring. Baza fayliga tegmang.
goto failed
:npm_missing
echo XATO: npm.cmd topilmadi. Node.js o'rnatuvchisida npm ni ham o'rnating.
goto failed
:files_missing
echo XATO: loyiha fayllari yetishmayapti. BAT ni RestAron papkasiga joylang.
goto failed
:check_ok
echo TEKSHIRUV OTDI: Python 3.12 64-bit va Node.js tayyor. Hech narsa o'rnatilmadi.
exit /b 0
:failed
echo.
echo O'rnatish tugamadi. Yuqoridagi XATO yozuvini tekshiring.
if /i "%~1"=="--check" exit /b 1
pause
exit /b 1
