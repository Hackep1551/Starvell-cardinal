"""
Пример плагина для Starvell Cardinal Bot

Этот плагин демонстрирует базовую структуру и возможности системы плагинов.
Показывает, как обрабатывать события, работать с API и сохранять данные.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any

# Настройка логирования
logger = logging.getLogger(__name__)

# ============ ОБЯЗАТЕЛЬНЫЕ ПОЛЯ ============

NAME = "Пример плагина"
VERSION = "2.0.0"
DESCRIPTION = "Демонстрационный плагин, показывающий основные возможности системы плагинов"
AUTHOR = "@kapystus"
UUID = "example-plugin-2024-001"  # Уникальный ID плагина,

# Команда для генерации UUID:
# import uuid
# print(str(uuid.uuid4()))


# ============ ОПЦИОНАЛЬНЫЕ ПОЛЯ ============

SETTINGS_PAGE = False  # Есть ли у плагина страница настроек в Telegram боте

# ============ ХРАНИЛИЩЕ ДАННЫХ ============

PLUGIN_DATA_FILE = Path("storage/example_plugin_data.json")

def save_data(data: dict):
    """Сохранить данные плагина"""
    PLUGIN_DATA_FILE.parent.mkdir(exist_ok=True)
    with open(PLUGIN_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data() -> dict:
    """Загрузить данные плагина"""
    if not PLUGIN_DATA_FILE.exists():
        return {"orders": [], "messages": []}
    with open(PLUGIN_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# ============ ОБРАБОТЧИКИ СОБЫТИЙ ============

async def on_init(bot, starvell, db, plugin_manager):
    """
    Вызывается при инициализации бота (после создания всех сервисов)
    
    Args:
        bot: Экземпляр aiogram.Bot
        starvell: StarvellService - доступ к API Starvell.com
        db: Database - хранилище данных
        plugin_manager: PluginManager - управление плагинами
    """
    logger.info(f"✅ {NAME} v{VERSION} инициализирован!")
    logger.info(f"📌 UUID: {UUID}")
    logger.info(f"� Автор: {AUTHOR}")
    
    # Пример: загрузить данные
    data = load_data()
    logger.info(f"📂 Загружено заказов: {len(data.get('orders', []))}")


async def on_start(bot, starvell, db, plugin_manager):
    """
    Вызывается при запуске бота
    
    Args:
        bot: Экземпляр aiogram.Bot
        starvell: StarvellService
        db: Database
        plugin_manager: PluginManager
    """
    logger.info(f"▶️ {NAME} запущен!")


async def on_stop(bot, starvell, db, plugin_manager):
    """
    Вызывается при остановке бота
    
    Args:
        bot: Экземпляр aiogram.Bot
        starvell: StarvellService
        db: Database
        plugin_manager: PluginManager
    """
    logger.info(f"⏹️ {NAME} остановлен!")


async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    """
    Вызывается при получении нового заказа
    
    Args:
        order_data (dict): Данные заказа
            {
                'id': str,              # UUID заказа
                'buyer': str,           # Имя покупателя
                'amount': float,        # Сумма в рублях
                'lot_name': str,        # Название лота
                'lot_description': str, # Описание лота
                'status': str,          # Статус (CREATED, COMPLETED, etc.)
                'chat_id': str          # UUID чата (может быть пусто)
            }
        starvell_service: StarvellService для работы с API
    
    Пример order_data:
        {
            'id': '019b97fa-497b-3dd2-a041-da54f9378d8e',
            'buyer': 'Hackep',
            'amount': 1.08,
            'lot_name': 'Товар',
            'lot_description': 'Описание товара',
            'status': 'CREATED',
            'chat_id': '019b8386-1e8f-f31d-9e66-b05331f70af6'
        }
    """
    logger.info(f"📦 Новый заказ: {order_data.get('id')}")
    logger.info(f"   Покупатель: {order_data.get('buyer')}")
    logger.info(f"   Сумма: {order_data.get('amount')}₽")
    
    # Сохраняем заказ в данные плагина
    data = load_data()
    data['orders'].append({
        'order_id': order_data.get('id'),
        'buyer': order_data.get('buyer'),
        'amount': order_data.get('amount')
    })
    save_data(data)
    
    # Отправляем приветствие покупателю
    if starvell_service and order_data.get('chat_id'):
        try:
            await starvell_service.send_message(
                order_data['chat_id'],
                f"👋 Здравствуйте, {order_data['buyer']}!\n\n"
                f"Спасибо за заказ: {order_data['lot_name']}\n"
                f"Мы скоро свяжемся с вами!"
            )
            logger.info(f"✅ Отправлено приветствие покупателю")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")


async def on_new_message(message_data: dict, starvell_service=None, **kwargs):
    """
    Вызывается при получении нового сообщения
    
    Args:
        message_data (dict): Данные сообщения
            {
                'chat_id': str,      # UUID чата
                'author': str,       # ID автора (buyerId как строка)
                'content': str,      # Текст сообщения
                'message_id': str    # UUID сообщения
            }
        starvell_service: StarvellService для работы с API
    
    Пример message_data:
        {
            'chat_id': '019b8386-1e8f-f31d-9e66-b05331f70af6',
            'author': '142989',
            'content': 'Привет!',
            'message_id': '019b9803-0ef6-eb89-eb81-0e72b7c2ff42'
        }
    
    Важно: 'author' содержит ID покупателя (число), а не имя!
    """
    logger.debug(f"💬 Сообщение от {message_data.get('author')}")
    
    content = message_data.get('content', '').lower()
    chat_id = message_data.get('chat_id')
    
    # Пример: автоответ на определенные слова
    if ('помощь' in content or 'help' in content) and starvell_service and chat_id:
        try:
            await starvell_service.send_message(
                chat_id,
                "ℹ️ Для помощи свяжитесь с нами: @support"
            )
            logger.info(f"✅ Отправлен автоответ на запрос помощи")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки автоответа: {e}")
    
    # Сохраняем сообщение
    data = load_data()
    data['messages'].append({
        'author': message_data.get('author'),
        'content': message_data.get('content')[:50]  # Первые 50 символов
    })
    save_data(data)


def on_delete():
    """
    Вызывается перед удалением плагина
    Используйте для очистки ресурсов, файлов, и т.д.
    """
    logger.info(f"🗑️ {NAME} удаляется...")
    
    # Пример: удалить файл данных
    if PLUGIN_DATA_FILE.exists():
        PLUGIN_DATA_FILE.unlink()
        logger.info(f"🗑️ Файл данных удален")


# ============ ПРИВЯЗКА К СОБЫТИЯМ ============

BIND_TO_INIT = [on_init]
BIND_TO_START = [on_start]
BIND_TO_STOP = [on_stop]
BIND_TO_NEW_ORDER = [on_new_order]
BIND_TO_NEW_MESSAGE = [on_new_message]
BIND_TO_DELETE = [on_delete]  # Может быть функцией или списком


# ============ ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ============

"""
📚 Доступные события для привязки:

