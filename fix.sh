#!/usr/bin/env bash
set -e

RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
BOLD='\033[1m'
RESET='\033[0m'

REPO_URL="https://github.com/Hackep1551/Starvell-cardinal.git"
BRANCH="main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ok()   { echo -e "  ${GREEN}[OK]${RESET} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${RESET} $1"; }
err()  { echo -e "  ${RED}[ERROR]${RESET} $1"; }
info() { echo -e "  ${CYAN}[INFO]${RESET} $1"; }

echo ""
echo -e "${CYAN}${BOLD}Starvell Cardinal — Fix Script${RESET}"
echo ""
info "Система: $(uname -s) $(uname -r)"
info "Папка проекта: $SCRIPT_DIR"
echo ""

ALL_OK=true

if command -v git &>/dev/null; then
    ok "$(git --version)"
else
    err "Git не установлен!"
    if [[ "$(uname -s)" == "Linux" ]]; then
        info "Установите: sudo apt install git  или  sudo yum install git"
    else
        info "Установите: brew install git  или  https://git-scm.com/"
    fi
    read -rp "Нажмите Enter для выхода..."
    exit 1
fi

PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

if [[ -n "$PYTHON_CMD" ]]; then
    ok "$($PYTHON_CMD --version 2>&1) ($PYTHON_CMD)"
else
    err "Python не найден!"
    if [[ "$(uname -s)" == "Linux" ]]; then
        info "Установите: sudo apt install python3 python3-pip"
    else
        info "Установите: brew install python3"
    fi
    ALL_OK=false
fi
echo ""

if [[ ! -d ".git" ]]; then
    warn "Папка .git не найдена. Инициализирую..."
    git init
    git remote add origin "$REPO_URL"
    git fetch origin "$BRANCH"
    git checkout -b "$BRANCH" --track "origin/$BRANCH"
    ok "Репозиторий инициализирован."
else
    ok "Репозиторий найден."
    CURRENT_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ -z "$CURRENT_URL" ]]; then
        warn "Remote origin не настроен. Добавляю..."
        git remote add origin "$REPO_URL"
        ok "Remote origin добавлен."
    elif [[ "$CURRENT_URL" != "$REPO_URL" ]]; then
        warn "Remote origin: $CURRENT_URL"
        info "Обновляю на: $REPO_URL"
        git remote set-url origin "$REPO_URL"
        ok "Remote origin обновлён."
    else
        ok "Remote origin: $CURRENT_URL"
    fi
fi
echo ""

info "Обновление из GitHub..."
if git fetch origin "$BRANCH" 2>/dev/null; then
    NEW_COMMITS=$(git log HEAD..origin/$BRANCH --oneline 2>/dev/null || echo "")
    if [[ -n "$NEW_COMMITS" ]]; then
        COMMIT_COUNT=$(echo "$NEW_COMMITS" | wc -l | tr -d ' ')
        info "Доступно $COMMIT_COUNT новых коммитов."
        git reset --hard "origin/$BRANCH"
        ok "Код обновлён до последней версии."
    else
        ok "Уже на последней версии."
    fi
else
    err "Не удалось получить обновления. Проверьте интернет."
    ALL_OK=false
fi
echo ""

git config core.autocrlf input
ok "core.autocrlf = input"

for f in fix.sh fix.py main.py; do
    [[ -f "$f" ]] && chmod +x "$f"
done
ok "Скрипты сделаны исполняемыми."
echo ""

if [[ -n "$PYTHON_CMD" ]]; then
    info "Обновляю pip..."
    $PYTHON_CMD -m pip install --upgrade pip 2>/dev/null || true

    if [[ -f "requirements.txt" ]]; then
        info "Устанавливаю зависимости..."
        if $PYTHON_CMD -m pip install -r requirements.txt; then
            ok "Все зависимости установлены."
        else
            warn "Ошибка установки. Пробую принудительно..."
            $PYTHON_CMD -m pip install --force-reinstall -r requirements.txt || ALL_OK=false
        fi
    else
        err "requirements.txt не найден!"
        ALL_OK=false
    fi
else
    warn "Python не найден — пропускаю установку зависимостей."
    ALL_OK=false
fi
echo ""

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
ok "Кеш очищен."

for d in configs logs storage plugins; do
    [[ ! -d "$d" ]] && mkdir -p "$d" && info "Создана папка: $d/"
    [[ -z "$(ls -A "$d" 2>/dev/null)" ]] && touch "$d/.gitkeep"
done
ok "Все директории на месте."
echo ""

if $ALL_OK; then
    ok "Все проверки пройдены! Запустите бота: python3 main.py"
else
    warn "Исправлено с предупреждениями. Проверьте сообщения выше."
fi

echo ""
read -rp "Нажмите Enter для выхода..."
