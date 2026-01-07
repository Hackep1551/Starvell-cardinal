@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================
echo   Starvell Cardinal Bot
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

REM Check dependencies
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Starting bot...
echo ========================================
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Bot crashed with error code: %errorlevel%
    pause
)