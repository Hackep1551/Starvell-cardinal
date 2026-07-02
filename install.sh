#!/usr/bin/env bash
#
# Starvell Cardinal — установка одной командой.
#
#   curl -fsSL https://raw.githubusercontent.com/Hackep1551/Starvell-cardinal/main/install.sh | bash
#
# Скрипт склонирует проект, поставит зависимости и подготовит запуск.
#
set -e

RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
BOLD='\033[1m'
RESET='\033[0m'

REPO_URL="https://github.com/Hackep1551/Starvell-cardinal.git"
BRANCH="main"
TARGET_DIR="${1:-Starvell-cardinal}"

ok()   { echo -e "  ${GREEN}[OK]${RESET} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${RESET} $1"; }
err()  { echo -e "  ${RED}[ERROR]${RESET} $1"; }
info() { echo -e "  ${CYAN}[INFO]${RESET} $1"; }

echo ""
echo -e "${CYAN}${BOLD}Starvell Cardinal — установка${RESET}"
echo ""

# --- git ---
if command -v git &>/dev/null; then
    ok "$(git --version)"
else
    err "Git не установлен."
    info "Debian/Ubuntu: sudo apt install -y git"
    info "CentOS/RHEL:   sudo yum install -y git"
    info "macOS:         brew install git"
    exit 1
fi

# --- python ---
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

if [[ -n "$PYTHON_CMD" ]]; then
    ok "$($PYTHON_CMD --version 2>&1) ($PYTHON_CMD)"
else
    err "Python не найден."
    info "Debian/Ubuntu: sudo apt install -y python3 python3-pip python3-venv"
    info "CentOS/RHEL:   sudo yum install -y python3 python3-pip"
    info "macOS:         brew install python3"
    exit 1
fi
echo ""

# --- клонирование ---
if [[ -d "$TARGET_DIR/.git" ]]; then
    warn "Папка $TARGET_DIR уже содержит репозиторий — обновляю."
    cd "$TARGET_DIR"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
    ok "Код обновлён до последней версии."
else
    if [[ -d "$TARGET_DIR" ]]; then
        err "Папка $TARGET_DIR уже существует и это не git-репозиторий."
        info "Удалите её или укажите другое имя: bash install.sh другое_имя"
        exit 1
    fi
    info "Клонирую $REPO_URL ..."
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
    ok "Проект склонирован в $(pwd)"
fi
echo ""

# --- виртуальное окружение ---
if [[ ! -d "venv" ]]; then
    info "Создаю виртуальное окружение..."
    if $PYTHON_CMD -m venv venv 2>/dev/null; then
        ok "venv создан."
    else
        warn "Не удалось создать venv — ставлю зависимости глобально."
        warn "На Debian/Ubuntu поставьте: sudo apt install -y python3-venv"
    fi
fi

PIP_CMD="$PYTHON_CMD -m pip"
if [[ -d "venv" ]]; then
    # shellcheck disable=SC1091
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
        PIP_CMD="pip"
        ok "Окружение venv активировано."
    fi
fi
echo ""

# --- зависимости ---
info "Обновляю pip..."
$PIP_CMD install --upgrade pip &>/dev/null || true

info "Устанавливаю зависимости..."
if $PIP_CMD install -r requirements.txt; then
    ok "Все зависимости установлены."
else
    warn "Первая попытка не удалась — пробую принудительно."
    $PIP_CMD install --force-reinstall -r requirements.txt
fi
echo ""

# --- права и директории ---
git config core.autocrlf input 2>/dev/null || true
for f in install.sh fix.sh fix.py main.py; do
    [[ -f "$f" ]] && chmod +x "$f"
done
for d in configs logs storage plugins; do
    [[ ! -d "$d" ]] && mkdir -p "$d"
done
ok "Директории и права настроены."
echo ""

echo -e "${GREEN}${BOLD}Установка завершена.${RESET}"
echo ""
info "Папка проекта: $(pwd)"
info "Запуск первичной настройки и бота:"
if [[ -d "venv" ]]; then
    echo -e "    ${BOLD}cd $TARGET_DIR && source venv/bin/activate && python main.py${RESET}"
else
    echo -e "    ${BOLD}cd $TARGET_DIR && $PYTHON_CMD main.py${RESET}"
fi
echo ""
