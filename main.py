"""
Starvell Bot - главный файл запуска
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from version import VERSION


# Цветной форматтер для логов
class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для логов с минималистичным оформлением"""
    
    # ANSI коды цветов
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Сокращения уровней
    LEVEL_ABBR = {
        'DEBUG': 'D',
        'INFO': 'I',
        'WARNING': 'W',
        'ERROR': 'E',
        'CRITICAL': 'C'
    }
    
    def format(self, record):
        # Цвет для уровня
        levelname_color = self.COLORS.get(record.levelname, self.RESET)
        
        # Форматируем время
        time_str = self.formatTime(record, '%H:%M:%S')
        
        # Сокращённый уровень
        level_abbr = self.LEVEL_ABBR.get(record.levelname, '?')
        level_str = f"{levelname_color}{self.BOLD}[{level_abbr}]{self.RESET}"
        
        # Сообщение
        message = record.getMessage()
        
        return f"{time_str} {level_str} {message}"


# Создаём папку для логов если её нет
from pathlib import Path
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Настройка цветного логирования
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter())

file_handler = logging.FileHandler('logs/bot.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

# Отключаем verbose логи aiogram
logging.getLogger('aiogram.event').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Логотип
LOGO = r"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     ███████╗████████╗ █████╗ ██████╗ ██╗   ██╗███████╗██╗     ██╗    ║
║     ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║   ██║██╔════╝██║     ██║    ║
║     ███████╗   ██║   ███████║██████╔╝██║   ██║█████╗  ██║     ██║    ║
║     ╚════██║   ██║   ██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  ██║     ██║    ║
║     ███████║   ██║   ██║  ██║██║  ██║ ╚████╔╝ ███████╗███████╗███████╗
║     ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝╚══════╝
║                                                                      ║
║        ╔═══════════════════════════════════════════════════╗         ║
║        ║  🔥  S T A R V E L L   -    C A R D I N A L   🔥  ║         ║
║        ╚═══════════════════════════════════════════════════╝         ║
║                                                                      ║
║                 ⚡ Telegram Bot v{:<16} ⚡                 ║
║                                                                      ║
║        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━           ║
║            🚀 Бот для Starvell.com | By kapystus 🚀                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

def print_logo():
    """Вывести логотип"""
    print("\n" + LOGO.format(VERSION))
    print("By @kapystus")
    print("GitHub: github.com/Hackep1551/Starvell-cardinal")
    print("Telegram: t.me/Starvell_cardinal")
    print()

def set_console_title(title: str):
    """Установить заголовок консоли"""
    if sys.platform == "win32":
        os.system(f"title {title}")
    else:
        sys.stdout.write(f"\x1b]2;{title}\x07")

def create_folders():
    """Создать необходимые папки"""
    folders = [
        "configs",
        "storage",
        "storage/cache",
        "storage/settings",
        "storage/stats",
        "logs"
    ]
    
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)

def check_first_run() -> bool:
    """Проверить, первый ли это запуск"""
    config_path = Path("configs/_main.cfg")
    return not config_path.exists()

async def main():
    """Главная функция"""
    if not Path("version.py").exists():
        logger.error("=" * 70)
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Файл version.py не найден!")
        logger.error("Бот не может запуститься без файла version.py")
        logger.error("=" * 70)
        time.sleep(5)
        sys.exit(1)
    
    # Устанавливаем заголовок
    set_console_title(f"Starvell Bot v{VERSION}")
    
    # Переходим в директорию скрипта
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(__file__))
    
    # Создаём папки
    create_folders()
    
    # Выводим логотип
    print_logo()
    
    # Проверяем первый запуск
    if check_first_run():
        logger.info("=" * 70)
        logger.info("ПЕРВЫЙ ЗАПУСК - ТРЕБУЕТСЯ НАСТРОЙКА")
        logger.info("=" * 70)
        
        # Импортируем и запускаем первоначальную установку
        try:
            from first_setup import run_setup
            
            logger.info("Запуск мастера первоначальной установки...\n")
            time.sleep(1)
            
            if not run_setup():
                logger.error("Установка прервана или завершилась с ошибкой")
                logger.info("Для повторной установки просто запустите бота снова")
                time.sleep(3)
                return
                
            logger.info("УСТАНОВКА ЗАВЕРШЕНА!")
            logger.info("Перезапускаю бота...\n")
            time.sleep(2)
            
        except KeyboardInterrupt:
            logger.info("\nУстановка прервана пользователем")
            return
        except Exception as e:
            logger.error(f"Ошибка при первоначальной установке: {e}", exc_info=True)
            return
    
    # Запускаем основной бот
    try:
        logger.info("ЗАПУСК БОТА")
        
        # Импортируем основной модуль бота
        from bot.bot_core import main as bot_main
        
        # Запускаем бота
        await bot_main()
        
    except KeyboardInterrupt:
        logger.info("\nПолучен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        time.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Завершение работы...")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}", exc_info=True)
        time.sleep(5)
