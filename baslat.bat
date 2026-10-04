@echo off
chcp 65001 > nul
title Transkript
echo ======================================================
echo   Transkript - PDR Yerel Ses Donusturucu
echo   (Tamamen Yerel ve Gizli - Veri Disari Cikmaz)
echo ======================================================
echo.
echo Uygulama baslatiliyor, lutfen bekleyin...
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Uygulama baslatilamadi!
    pause
)
