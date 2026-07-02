@echo off
chcp 65001 >nul
title Starvell Cardinal - Fix

echo.
echo Starvell Cardinal - Fix Script
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found! Download: https://git-scm.com/download/win
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('git --version 2^>^&1') do echo [OK] %%i
echo.

if not exist ".git" (
    echo [WARN] .git not found. Initializing...
    git init
    git remote add origin https://github.com/Hackep1551/Starvell-cardinal.git
    git fetch origin main
    git checkout -b main --track origin/main
    echo [OK] Repository initialized.
) else (
    echo [OK] Repository found.
)

for /f "tokens=*" %%i in ('git remote get-url origin 2^>^&1') do set GIT_URL=%%i
if "%GIT_URL%"=="" (
    echo [WARN] Remote origin not set. Adding...
    git remote add origin https://github.com/Hackep1551/Starvell-cardinal.git
) else (
    echo [OK] Remote: %GIT_URL%
)
echo.

echo [INFO] Fetching updates from GitHub...
git fetch origin main
if errorlevel 1 (
    echo [ERROR] Could not fetch updates. Check internet connection.
) else (
    git reset --hard origin/main
    echo [OK] Code updated to latest version.
)
echo.

git config core.autocrlf true
echo [OK] core.autocrlf = true

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
echo.

echo [INFO] Installing dependencies...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Error installing. Retrying with --force-reinstall...
        python -m pip install --force-reinstall -r requirements.txt
    )
    echo [OK] Dependencies installed.
) else (
    echo [ERROR] requirements.txt not found!
)
echo.

echo [INFO] Cleaning cache...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)
del /s /q *.pyc >nul 2>&1
echo [OK] Cache cleared.

if not exist "configs" mkdir configs
if not exist "logs" mkdir logs
if not exist "storage" mkdir storage
if not exist "plugins" mkdir plugins
echo [OK] Directories OK.
echo.

echo [OK] Done! Start the bot: Start.bat
echo.
pause
