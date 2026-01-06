@echo off
chcp 65001 >nul
cls
echo ================================
echo Starvell Telegram Bot
echo ================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не установлен!
    echo Скачайте Python с https://www.python.org/
    pause
    exit /b 1
)

REM Запуск бота
echo Запуск бота...
echo.
python main.py

pause

echo [INFO] Запуск бота...
echo.

python -m bot.main

if errorlevel 1 (
    echo.
    echo [ERROR] Бот завершился с ошибкой!
    echo Проверьте файл bot.log для деталей
    echo.
    pause
    exit /b 1
)

pause
