"""
Первичная установка Starvell Cardinal
"""

import os
import sys
import configparser
import hashlib
import time
import re
import socket
from pathlib import Path

try:
    from colorama import Fore, Style, init, Back
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Если colorama не установлена
    class Fore:
        CYAN = MAGENTA = RED = BLUE = GREEN = YELLOW = WHITE = LIGHTBLUE_EX = LIGHTGREEN_EX = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""
    class Back:
        BLACK = ""
    HAS_COLOR = False


# ═══════════════════════════════════════════════════════════
# 🎨 Стилизация
# ═══════════════════════════════════════════════════════════

def clear():
    """Очистить экран"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_logo():
    """Красивый ASCII логотип"""
    logo = f"""
{Fore.CYAN}{Style.BRIGHT}
    ███████╗████████╗ █████╗ ██████╗ ██╗   ██╗███████╗██╗     ██╗     
    ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║   ██║██╔════╝██║     ██║     
    ███████╗   ██║   ███████║██████╔╝██║   ██║█████╗  ██║     ██║     
    ╚════██║   ██║   ██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  ██║     ██║     
    ███████║   ██║   ██║  ██║██║  ██║ ╚████╔╝ ███████╗███████╗███████╗
    ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝╚══════╝
{Style.RESET_ALL}"""
    print(logo)


def print_header(step=None, total=5):
    """Красивый заголовок с индикатором прогресса"""
    clear()
    print_logo()
    
    if step:
        # Индикатор прогресса
        progress = "█" * step + "░" * (total - step)
        percentage = int((step / total) * 100)
        
        print(f"\n{Fore.CYAN}╔{'═' * 70}╗")
        print(f"║{' ' * 24}{Fore.WHITE}МАСТЕР УСТАНОВКИ{Fore.CYAN}{' ' * 30}║")
        print(f"║{' ' * 70}║")
        print(f"║  {Fore.LIGHTBLUE_EX}Прогресс: {Fore.GREEN}{progress}{Fore.CYAN} {percentage}% {Fore.WHITE}(Шаг {step} из {total}){Fore.CYAN}{' ' * (70 - 45 - len(str(step)) - len(str(total)))}║")
        print(f"╚{'═' * 70}╝{Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.CYAN}╔{'═' * 70}╗")
        print(f"║{' ' * 20}{Fore.WHITE}{Style.BRIGHT}ДОБРО ПОЖАЛОВАТЬ В STARVELL CARDINAL{Fore.CYAN}{Style.NORMAL}{' ' * 15}║")
        print(f"║{' ' * 25}{Fore.WHITE}Made by @kapystus{Fore.CYAN}{' ' * 29}║")
        print(f"╚{'═' * 70}╝{Style.RESET_ALL}\n")


def print_box(title, lines, color=Fore.CYAN):
    """Красивая рамка с текстом"""
    width = 68
    print(f"\n{color}┌─ {Fore.WHITE}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    for line in lines:
        print(f"{color}│ {Fore.WHITE}{line}{Style.RESET_ALL}")
    print(f"{color}└{'─' * width}{Style.RESET_ALL}\n")


def print_info(text, icon="ℹ"):
    """Информационное сообщение"""
    print(f"{Fore.LIGHTBLUE_EX}{icon}  {Fore.WHITE}{text}{Style.RESET_ALL}")


def print_success(text, icon="✓"):
    """Сообщение об успехе"""
    print(f"{Fore.GREEN}{icon}  {Fore.WHITE}{text}{Style.RESET_ALL}")


def print_error(text, icon="✗"):
    """Сообщение об ошибке"""
    print(f"{Fore.RED}{icon}  {Fore.WHITE}{text}{Style.RESET_ALL}")


def print_warning(text, icon="⚠"):
    """Предупреждение"""
    print(f"{Fore.YELLOW}{icon}  {Fore.WHITE}{text}{Style.RESET_ALL}")


def ask(prompt, default="", secret=False):
    """Запросить ввод с подсказкой"""
    if default:
        full_prompt = f"{Fore.CYAN}❯ {Fore.WHITE}{prompt} {Fore.GREEN}[{default}]{Fore.CYAN}: {Style.RESET_ALL}"
    else:
        full_prompt = f"{Fore.CYAN}❯ {Fore.WHITE}{prompt}{Fore.CYAN}: {Style.RESET_ALL}"
    
    if secret:
        import getpass
        value = getpass.getpass(full_prompt)
    else:
        value = input(full_prompt).strip()
    
    return value if value else default


def ask_yes_no(prompt, default=True):
    """Запросить да/нет"""
    default_str = f"{Fore.GREEN}Y{Fore.WHITE}/{Fore.RED}n" if default else f"{Fore.WHITE}y{Fore.RED}/N"
    
    while True:
        full_prompt = f"{Fore.CYAN}❯ {Fore.WHITE}{prompt} ({default_str}{Fore.CYAN}): {Style.RESET_ALL}"
        value = input(full_prompt).strip().lower()
        
        if not value:
            return default
        
        if value in ['y', 'yes', 'д', 'да', '1']:
            return True
        if value in ['n', 'no', 'н', 'нет', '0']:
            return False
        
        print_error("Введите Y (да) или N (нет)")


def animate_dots(text, duration=1):
    """Анимация точек"""
    print(f"{Fore.CYAN}{text}", end="", flush=True)
    for _ in range(3):
        time.sleep(duration / 3)
        print(".", end="", flush=True)
    print(f" {Fore.GREEN}✓{Style.RESET_ALL}")
    time.sleep(0.3)


# ═══════════════════════════════════════════════════════════
# 🔧 Установка
# ═══════════════════════════════════════════════════════════

def run_setup():
    """Запустить установку"""
    config = configparser.ConfigParser()
    
    # ═══ Приветствие ═══
    print_header()
    
    print(f"{Fore.CYAN}╔{'═' * 70}╗")
    print(f"║{' ' * 70}║")
    print(f"║{' ' * 15}{Fore.WHITE}{Style.BRIGHT}🚀 Мастер быстрой настройки бота 🚀{Fore.CYAN}{Style.NORMAL}{' ' * 18}║")
    print(f"║{' ' * 70}║")
    print(f"║{' ' * 10}{Fore.WHITE}Сейчас мы за 5 простых шагов настроим ваш бот{Fore.CYAN}{' ' * 15}║")
    print(f"║{' ' * 15}{Fore.WHITE}Это займёт всего пару минут!{Fore.CYAN}{' ' * 27}║")
    print(f"║{' ' * 70}║")
    print(f"╚{'═' * 70}╝{Style.RESET_ALL}\n")
    
    print_info("Вы можете в любой момент прервать установку нажав Ctrl+C")
    print_info("Все настройки позже можно изменить через бота\n")
    
    input(f"{Fore.GREEN}{Style.BRIGHT}❯ Нажмите Enter для начала...{Style.RESET_ALL}")
    
    # ═══════════════════════════════════════════════════════════
    # ШАГ 1: Telegram Bot Token
    # ═══════════════════════════════════════════════════════════
    print_header(step=1)
    print_header(step=1)
    
    print_box(
        "📱 ШАГ 1: Telegram Bot Token",
        [
            "Для работы бота нужен токен от @BotFather",
            "",
            "Как получить:",
            "  1️⃣  Напишите @BotFather в Telegram",
            "  2️⃣  Отправьте команду /newbot",
            "  3️⃣  Следуйте инструкциям",
            "  4️⃣  Скопируйте полученный токен"
        ]
    )
    
    while True:
        bot_token = ask("Введите токен бота")
        
        if not bot_token or ':' not in bot_token:
            print_error("Неверный формат токена!")
            print_warning("Токен должен выглядеть так: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n")
            continue
        
        try:
            parts = bot_token.split(':')
            if not parts[0].isdigit() or len(parts[1]) < 20:
                raise ValueError()
            
            animate_dots("Проверка токена")
            print_success("Токен принят!\n")
            break
        except:
            print_error("Неверный формат токена!\n")
    
    config['Telegram'] = {'token': bot_token}
    
    # ═══════════════════════════════════════════════════════════
    # ШАГ 2: Пароль
    # ═══════════════════════════════════════════════════════════
    print_header(step=2)
    
    print_box(
        "🔐 ШАГ 2: Пароль для бота",
        [
            "Пароль защитит бот от несанкционированного доступа",
            "",
            "Требования:",
            "  ✓ Минимум 8 символов",
            "  ✓ Заглавные и строчные буквы (A-z)",
            "  ✓ Хотя бы одна цифра (0-9)"
        ]
    )
    
    while True:
        password = ask("Придумайте надёжный пароль")
        
        if len(password) < 8:
            print_error("Слишком короткий! Минимум 8 символов\n")
            continue
        
        if password.lower() == password or password.upper() == password:
            print_error("Нужны и заглавные, и строчные буквы!\n")
            continue
        
        if not any(c.isdigit() for c in password):
            print_error("Нужна хотя бы одна цифра!\n")
            continue
        
        # Подтверждение пароля
        password_confirm = ask("Повторите пароль")
        
        if password != password_confirm:
            print_error("Пароли не совпадают! Попробуйте снова\n")
            continue
        
        animate_dots("Сохранение пароля")
        print_success("Пароль принят!\n")
        break
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    config['Telegram']['secretkeyhash'] = password_hash
    config['Telegram']['adminIds'] = '[]'
    config['Telegram']['enabled'] = '1'
    
    # ═══════════════════════════════════════════════════════════
    # ШАГ 3: Starvell Session
    # ═══════════════════════════════════════════════════════════
    print_header(step=3)
    
    print_box(
        "🔑 ШАГ 3: Starvell Session Cookie",
        [
            "Session cookie нужен для доступа к API Starvell",
            "",
            "Как получить:",
            "  1️⃣  Откройте starvell.com и войдите в аккаунт",
            "  2️⃣  Нажмите F12 (открыть DevTools)",
            "  3️⃣  Перейдите: Application → Cookies → starvell.com",
            "  4️⃣  Найдите cookie с именем 'session'",
            "  5️⃣  Скопируйте её значение (двойной клик → Ctrl+C)"
        ]
    )
    
    while True:
        session = ask("Введите session cookie")
        
        if not session or len(session) < 10:
            print_error("Cookie не может быть пустой!\n")
            continue
        
        animate_dots("Проверка cookie")
        print_success("Session сохранён!\n")
        break
    
    # User-Agent (опционально)
    print()
    print_info("User-Agent (опционально):")
    print_info("Оставьте пустым для использования стандартного\n")
    
    user_agent = ask("User-Agent (или Enter для пропуска)", "")
    
    if not user_agent:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        print_success("Используется стандартный User-Agent\n")
    else:
        print_success("User-Agent сохранён\n")
    
    config['Starvell'] = {
        'session_cookie': session,
        'user_agent': user_agent,
        'autoRaise': '0',
        'autoDelivery': '0',
        'autoRestore': '0',
        'locale': 'ru',
        'autoTicket': '0',
        'autoTicketInterval': '3600',
        'autoTicketMaxOrders': '5',
        'autoTicketOrderAge': '48'
    }
    

    # ═══════════════════════════════════════════════════════════
    # ШАГ 4: Прокси
    # ═══════════════════════════════════════════════════════════
    print_header(step=4)

    print_box(
        "🔒 ШАГ 4: Прокси (необязательно)",
        [
            "Прокси нужен если Telegram заблокирован в вашей стране.",
            "",
            "Поддерживаемые форматы:",
            "  socks5://ip:port",
            "  socks4://ip:port",
            "  http://ip:port",
            "  socks5://login:password@ip:port",
            "",
            "Оставьте пустым если прокси не нужен."
        ]
    )

    proxy_cfg = {'enabled': '0', 'type': 'socks5', 'ip': '', 'port': '', 'login': '', 'password': ''}
    proxy_pattern = re.compile(
        r'^(socks5|socks4|http)://(?:([^:@]+):([^@]*)@)?([\w\d\.\-]+):(\d{1,5})$',
        re.IGNORECASE
    )

    while True:
        proxy_raw = ask("Прокси (или Enter для пропуска)", "")

        if not proxy_raw:
            print_success("Прокси пропущен. Продолжаем без прокси.\n")
            break

        m = proxy_pattern.match(proxy_raw)
        if not m:
            print_error("Неверный формат! Пример: socks5://1.2.3.4:1080\n")
            continue

        p_type = m.group(1).lower()
        p_login = m.group(2) or ''
        p_password = m.group(3) or ''
        p_ip = m.group(4)
        p_port = m.group(5)

        # Проверка валидности прокси
        print(f"{Fore.CYAN}⟳  Проверка прокси {p_type}://{p_ip}:{p_port} ...", end="", flush=True)
        proxy_ok = False
        try:
            sock = socket.create_connection((p_ip, int(p_port)), timeout=5)
            sock.close()
            proxy_ok = True
        except (socket.timeout, ConnectionRefusedError, OSError):
            proxy_ok = False

        if proxy_ok:
            print(f" {Fore.GREEN}✓ Доступен!{Style.RESET_ALL}")
            print_success(f"Прокси принят: {p_type}://{p_ip}:{p_port}\n")
            proxy_cfg = {
                'enabled': '1',
                'type': p_type,
                'ip': p_ip,
                'port': p_port,
                'login': p_login,
                'password': p_password
            }
            break
        else:
            print(f" {Fore.RED}✗ Недоступен!{Style.RESET_ALL}")
            print_error(f"Не удалось подключиться к {p_ip}:{p_port} (timeout 5 сек)")
            retry = ask_yes_no("Попробовать другой прокси?", default=True)
            if not retry:
                print_warning("Прокси пропущен. Продолжаем без прокси.\n")
                break

    config['Proxy'] = proxy_cfg

    # ═══════════════════════════════════════════════════════════
    # ШАГ 5: Сохранение
    # ═══════════════════════════════════════════════════════════
    print_header(step=5)

    # Дополнительные настройки (по умолчанию)
    config['Notifications'] = {
        'checkInterval': '30',
        'newMessages': '1',
        'newOrders': '1',
        'lotRestore': '1',
        'botStart': '1',
        'lotDeactivate': '1',
        'lotBump': '1',
        'autoTicket': '1'
    }
    
    config['AutoRaise'] = {
        'interval': '3600',
        'gameId': '1',
        'categories': '[10, 11, 12]'
    }
    
    config['AutoUpdate'] = {
        'enabled': '1'
    }
    
    config['KeepAlive'] = {
        'enabled': '1'
    }
    
    config['Storage'] = {
        'dir': 'storage'
    }
    
    config['Blacklist'] = {
        'block_delivery': '1',
        'block_response': '1',
        'block_msg_notifications': '1',
        'block_order_notifications': '1'
    }
    
    config['Other'] = {
        'debug': '0',
        'watermark': '🤖'
    }
    
    config['AutoTicket'] = {
        'ticketType': '1',
        'orderUserTypeId': '2',
        'orderTopicId': '501'
    }
    
    # Сохраняем конфигурацию
    print()
    animate_dots("Сохранение конфигурации")
    
    try:
        config_path = Path("configs/_main.cfg")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print_success("Конфигурация сохранена!\n")
        time.sleep(0.5)
        
    except Exception as e:
        print_error(f"Ошибка сохранения: {e}\n")
        return False
    
    # ═══════════════════════════════════════════════════════════
    # Финал - Успешное завершение
    # ═══════════════════════════════════════════════════════════
    clear()
    print_logo()
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}╔{'═' * 70}╗")
    print(f"║{' ' * 70}║")
    print(f"║{' ' * 20}🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО! 🎉{' ' * 19}║")
    print(f"║{' ' * 70}║")
    print(f"╚{'═' * 70}╝{Style.RESET_ALL}\n")
    
    proxy_summary = f"{proxy_cfg['type']}://{proxy_cfg['ip']}:{proxy_cfg['port']}" if proxy_cfg['enabled'] == '1' else "не настроен"
    print_box(
        "📋 Сводка установки",
        [
            f"✓ Bot Token: {bot_token[:20]}...{bot_token[-10:]}",
            f"✓ Пароль: {'*' * 16}",
            f"✓ Session: {session[:25]}...{session[-15:] if len(session) > 40 else ''}",
            f"✓ Прокси: {proxy_summary}",
            f"✓ Конфигурация сохранена: configs/_main.cfg"
        ],
        color=Fore.GREEN
    )
    
    print_box(
        "🚀 Что дальше?",
        [
            "1️⃣  Запустите бота:",
            f"    {Fore.GREEN}python main.py{Fore.WHITE}",
            "",
            "2️⃣  Откройте бот в Telegram и отправьте:",
            f"    {Fore.GREEN}/start{Fore.WHITE}",
            "",
            "3️⃣  Введите пароль для авторизации:",
            f"    {Fore.GREEN}{password}{Fore.WHITE}",
            "",
            "4️⃣  Готово! Управляйте ботом через меню",
            "",
            f"{Fore.YELLOW}💡 Все настройки можно изменить через бота{Fore.WHITE}"
        ],
        color=Fore.CYAN
    )
    
    print(f"{Fore.CYAN}╔{'═' * 70}╗")
    print(f"║{' ' * 18}{Fore.WHITE}Документация: {Fore.GREEN}docs/PLUGINS_API.md{Fore.CYAN}{' ' * 22}║")
    print(f"║{' ' * 20}{Fore.WHITE}GitHub: {Fore.GREEN}github.com/Hackep1551{Fore.CYAN}{' ' * 21}║")
    print(f"║{' ' * 18}{Fore.WHITE}Telegram: {Fore.GREEN}@kapystus{Fore.CYAN}{' ' * 33}║")
    print(f"╚{'═' * 70}╝{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}{Style.BRIGHT}Спасибо за установку Starvell Cardinal!{Style.RESET_ALL}\n")
    
    return True


# ═══════════════════════════════════════════════════════════
# 🚀 Запуск
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        success = run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Установка прервана пользователем{Style.RESET_ALL}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Fore.RED}Критическая ошибка: {e}{Style.RESET_ALL}\n")
        sys.exit(1)
