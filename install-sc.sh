#!/bin/bash

# Скрипт для быстрой установки Starvell Cardinal на Linux сервер
# Используется: wget https://raw.githubusercontent.com/Hackep1551/Starvell-cardinal/main/install-sc.sh -O install-sc.sh && bash install-sc.sh

set -e

# Цвета для вывода
RED='\033[1;31m'
GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[1;35m'
RESET='\033[0m'

# Логотип
LOGO="
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ███████╗████████╗ █████╗ ██████╗ ██╗   ██╗███████╗██╗     ║
║   ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║   ██║██╔════╝██║     ║
║   ███████╗   ██║   ███████║██████╔╝██║   ██║█████╗  ██║     ║
║   ╚════██║   ██║   ██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  ██║     ║
║   ███████║   ██║   ██║  ██║██║  ██║ ╚████╔╝ ███████╗███████╗║
║   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝║
║                                                               ║
║              Starvell Cardinal - Fast Installer              ║
╚═══════════════════════════════════════════════════════════════╝
"

echo -e "${CYAN}${LOGO}${RESET}"
echo -e "${MAGENTA}By Starvell Team${RESET}"
echo -e "${CYAN}GitHub: github.com/Hackep1551/Starvell-cardinal${RESET}\n"

# Проверка прав суперпользователя
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ Не запускайте этот скрипт от имени root!${RESET}"
   echo -e "${YELLOW}💡 Скрипт сам запросит sudo при необходимости.${RESET}"
   exit 1
fi

# Проверка зависимостей
check_dependencies() {
    local deps=("curl" "wget" "git")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            echo -e "${YELLOW}📦 Устанавливаю $dep...${RESET}"
            sudo apt update && sudo apt install -y "$dep" || {
                echo -e "${RED}❌ Ошибка при установке $dep${RESET}"
                exit 1
            }
        fi
    done
}

# Ввод параметров установки
setup_parameters() {
    echo -e "${CYAN}⚙️  Параметры установки:${RESET}\n"
    
    # Имя пользователя
    while true; do
        read -p "👤 Введите имя пользователя для Starvell Cardinal: " USERNAME
        
        if [[ ! "$USERNAME" =~ ^[a-zA-Z][a-zA-Z0-9_-]*$ ]]; then
            echo -e "${RED}❌ Имя должно начинаться с буквы и содержать только буквы, цифры, '_' или '-'${RESET}"
            continue
        fi
        
        if id "$USERNAME" &>/dev/null; then
            read -p "👤 Пользователь $USERNAME уже существует. Использовать его? (y/n): " use_existing
            if [[ "$use_existing" == "y" ]]; then
                break
            fi
        else
            break
        fi
    done
    
    # Директория установки
    read -p "📁 Путь для установки [/home/$USERNAME/starvell-cardinal]: " INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-/home/$USERNAME/starvell-cardinal}"
    
    # Telegram Token
    read -sp "🤖 Введите Telegram Bot Token: " BOT_TOKEN
    echo ""
    
    if [[ -z "$BOT_TOKEN" ]]; then
        echo -e "${RED}❌ Bot Token не может быть пустым!${RESET}"
        exit 1
    fi
    
    # Стартовая команда (опционально)
    read -p "▶️  Автоматически запустить бота? (y/n) [y]: " START_BOT
    START_BOT="${START_BOT:-y}"
}

# Установка системных зависимостей
install_system_deps() {
    echo -e "\n${CYAN}📦 Установка системных зависимостей...${RESET}"
    
    if ! sudo apt update; then
        echo -e "${RED}❌ Ошибка при обновлении списка пакетов${RESET}"
        exit 2
    fi
    
    if ! sudo apt install -y python3 python3-pip python3-venv git curl wget; then
        echo -e "${RED}❌ Ошибка при установке зависимостей${RESET}"
        exit 2
    fi
    
    echo -e "${GREEN}✅ Системные зависимости установлены${RESET}"
}

