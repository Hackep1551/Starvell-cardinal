#!/bin/bash

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
║                      Telegram Bot Installer                  ║
╚═══════════════════════════════════════════════════════════════╝
"

clear
echo -e "${CYAN}${LOGO}${RESET}"
echo -e "${MAGENTA}By Starvell Team${RESET}"
echo -e "${CYAN}GitHub: github.com/Hackep1551/Starvell-cardinal${RESET}\n"

# Проверка прав суперпользователя
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}Не запускайте этот скрипт от имени root!${RESET}"
   echo -e "${YELLOW}Скрипт сам запросит sudo при необходимости.${RESET}"
   exit 1
fi

# Ввод имени пользователя
while true; do
  echo -e "${CYAN}Введите имя пользователя для FPC (будет создан новый пользователь):${RESET}"
  read -p "Имя пользователя: " USERNAME
  
  # Проверка имени пользователя
  if [[ ! "$USERNAME" =~ ^[a-zA-Z][a-zA-Z0-9_-]*$ ]]; then
    echo -e "${RED}Имя пользователя должно начинаться с буквы и содержать только буквы, цифры, '_', или '-'.${RESET}"
    continue
  fi
  
  break
done

echo -e "\n${GREEN}Начинаю установку для пользователя: ${USERNAME}${RESET}\n"
sleep 2

# Определение версии дистрибутива
DISTRO_VERSION=$(lsb_release -rs)
echo -e "${CYAN}Версия дистрибутива: ${DISTRO_VERSION}${RESET}\n"

# Обновление списка пакетов
echo -e "${CYAN}Обновляю список пакетов...${RESET}"
if ! sudo apt update; then
  echo -e "${RED}Ошибка при обновлении списка пакетов!${RESET}"
  exit 2
fi

# Установка необходимых пакетов
echo -e "\n${CYAN}Устанавливаю необходимые пакеты...${RESET}"
if ! sudo apt install -y software-properties-common curl wget git unzip; then
  echo -e "${RED}Ошибка при установке пакетов!${RESET}"
  exit 2
fi

# Установка Python
echo -e "\n${CYAN}Устанавливаю Python...${RESET}"
case $DISTRO_VERSION in
  "24.04" | "24.10")
    if ! sudo apt install -y python3.12 python3.12-dev python3.12-venv; then
      echo -e "${RED}Ошибка при установке Python!${RESET}"
      exit 2
    fi
    PYTHON_CMD="python3.12"
    ;;
  *)
    if ! sudo apt install -y python3.11 python3.11-dev python3.11-venv; then
      echo -e "${RED}Ошибка при установке Python!${RESET}"
      exit 2
    fi
    PYTHON_CMD="python3.11"
    ;;
esac

# Создание пользователя
echo -e "\n${CYAN}Создаю пользователя ${USERNAME}...${RESET}"
if ! sudo useradd -m $USERNAME 2>/dev/null; then
  echo -e "${YELLOW}Пользователь уже существует, продолжаю...${RESET}"
fi

# Создание виртуального окружения
echo -e "\n${CYAN}Создаю виртуальное окружение...${RESET}"
if ! sudo -u $USERNAME $PYTHON_CMD -m venv /home/$USERNAME/venv; then
  echo -e "${RED}Ошибка при создании виртуального окружения!${RESET}"
  exit 2
fi

# Обновление pip
echo -e "\n${CYAN}Обновляю pip...${RESET}"
if ! sudo -u $USERNAME /home/$USERNAME/venv/bin/python -m pip install --upgrade pip; then
  echo -e "${RED}Ошибка при обновлении pip!${RESET}"
  exit 2
fi

# Установка Starvell Bot
echo -e "\n${CYAN}Устанавливаю Starvell Bot...${RESET}"

# Скачивание репозитория
INSTALL_DIR="/home/$USERNAME/Starvell-cardinal"
echo -e "${CYAN}Скачиваю файлы в ${INSTALL_DIR}...${RESET}"

if [ -d "$INSTALL_DIR" ]; then
  echo -e "${YELLOW}Директория уже существует, обновляю...${RESET}"
  sudo rm -rf $INSTALL_DIR
fi

# Клонируем репозиторий (или копируем текущую директорию)
if [ -d ".git" ]; then
  sudo -u $USERNAME git clone . $INSTALL_DIR
else
  sudo mkdir -p $INSTALL_DIR
  sudo cp -r ./* $INSTALL_DIR/
  sudo chown -R $USERNAME:$USERNAME $INSTALL_DIR
fi

# Установка зависимостей
echo -e "\n${CYAN}Устанавливаю зависимости Python...${RESET}"
if ! sudo -u $USERNAME /home/$USERNAME/venv/bin/pip install -r $INSTALL_DIR/requirements.txt; then
  echo -e "${RED}Ошибка при установке зависимостей!${RESET}"
  exit 2
fi

# Создание systemd сервиса
echo -e "\n${CYAN}Создаю systemd сервис...${RESET}"

SERVICE_FILE="/etc/systemd/system/starvell-cardinal@.service"
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Starvell Telegram Bot
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/Starvell-cardinal
ExecStart=/home/%i/venv/bin/python /home/%i/Starvell-cardinal/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable starvell-cardinal@$USERNAME.service

# Завершение
clear
echo -e "${CYAN}${LOGO}${RESET}"
echo -e "${GREEN}################################################################################${RESET}"
echo -e "${GREEN}Установка завершена!${RESET}"
echo -e "${GREEN}################################################################################${RESET}\n"

echo -e "${CYAN}Запускаю первичную настройку...${RESET}"
sleep 2

# Запуск первичной настройки
clear
sudo -u $USERNAME LANG=en_US.utf8 /home/$USERNAME/venv/bin/python /home/$USERNAME/Starvell-cardinal/main.py

# Запуск сервиса
echo -e "\n${CYAN}Запускаю бота как фоновый процесс...${RESET}"
sudo systemctl start starvell-cardinal@$USERNAME.service

clear
echo -e "${CYAN}${LOGO}${RESET}"
echo -e "${GREEN}################################################################################${RESET}"
echo -e "${GREEN}Бот успешно установлен и запущен!${RESET}"
echo -e "${GREEN}################################################################################${RESET}\n"

echo -e "${CYAN}Полезные команды:${RESET}"
echo -e "  ${YELLOW}Статус:${RESET}       sudo systemctl status starvell-cardinal@$USERNAME"
echo -e "  ${YELLOW}Остановить:${RESET}   sudo systemctl stop starvell-cardinal@$USERNAME"
echo -e "  ${YELLOW}Запустить:${RESET}    sudo systemctl start starvell-cardinal@$USERNAME"
echo -e "  ${YELLOW}Перезапуск:${RESET}   sudo systemctl restart starvell-cardinal@$USERNAME"
echo -e "  ${YELLOW}Логи:${RESET}         sudo journalctl -u starvell-cardinal@$USERNAME -f"
echo -e "  ${YELLOW}Автозапуск:${RESET}   sudo systemctl enable starvell-cardinal@$USERNAME"
echo -e ""

echo -e "${GREEN}GitHub: ${CYAN}github.com/Hackep1551/Starvell-cardinal${RESET}"
echo -e "${GREEN}Telegram: ${CYAN}t.me/starvell_bot${RESET}\n"
