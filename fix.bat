@echo off
chcp 65001 >nul
title Starvell Cardinal - Fix Script

echo.
echo Starvell Cardinal — Fix Script
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Скачайте: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git не найден! Скачайте: https://git-scm.com/download/win
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('git --version 2^>^&1') do echo [OK] %%i
echo.

if not exist ".git" (
    echo [WARN] Папка .git не найдена. Инициализирую...
    git init
    git remote add origin https://github.com/Hackep1551/Starvell-cardinal.git
    git fetch origin main
    git checkout -b main --track origin/main
    echo [OK] Репозиторий инициализирован.
) else (
    echo [OK] Репозиторий найден.
)

for /f "tokens=*" %%i in ('git remote get-url origin 2^>^&1') do set GIT_URL=%%i
if "%GIT_URL%"=="" (
    echo [WARN] Remote origin не настроен. Добавляю...
    git remote add origin https://github.com/Hackep1551/Starvell-cardinal.git
) else (
    echo [OK] Remote: %GIT_URL%
)
echo.

echo [INFO] Обновление из GitHub...
git fetch origin main
if errorlevel 1 (
    echo [ERROR] Не удалось получить обновления! Проверьте интернет.
) else (
    git reset --hard origin/main
    echo [OK] Код обновлён до последней версии.
)
echo.

git config core.autocrlf true
echo [OK] core.autocrlf = true

echo [INFO] Обновляю pip...
python -m pip install --upgrade pip
echo.

echo [INFO] Устанавливаю зависимости...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Ошибка при установке. Пробую принудительно...
        python -m pip install --force-reinstall -r requirements.txt
    )
    echo [OK] Зависимости установлены.
) else (
    echo [ERROR] requirements.txt не найден!
)
echo.

echo [INFO] Очистка кеша...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)
del /s /q *.pyc >nul 2>&1
echo [OK] Кеш очищен.

if not exist "configs" mkdir configs
if not exist "logs" mkdir logs
if not exist "storage" mkdir storage
if not exist "plugins" mkdir plugins
echo [OK] Все директории на месте.
echo.

echo [OK] Все проверки завершены! Запустите бота: Start.bat
echo.
pause
