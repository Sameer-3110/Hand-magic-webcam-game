@echo off
title HAND MAGIC
cd /d "%~dp0"

echo ========================================
echo          HAND MAGIC GAME
echo ========================================
echo.
echo Starting webcam hand tracking...
echo.
"C:\Users\samee\AppData\Local\Programs\Python\Python312\python.exe" main.py

if errorlevel 1 (
    echo.
    echo The game stopped because of an error.
    echo Check the message above.
    pause
)