# Создание пользователя
create_user() {
    if ! id "$USERNAME" &>/dev/null; then
        echo -e "\n${CYAN}👤 Создаю пользователя $USERNAME...${RESET}"
        if ! sudo useradd -m -s /bin/bash "$USERNAME"; then
            echo -e "${RED}❌ Ошибка при создании пользователя${RESET}"
            exit 2
        fi
        echo -e "${GREEN}✅ Пользователь $USERNAME создан${RESET}"
    else
        echo -e "${YELLOW}ℹ️  Пользователь $USERNAME уже существует${RESET}"
    fi
}

# Клонирование репозитория
clone_repository() {
    echo -e "\n${CYAN}📥 Клонирую репозиторий...${RESET}"
    
    # Удаляем старую директорию если существует
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}⚠️  Директория $INSTALL_DIR уже существует${RESET}"
        read -p "Перезаписать? (y/n) [y]: " overwrite
        overwrite="${overwrite:-y}"
        
        if [[ "$overwrite" == "y" ]]; then
            sudo rm -rf "$INSTALL_DIR"
        else
            echo -e "${YELLOW}ℹ️  Использую существующую директорию${RESET}"
            return
        fi
    fi
    
    if ! sudo git clone https://github.com/Hackep1551/Starvell-cardinal.git "$INSTALL_DIR"; then
        echo -e "${RED}❌ Ошибка при клонировании репозитория${RESET}"
        exit 2
    fi
    
    echo -e "${GREEN}✅ Репозиторий клонирован в $INSTALL_DIR${RESET}"
}

# Установка Python зависимостей
install_python_deps() {
    echo -e "\n${CYAN}🐍 Установка Python зависимостей...${RESET}"
    
    if ! sudo -u "$USERNAME" python3 -m venv "$INSTALL_DIR/venv"; then
        echo -e "${RED}❌ Ошибка при создании виртуального окружения${RESET}"
        exit 2
    fi
    
    # Активируем виртуальное окружение и устанавливаем зависимости
    if ! sudo -u "$USERNAME" bash -c "source $INSTALL_DIR/venv/bin/activate && pip install --upgrade pip && pip install -r $INSTALL_DIR/requirements.txt"; then
        echo -e "${RED}❌ Ошибка при установке Python зависимостей${RESET}"
        exit 2
    fi
    
    echo -e "${GREEN}✅ Python зависимости установлены${RESET}"
}

# Настройка конфигурации
setup_config() {
    echo -e "\n${CYAN}⚙️  Настройка конфигурации...${RESET}"
    
    # Создаём директорию configs
    CONFIG_DIR="$INSTALL_DIR/configs"
    if ! sudo -u "$USERNAME" mkdir -p "$CONFIG_DIR"; then
        echo -e "${RED}❌ Ошибка при создании директории configs${RESET}"
        exit 2
    fi
    
    # Создаём конфиг файл с токеном
    CONFIG_FILE="$CONFIG_DIR/_main.cfg"
    
    sudo tee "$CONFIG_FILE" > /dev/null << 'EOF'
[Starvell]
session_cookie = 
bot_token = 
user_agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
autoRaise = 0
autoDelivery = 0
autoRestore = 0
locale = ru

[Logging]
level = INFO
file = logs/bot.log
EOF
    
    # Устанавливаем права доступа
    sudo chown "$USERNAME:$USERNAME" "$CONFIG_FILE"
    sudo chmod 600 "$CONFIG_FILE"
    
    echo -e "${GREEN}✅ Конфигурация создана в $CONFIG_FILE${RESET}"
    echo -e "${YELLOW}⚠️  ВАЖНО: Отредактируйте $CONFIG_FILE и добавьте session_cookie${RESET}"
}

# Создание systemd сервиса
create_systemd_service() {
    echo -e "\n${CYAN}🔧 Создаю systemd сервис...${RESET}"
    
    SERVICE_FILE="/etc/systemd/system/starvell-cardinal.service"
    
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Starvell Cardinal Bot
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable starvell-cardinal.service
    
    echo -e "${GREEN}✅ Systemd сервис создан${RESET}"
}

