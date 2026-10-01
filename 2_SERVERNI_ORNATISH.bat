@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Windows Server O'rnatish
color 0A

REM ===================================================================
REM  RestAron - Windows ni DOIMIY SERVER qilib sozlash
REM
REM  Bu skript bir marta, ADMINISTRATOR sifatida ishga tushiriladi:
REM    1. Kompyuter uyquga ketmasligini sozlaydi
REM    2. Firewall da 8000-portni ochadi
REM    3. Kompyuter yonganda serverni AVTOMATIK ishga tushiradi
REM       (foydalanuvchi tizimga kirmasa ham)
REM    4. Server qulab tushsa, o'zi qayta ko'tariladi
REM ===================================================================

echo.
echo  ================================================================
echo   RESTARON - WINDOWS SERVER O'RNATISH
echo  ================================================================
echo.

REM --- Administrator huquqini tekshirish ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  XATO: Administrator huquqi kerak!
    echo.
    echo  Shu faylni O'NG tugma bilan bosing va
    echo  "Run as administrator" / "Administrator nomidan ishga tushirish"
    echo  ni tanlang.
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"
set BASE_DIR=%~dp0
set PYTHON_PATH=%~dp0backend\.venv\Scripts\python.exe

if not exist "%PYTHON_PATH%" (
    echo  XATO: Python muhiti topilmadi:
    echo    %PYTHON_PATH%
    echo.
    echo  Avval quyidagilarni bajaring:
    echo    cd backend
    echo    python -m venv .venv
    echo    .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo  [1/5] Python muhiti topildi.

REM --- 2. Uyqu rejimini o'chirish ---
echo  [2/5] Uyqu rejimi o'chirilmoqda (server uzluksiz ishlashi uchun)...
powercfg /change standby-timeout-ac 0      >nul 2>&1
powercfg /change hibernate-timeout-ac 0    >nul 2>&1
powercfg /change disk-timeout-ac 0         >nul 2>&1
powercfg /hibernate off                    >nul 2>&1
REM Ekran o'chishi mumkin - bu serverga ta'sir qilmaydi, tok tejaydi
powercfg /change monitor-timeout-ac 15     >nul 2>&1
REM Noutbuk qopqog'i yopilganda ham ishlashda davom etsin
powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0 >nul 2>&1
powercfg /setactive SCHEME_CURRENT         >nul 2>&1
echo        Tayyor: kompyuter endi uyquga ketmaydi.

REM --- 3. Firewall ---
echo  [3/5] Firewall da 8000-port ochilmoqda...
netsh advfirewall firewall delete rule name="RestAron Server (8000)" >nul 2>&1
netsh advfirewall firewall add rule name="RestAron Server (8000)" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1
echo        Tayyor: ofitsiant telefonlari ulanishi mumkin.

REM --- 4. Avtomatik ishga tushish (Scheduled Task) ---
echo  [4/5] Avtomatik ishga tushish sozlanmoqda...
schtasks /Delete /TN "RestAron Server" /F >nul 2>&1
schtasks /Create /TN "RestAron Server" /SC ONSTART /RU SYSTEM /RL HIGHEST /F ^
  /TR "\"%PYTHON_PATH%\" \"%BASE_DIR%server_manager.py\" serve" >nul 2>&1

if %errorLevel% neq 0 (
    echo        OGOHLANTIRISH: Avtomatik ishga tushirishni sozlab bo'lmadi.
    echo        Serverni qo'lda RESTARON_ISHGA_TUSHIR.bat orqali yoqasiz.
) else (
    echo        Tayyor: kompyuter yonganda server o'zi ishga tushadi.
)

REM --- 5. Hoziroq ishga tushirish ---
echo  [5/5] Server ishga tushirilmoqda...
schtasks /Run /TN "RestAron Server" >nul 2>&1
timeout /t 20 /nobreak >nul

REM --- Mahalliy IP ni aniqlash ---
REM IP ni aniqlash. `for /f` ichidagi PowerShell quvuri (^|) ishonchsiz --
REM cmd uni PowerShell ga noto'g'ri uzatadi. Shuning uchun natijani
REM vaqtinchalik faylga yozamiz: qo'shtirnoq ichidagi | quvur deb olinmaydi.
set LOCAL_IP=
powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.254*' } | Select-Object -First 1).IPAddress" > "%TEMP%\restaron_ip.txt" 2>nul
if exist "%TEMP%\restaron_ip.txt" (
    set /p LOCAL_IP=<"%TEMP%\restaron_ip.txt"
    del "%TEMP%\restaron_ip.txt" >nul 2>&1
)
for /f "tokens=* delims= " %%i in ("!LOCAL_IP!") do set LOCAL_IP=%%i
if "!LOCAL_IP!"=="" set LOCAL_IP=127.0.0.1

echo.
echo  ================================================================
echo   O'RNATISH TUGADI
echo  ================================================================
echo.
echo    Kassa / Admin (shu kompyuterda):
echo      http://localhost:8000
echo.
echo    Ofitsiant telefonlari (bir xil Wi-Fi):
echo      http://!LOCAL_IP!:8000
echo.
echo    Internet orqali (4G, boshqa joydan):
echo      Manzil 1-2 daqiqada tayyor bo'ladi va
echo      SERVER_ONLINE_URL.txt fayliga yoziladi.
echo      Ko'rish uchun: RESTARON_URL_KOR.bat
echo.
echo    Admin login:  maqsad
echo    Admin parol:  01020307m
echo.
echo  ----------------------------------------------------------------
echo   Server endi FONDA doimiy ishlaydi.
echo   Kompyuter o'chib yonsa - o'zi qayta ishga tushadi.
echo   Bu oynani yopsangiz ham server to'xtamaydi.
echo.
echo   To'xtatish:  RESTARON_XIZMATNI_TOXTATISH.bat
echo   Jurnal:      server.log
echo  ================================================================
echo.
pause