1. BIND_TO_PRE_INIT - До инициализации бота (список функций)
2. BIND_TO_INIT - Инициализация бота (список функций)
3. BIND_TO_START - Запуск бота (список функций)
4. BIND_TO_STOP - Остановка бота (список функций)
5. BIND_TO_NEW_ORDER - Новый заказ (список функций)
6. BIND_TO_NEW_MESSAGE - Новое сообщение (список функций)
7. BIND_TO_DELETE - Удаление плагина (функция или список)

📋 Параметры обработчиков:

BIND_TO_INIT, BIND_TO_START, BIND_TO_STOP:
    async def handler(bot, starvell, db, plugin_manager):
        ...

BIND_TO_NEW_ORDER:
    async def handler(order_data: dict, starvell_service=None, **kwargs):
        ...

BIND_TO_NEW_MESSAGE:
    async def handler(message_data: dict, starvell_service=None, **kwargs):
        ...

BIND_TO_DELETE:
    def handler():
        ...

🔧 StarvellService методы:

- await starvell_service.send_message(chat_id, content)
- await starvell_service.get_order_details(order_id)
- await starvell_service.get_orders()
- await starvell_service.refund_order(order_id)
- await starvell_service.find_chat_by_user_id(user_id)

💡 Полезные советы:

1. Всегда используйте async/await для обработчиков событий
2. Проверяйте starvell_service перед использованием
3. Оборачивайте код в try/except
4. Используйте logger для логов
5. Генерируйте уникальный UUID:
   
   import uuid
   print(str(uuid.uuid4()))

6. Чтобы временно отключить плагин без удаления,
   добавьте # noplug в первую строку файла:
   
   # noplug
   # Этот плагин отключён
   
   NAME = "Мой плагин"
   ...

📖 Документация:

- docs/QUICK_START.md - Быстрый старт
- docs/PLUGINS_API.md - Полное API
- docs/API_REFERENCE.md - Справочник методов
- plugins/AutoSmm.py - Пример сложного плагина
"""