# Создание скрипта для управления ботом
create_management_script() {
    echo -e "\n${CYAN}📝 Создаю скрипт управления...${RESET}"
    
    MANAGE_SCRIPT="$INSTALL_DIR/manage.sh"
    
    sudo tee "$MANAGE_SCRIPT" > /dev/null << 'EOF'
#!/bin/bash

# Скрипт для управления Starvell Cardinal

case "$1" in
    start)
        echo "▶️  Запуск Starvell Cardinal..."
        sudo systemctl start starvell-cardinal.service
        echo "✅ Сервис запущен"
        ;;
    stop)
        echo "⏹️  Остановка Starvell Cardinal..."
        sudo systemctl stop starvell-cardinal.service
        echo "✅ Сервис остановлен"
        ;;
    restart)
        echo "🔄 Перезапуск Starvell Cardinal..."
        sudo systemctl restart starvell-cardinal.service
        echo "✅ Сервис перезапущен"
        ;;
    status)
        echo "📊 Статус Starvell Cardinal:"
        sudo systemctl status starvell-cardinal.service
        ;;
    logs)
        echo "📋 Логи (последние 50 строк):"
        sudo journalctl -u starvell-cardinal.service -n 50 -f
        ;;
    config)
        echo "⚙️  Редактирование конфигурации..."
        sudo nano "$(dirname "$0")/configs/_main.cfg"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|config}"
        exit 1
        ;;
esac
EOF
    
    sudo chmod +x "$MANAGE_SCRIPT"
    sudo chown "$USERNAME:$USERNAME" "$MANAGE_SCRIPT"
    
    echo -e "${GREEN}✅ Скрипт управления создан в $MANAGE_SCRIPT${RESET}"
}

# Финальный вывод
show_final_info() {
    echo -e "\n${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
    echo -e "${GREEN}║          ✅ Установка завершена успешно!             ║${RESET}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${RESET}\n"
    
    echo -e "${CYAN}📍 Директория установки:${RESET}"
    echo -e "   ${YELLOW}$INSTALL_DIR${RESET}\n"
    
    echo -e "${CYAN}⚙️  Следующие шаги:${RESET}"
    echo -e "   1️⃣  Отредактируйте конфигурацию:"
    echo -e "      ${YELLOW}nano $INSTALL_DIR/configs/_main.cfg${RESET}"
    echo -e ""
    echo -e "   2️⃣  Добавьте session_cookie от Starvell.com\n"
    
    if [[ "$START_BOT" == "y" ]]; then
        echo -e "   3️⃣  Запустите бота:"
        echo -e "      ${YELLOW}sudo systemctl start starvell-cardinal${RESET}"
    fi
    
    echo -e "\n${CYAN}📊 Команды для управления:${RESET}"
    echo -e "   ${YELLOW}$INSTALL_DIR/manage.sh start${RESET}      - Запустить бота"
    echo -e "   ${YELLOW}$INSTALL_DIR/manage.sh stop${RESET}       - Остановить бота"
    echo -e "   ${YELLOW}$INSTALL_DIR/manage.sh restart${RESET}    - Перезапустить бота"
    echo -e "   ${YELLOW}$INSTALL_DIR/manage.sh status${RESET}     - Статус бота"
    echo -e "   ${YELLOW}$INSTALL_DIR/manage.sh logs${RESET}       - Просмотреть логи"
    echo -e "   ${YELLOW}$INSTALL_DIR/manage.sh config${RESET}     - Редактировать конфиг\n"
    
    echo -e "${CYAN}🔗 Ссылки:${RESET}"
    echo -e "   GitHub: ${YELLOW}https://github.com/Hackep1551/Starvell-cardinal${RESET}"
    echo -e "   Telegram: ${YELLOW}https://t.me/kapystus${RESET}\n"
}

# Основной процесс
main() {
    check_dependencies
    setup_parameters
    install_system_deps
    create_user
    clone_repository
    install_python_deps
    setup_config
    create_systemd_service
    create_management_script
    
    if [[ "$START_BOT" == "y" ]]; then
        echo -e "\n${CYAN}▶️  Запуск бота...${RESET}"
        sudo systemctl start starvell-cardinal.service
    fi
    
    show_final_info
}

# Запуск основной функции
main
