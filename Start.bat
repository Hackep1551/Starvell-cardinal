@echo off
chcp 65001 >nul
cls
echo ================================
echo Starvell Telegram Bot
echo ================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Download Python from https://www.python.org/
    pause
    exit /b 1
)

echo [INFO] Starting bot...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot crashed!
    echo Check bot.log for details
    echo.
    pause
    exit /b 1
)

pause