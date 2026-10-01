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
REM Eski xizmat ishlab turgan bo'lsa to'xtatamiz, aks holda 8000-port band
REM qolib, yangi server ishga tushmaydi (masalan boshqa papkadan qayta
REM o'rnatilayotgan bo'lsa).
schtasks /End /TN "RestAron Server" >nul 2>&1
schtasks /Delete /TN "RestAron Server" /F >nul 2>&1

REM 8000-portni band qilib turgan jarayonni topib yopamiz.
REM Natijani faylga yozamiz, chunki `for /f` ichida quvur ishonchsiz.
netstat -ano -p TCP > "%TEMP%\restaron_ports.txt" 2>nul
if exist "%TEMP%\restaron_ports.txt" (
    for /f "tokens=5" %%p in ('findstr /r /c:":8000 .*LISTENING" "%TEMP%\restaron_ports.txt"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    del "%TEMP%\restaron_ports.txt" >nul 2>&1
)
timeout /t 2 /nobreak >nul
REM Ishga tushiruvchi faylni yaratamiz.
REM MUHIM: schtasks /TR ichiga qo'sh tirnoqli uzun buyruq berib bo'lmaydi --
REM cmd `\"` ni ekranlash deb bilmaydi va uni so'zma-so'z uzatadi, natijada
REM yo'l buzilib, vazifa umuman ishga tushmaydi. Shuning uchun vazifa
REM BITTA faylga ishora qiladi, qolgan hammasi shu fayl ichida.
set LAUNCHER=%BASE_DIR%_xizmat_ishga_tushirish.cmd
> "%LAUNCHER%" echo @echo off
>>"%LAUNCHER%" echo cd /d "%BASE_DIR%"
>>"%LAUNCHER%" echo "%PYTHON_PATH%" "%BASE_DIR%server_manager.py" serve

schtasks /Create /TN "RestAron Server" /SC ONSTART /RU SYSTEM /RL HIGHEST /F /TR "%LAUNCHER%" >nul 2>&1

if %errorLevel% neq 0 (
    echo        OGOHLANTIRISH: Avtomatik ishga tushirishni sozlab bo'lmadi.
    echo        Serverni qo'lda RESTARON_ISHGA_TUSHIR.bat orqali yoqasiz.
) else (
    echo        Tayyor: kompyuter yonganda server o'zi ishga tushadi.
)

REM --- 5. Hoziroq ishga tushirish ---
echo  [5/5] Server ishga tushirilmoqda...
schtasks /Run /TN "RestAron Server" >nul 2>&1

REM Server haqiqatan javob berishini kutamiz (60 soniyagacha).
REM Ilgari shunchaki 20 soniya kutilib, "tayyor" deb yozilardi -- server
REM ko'tarilmagan bo'lsa ham. Endi haqiqiy holat tekshiriladi.
set SERVER_OK=0
for /l %%i in (1,1,20) do (
    if !SERVER_OK!==0 (
        timeout /t 3 /nobreak >nul
        powershell -NoProfile -Command "try { if ((Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
        if !errorLevel!==0 set SERVER_OK=1
    )
)

if !SERVER_OK!==1 (
    echo        Tayyor: server javob bermoqda.
) else (
    echo.
    echo        XATO: Server 60 soniyada ko'tarilmadi!
    echo.
    echo        Tekshiring:
    echo          1^) 1_BIRINCHI_ORNATISH.bat to'liq bajarilganmi?
    echo          2^) Jurnal: %BASE_DIR%server.log
    echo          3^) Qo'lda sinab ko'ring:
    echo             cd "%BASE_DIR%backend"
    echo             .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
    echo.
)

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
