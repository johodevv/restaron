@echo off
chcp 65001 >nul
title RestAron - Rasmlarni siqish
cd /d "%~dp0"
echo.
echo ============================================================
echo   RESTARON - SAYTDAGI RASMLARNI SIQISH
echo ============================================================
echo.
echo  Saytdagi rasmlar juda katta bolsa sayt sekin ochiladi.
echo  Bu dastur ularni siqadi - sifat deyarli ozgarmaydi,
echo  lekin hajmi 10-40 barobar kichrayadi.
echo.
echo  Asl nusxalar "backend\uploads\_asl_nusxa" papkasiga saqlanadi.
echo.

set "PY=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo  Avval TEKSHIRAMIZ (hech narsa ozgarmaydi)...
echo ------------------------------------------------------------
"%PY%" "%~dp0backend\rasm_siqish.py" --korish
echo ------------------------------------------------------------
echo.
set /p JAVOB="  Siqishni boshlaymizmi? (ha / yoq): "
if /i not "%JAVOB%"=="ha" goto BEKOR
echo.
echo  Siqilmoqda, kuting...
echo ------------------------------------------------------------
"%PY%" "%~dp0backend\rasm_siqish.py"
echo ------------------------------------------------------------
echo.
echo  TAYYOR. Endi serverni qayta ishga tushiring:
echo    RESTARON_YANGILASH.bat
echo.
goto SON

:BEKOR
echo.
echo  Bekor qilindi - hech narsa ozgarmadi.
echo.

:SON
pause
