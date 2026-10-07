@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title RestAron - Yangilash
color 0A

REM  Bitta bosishda yangilash: git pull + qayta yig'ish + serverni qayta yoqish.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  XATO: Administrator huquqi kerak.
    echo  Bu faylni O'NG tugma bilan bosing -^> "Run as administrator".
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"

echo.
echo  ================================================================
echo   RESTARON - YANGILASH
echo  ================================================================
echo.
echo   Ma'lumotlaringiz ^(menyu, stollar, cheklar^) o'chmaydi.
echo.

REM ---------- Git tekshiruvi ----------
where git >nul 2>&1
if %errorLevel% neq 0 (
    echo  XATO: Git topilmadi.
    echo.
    echo  Git ni o'rnating: https://git-scm.com/download/win
    echo  Keyin shu faylni qayta ishga tushiring.
    echo.
    pause
    exit /b 1
)

if not exist ".git" (
    echo  XATO: Bu papka git orqali olinmagan.
    echo.
    echo  Yangi nusxani shunday oling:
    echo    git clone -b claude/sharp-cerf-koy3wf https://github.com/johodevv/restaron C:\RestAron
    echo.
    pause
    exit /b 1
)

echo  [1/4] Yangi kod yuklanmoqda...
git pull
if %errorLevel% neq 0 (
    echo.
    echo  XATO: Yangi kodni yuklab bo'lmadi.
    echo  Internet aloqasini tekshiring.
    echo  Agar "local changes" deb yozsa, quyidagini bajaring:
    echo      git stash
    echo  va shu faylni qayta ishga tushiring.
    echo.
    pause
    exit /b 1
)

echo.
echo  [2/4] Backend kutubxonalari tekshirilmoqda...
if not exist "backend\.venv\Scripts\python.exe" (
    echo  XATO: Python muhiti topilmadi.
    echo  Avval 1_BIRINCHI_ORNATISH.bat ni ishga tushiring.
    pause
    exit /b 1
)
"backend\.venv\Scripts\pip.exe" install -r "backend\requirements.txt" --quiet
echo        Tayyor.

echo  [3/4] Sayt qayta yig'ilmoqda ^(1-3 daqiqa^)...
pushd frontend
call npm install --no-audit --no-fund --silent
call npm run build --silent
set "RC=!errorLevel!"
popd
if not "!RC!"=="0" (
    echo.
    echo  XATO: Saytni yig'ib bo'lmadi.
    pause
    exit /b 1
)
if not exist "frontend\dist\index.html" (
    echo.
    echo  XATO: Sayt yig'ilmadi.
    pause
    exit /b 1
)
echo        Tayyor.

echo  [4/4] Server qayta ishga tushirilmoqda...

REM  MUHIM: schtasks /End faqat boshqaruvchi jarayonni to'xtatadi.
REM  Uning bolasi (uvicorn) tirik qolib, 8000-portni ESKI kod bilan
REM  ushlab turadi. Yangi server portni band deb ko'rib ishga tushmaydi
REM  va sayt eski holida qolaveradi. Shuning uchun portni bo'shatamiz.
schtasks /End /TN "RestAron Server" >nul 2>&1
taskkill /F /IM cloudflared.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

REM  8000-portni band qilib turgan jarayonni topib yopamiz.
netstat -ano -p TCP > "%TEMP%\restaron_ports.txt" 2>nul
if exist "%TEMP%\restaron_ports.txt" (
    for /f "tokens=5" %%p in ('findstr /r /c:":8000 .*LISTENING" "%TEMP%\restaron_ports.txt"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    del "%TEMP%\restaron_ports.txt" >nul 2>&1
)
timeout /t 3 /nobreak >nul

schtasks /Run /TN "RestAron Server" >nul 2>&1
if errorlevel 1 (
    echo        Eslatma: xizmat topilmadi.
    echo        2_SERVERNI_ORNATISH.bat ni administrator nomidan ishga tushiring.
    echo.
    pause
    exit /b 0
)

echo        Server javob berishi kutilmoqda...
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 45;$i++){ try { if((Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200){ $ok=$true; break } } catch {}; Start-Sleep -Seconds 2 }; if($ok){ exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo        DIQQAT: server javob bermadi. server.log ni tekshiring.
) else (
    echo        Server ishlamoqda.
    start "" "http://localhost:8000"
)

REM  Ishlab turgan versiyani ko'rsatamiz - yangilanish yetib kelganini
REM  shu raqamdan bilib olasiz.
set "VER="
for /f "delims=" %%v in ('powershell -NoProfile -Command "try{((Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing -TimeoutSec 5).Content ^| ConvertFrom-Json).version}catch{''}"') do set "VER=%%v"
if not "!VER!"=="" echo        Ishlayotgan versiya: !VER!

echo.
echo  ================================================================
echo   YANGILASH TUGADI
echo  ================================================================
echo.
echo   Brauzerda sahifani yangilang: Ctrl + F5
echo   ^(eski versiya keshda qolmasligi uchun^)
echo.
pause
