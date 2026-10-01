@echo off
title RestAron - Windows Firewall Portlarini Ochish
echo ========================================================
echo       RESTARON SERVER - FIREWALL PORTLARINI OCHISH
echo ========================================================
echo.
echo Ushbu buyruq kompyuteringizdagi 8000 va 5173 portlarini
echo restoran Wi-Fi tarmog'idagi ofitsiant telefonlari uchun ochadi.
echo.
echo Administrator huquqi talab qilinmoqda...
echo.

powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \"New-NetFirewallRule -DisplayName ''RestAron Server Ports (8000, 5173)'' -Direction Inbound -LocalPort 8000, 5173 -Protocol TCP -Action Allow -Profile Any -Force; Write-Host ''`n[OK] Portlar 8000 va 5173 muvaffaqiyatli ochildi! Endi ofitsiant telefonlari ulanishi mumkin.`n'' -ForegroundColor Green; Start-Sleep -Seconds 4\"' -Verb RunAs"

echo.
echo Agar administrator roziligi oynasi (UAC) chiqqan bo'lsa, 'Ha' (Yes) ni bosing.
echo.
pause
