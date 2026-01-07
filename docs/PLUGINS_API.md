# 🔌 Документация по плагинам Starvell Cardinal

## Введение

Система плагинов Starvell Cardinal позволяет расширять функциональность бота без изменения основного кода. Плагины могут обрабатывать события, добавлять команды и выполнять автоматические действия.

## Структура плагина

Плагин - это обычный Python файл (.py) в папке `plugins/` с определёнными переменными и функциями.

### Минимальный плагин

```python
"""
Пример плагина
"""

# === МЕТАДАННЫЕ ===
NAME = "Мой плагин"
VERSION = "1.0.0"
DESCRIPTION = "Описание плагина"
AUTHOR = "Ваше имя"
UUID = "unique-plugin-id-12345"  # Уникальный ID

# === ФУНКЦИИ-ОБРАБОТЧИКИ ===
def on_init():
    """Вызывается при загрузке плагина"""
    print(f"Плагин {NAME} загружен!")

# === ПРИВЯЗКА К СОБЫТИЯМ ===
BIND_TO_PRE_INIT = [on_init]
```

## Обязательные переменные

| Переменная | Тип | Описание |
|-----------|------|----------|
| `NAME` | str | Название плагина |
| `VERSION` | str | Версия плагина |
| `DESCRIPTION` | str | Описание плагина |
| `AUTHOR` | str | Автор плагина |
| `UUID` | str | Уникальный ID плагина |
## События плагинов

### Жизненный цикл

#### `BIND_TO_PRE_INIT`
Вызывается **перед** инициализацией бота.

```python
def on_pre_init():
    print("Бот ещё не запущен")

BIND_TO_PRE_INIT = [on_pre_init]
```

#### `BIND_TO_INIT`
Вызывается **после** инициализации бота.

```python
async def on_init(bot, starvell, db, plugin_manager):
    """
    Args:
        bot: Объект бота Aiogram (Bot)
        starvell: StarvellService для работы с API
        db: Database для работы с хранилищем
        plugin_manager: PluginManager для управления плагинами
    """
    print("Бот запущен!")
    
    # Пример: получить список заказов
    orders = await starvell.get_orders()
    print(f"Активных заказов: {len(orders)}")

BIND_TO_INIT = [on_init]
```

#### `BIND_TO_DELETE`
Вызывается при **удалении** плагина.

```python
def on_delete():
    print("Плагин удаляется...")

BIND_TO_DELETE = [on_delete]
```

### События бота

#### `BIND_TO_NEW_MESSAGE`
Вызывается при получении нового сообщения.

```python
async def on_new_message(message_data: dict, starvell_service=None, *args, **kwargs):
    """
    Args:
        message_data (dict): Данные сообщения
        starvell_service (StarvellService): Сервис для работы с API
    
    Структура message_data:
    {
        'chat_id': str,       # ID чата (UUID)
        'author': str,        # ID автора сообщения (числовой, как строка)
        'content': str,       # Текст сообщения
        'message_id': str     # ID сообщения (UUID)
    }
    
    Пример:
    {
        'chat_id': '019b8386-1e8f-f31d-9e66-b05331f70af6',
        'author': '142989',
        'content': 'https://t.me/channel/123',
        'message_id': '019b9803-0ef6-eb89-eb81-0e72b7c2ff42'
    }
    """
    print(f"Новое сообщение от {message_data['author']}: {message_data['content']}")
    
    # Ответить на сообщение
    if starvell_service and message_data.get('chat_id'):
        await starvell_service.send_message(
            message_data['chat_id'],
            "Спасибо за сообщение!"
        )

BIND_TO_NEW_MESSAGE = [on_new_message]
```

#### `BIND_TO_NEW_ORDER`
Вызывается при получении нового заказа.

```python
async def on_new_order(order_data: dict, starvell_service=None, *args, **kwargs):
    """
    Args:
        order_data (dict): Данные заказа
        starvell_service (StarvellService): Сервис для работы с API
    
    Структура order_data:
    {
        'id': str,                    # ID заказа (UUID)
        'buyer': str,                 # Имя покупателя
        'amount': float,              # Сумма заказа в рублях
        'lot_name': str,              # Название лота
        'lot_description': str,       # Описание лота
        'status': str,                # Статус заказа (CREATED, COMPLETED, etc.)
        'chat_id': str                # ID чата с покупателем (пусто если не найден)
    }
    
    Пример:
    {
        'id': '019b97fa-497b-3dd2-a041-da54f9378d8e',
        'buyer': 'Hackep',
        'amount': 1.08,
        'lot_name': 'АВТОНАКРУТКА ПРОСМОТРОВ TELEGRAM',
        'lot_description': '💜 Минимальный заказ: 50...',
        'status': 'CREATED',
        'chat_id': '019b8386-1e8f-f31d-9e66-b05331f70af6'
    }
    """
    print(f"📦 Новый заказ #{order_data['id']} от {order_data['buyer']}")
    
    # Отправить сообщение покупателю
    if starvell_service and order_data.get('chat_id'):
        await starvell_service.send_message(
            order_data['chat_id'],
            f"Здравствуйте! Спасибо за заказ {order_data['lot_name']}"
        )

BIND_TO_NEW_ORDER = [on_new_order]
```

## Команды плагинов

Плагины могут добавлять собственные команды в бота.

### Создание команды

```python
from aiogram import types
from aiogram.filters import Command

async def my_command(message: types.Message):
    """Обработчик команды /mycommand"""
    await message.answer("Привет из плагина!")

# Привязка команды
COMMANDS = {
    "mycommand": {
        "handler": my_command,
        "description": "Моя команда",
        "filters": [Command("mycommand")]
    }
}
```

### Команды с callback

```python
from aiogram import types, F

async def button_callback(callback: types.CallbackQuery):
    """Обработчик нажатия на кнопку"""
    await callback.answer("Кнопка нажата!")
    await callback.message.answer("Вы нажали кнопку")

# Привязка callback
CALLBACKS = {
    "my_button": {
        "handler": button_callback,
        "filter": F.data == "my_plugin_button"
    }
}
```

## Настройки плагина

Плагины могут иметь собственные настройки.

```python
# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "enabled": True,
    "interval": 60,
    "max_retries": 3
}

# Функция для получения настроек
def get_settings():
    """Получить настройки плагина"""
    # Здесь можно загрузить настройки из файла
    return DEFAULT_SETTINGS

# Функция для сохранения настроек
def save_settings(settings):
    """Сохранить настройки плагина"""
    # Здесь можно сохранить настройки в файл
    pass
```

## Доступ к API бота

Плагины могут использовать API Starvell через параметр `starvell_service` в обработчиках событий.

### StarvellService API

Объект `StarvellService` предоставляет методы для работы с платформой Starvell.com:

#### `send_message(chat_id: str, content: str) -> dict`

Отправить сообщение в чат.

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    if starvell_service and order_data.get('chat_id'):
        result = await starvell_service.send_message(
            chat_id=order_data['chat_id'],
            content="Здравствуйте! Спасибо за заказ!"
        )
        # result - dict с ответом от API
```

**Возвращает:**
```python
{
    "success": True,  # или False при ошибке
    # ... другие поля от API
}
```

#### `get_order_details(order_id: str) -> dict`

Получить детальную информацию о заказе.

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    if starvell_service:
        details = await starvell_service.get_order_details(order_data['id'])
```

**Возвращает:**
```python
{
    "pageProps": {
        "order": {
            "id": "019b97fa-497b-3dd2-a041-da54f9378d8e",
            "status": "CREATED",
            "basePrice": 100,          # Цена в копейках
            "totalPrice": 108,         # Итого в копейках (с комиссией)
            "buyerId": 142989,         # ID покупателя (число)
            "sellerId": 7970,          # ID продавца (число)
            "offerId": 141378,         # ID лота
            "quantity": 1000,          # Количество единиц товара
            "createdAt": "2026-01-07T10:22:01.068Z",
            "buyer": {
                "id": 142989,
                "username": "Hackep",
                "isOnline": True,
                "avatar": "uuid-here",
                # ... другие поля профиля
            },
            "seller": {
                "id": 7970,
                "username": "Kirito",
                # ... другие поля профиля
            },
            "offerDetails": {
                "game": {"id": 14, "name": "Telegram"},
                "category": {"id": 175, "name": "Услуги"},
                "descriptions": {
                    "rus": {
                        "description": "Полное описание...",
                        "briefDescription": "Краткое описание"
                    }
                },
                # ... другие поля лота
            }
        },
        "chat": {
            "id": "019b8386-1e8f-f31d-9e66-b05331f70af6",  # UUID чата!
            # ... другие поля чата
        },
        "messages": [],  # Массив сообщений
        # ... другие поля
    },
    "__N_SSP": True
}
```

**Важно:** `chat.id` находится в `pageProps.chat.id`, а не в `pageProps.order`!

#### `get_orders() -> list`

Получить список заказов.

```python
async def on_init(bot, starvell, db, plugin_manager):
    orders = await starvell.get_orders()
    for order in orders:
        print(f"Заказ: {order['id']}")
```

**Возвращает:**
```python
[
    {
        "id": "order-uuid",
        "status": "CREATED",
        "totalPrice": 108,
        "buyer": {...},
        "seller": {...},
        # ... другие поля
    },
    # ... остальные заказы
]
```

#### `refund_order(order_id: str) -> dict`

Вернуть деньги за заказ.

```python
async def handle_refund(order_id: str, starvell_service):
    result = await starvell_service.refund_order(order_id)
    # result содержит результат операции
```

#### `find_chat_by_user_id(user_id: str) -> str | None`

Найти ID чата с конкретным пользователем по его ID.

```python
async def find_user_chat(starvell_service):
    chat_id = await starvell_service.find_chat_by_user_id("142989")
    if chat_id:
        await starvell_service.send_message(chat_id, "Привет!")
```

**Возвращает:** UUID чата (строка) или `None` если чат не найден.

### Примеры использования

#### Отправка приветствия при новом заказе

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    """Отправить приветствие покупателю"""
    if not starvell_service:
        return
    
    # Если chat_id уже есть в order_data
    if order_data.get('chat_id'):
        await starvell_service.send_message(
            order_data['chat_id'],
            f"👋 Здравствуйте!\n\n"
            f"📦 Спасибо за заказ: {order_data['lot_name']}\n"
            f"💰 Сумма: {order_data['amount']}₽"
        )
    else:
        # Получить детали заказа, чтобы найти chat_id
        details = await starvell_service.get_order_details(order_data['id'])
        page_props = details.get("pageProps", {})
        chat_data = page_props.get("chat", {})
        chat_id = chat_data.get("id")
        
        if chat_id:
            await starvell_service.send_message(chat_id, "Привет!")
```

#### Обработка сообщений с автоответом

```python
async def on_new_message(message_data: dict, starvell_service=None, **kwargs):
    """Автоматически ответить на сообщение"""
    if not starvell_service:
        return
    
    content = message_data.get('content', '').lower()
    chat_id = message_data.get('chat_id')
    
    if 'помощь' in content or 'help' in content:
        await starvell_service.send_message(
            chat_id,
            "ℹ️ Для помощи напишите администратору @support"
        )
```

## Логирование

Используйте стандартный модуль `logging` для вывода логов.

```python
import logging

logger = logging.getLogger(__name__)

def on_init():
    logger.info("✅ Плагин инициализирован")
    logger.debug("Отладочная информация")
    logger.warning("⚠️ Предупреждение")
    logger.error("❌ Ошибка")

BIND_TO_INIT = [on_init]
```

## Пример полного плагина

```python
"""
Плагин автоответчика
Автоматически отвечает на сообщения с определённым текстом
"""

import logging

logger = logging.getLogger(__name__)

# === МЕТАДАННЫЕ ===
NAME = "Автоответчик"
VERSION = "1.0.0"
DESCRIPTION = "Автоматически отвечает на сообщения"
AUTHOR = "@kapystus"
UUID = "auto-reply-plugin-001"
# === НАСТРОЙКИ ===
TRIGGER_WORDS = ["помощь", "help", "info"]
AUTO_REPLY = "Здравствуйте! Я сейчас не могу ответить. Напишите позже."

# === ОБРАБОТЧИКИ ===
def on_init():
    logger.info(f"✅ {NAME} v{VERSION} загружен")

async def on_new_message(message_data, starvell_service=None, *args):
    """Проверяем сообщение и отвечаем если нужно"""
    content = message_data.get('content', '').lower()
    
    # Проверяем триггерные слова
    if any(word in content for word in TRIGGER_WORDS):
        chat_id = message_data.get('chat_id')
        
        if starvell_service and chat_id:
            try:
                await starvell_service.send_message(chat_id, AUTO_REPLY)
                logger.info(f"📤 Отправлен автоответ в чат {chat_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки автоответа: {e}")

# === ПРИВЯЗКИ ===
BIND_TO_INIT = [on_init]
BIND_TO_NEW_MESSAGE = [on_new_message]
```

## Установка плагина

1. Скопируйте `.py` файл плагина в папку `plugins/`
2. Перезапустите бота или используйте команду `/start`
3. Плагин автоматически загрузится




## Примеры плагинов

Смотрите `plugins/example_plugin.py` и `plugins/AutoSmm.py` для примеров реализации всех возможностей.

## Полезные советы

### 1. Всегда используйте async/await

Все обработчики событий должны быть асинхронными:

```python
# ✅ Правильно
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    await starvell_service.send_message(...)

# ❌ Неправильно
def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    # Синхронная функция не может использовать await
    pass
```

### 2. Проверяйте наличие starvell_service

Всегда проверяйте, что `starvell_service` передан:

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    if not starvell_service:
        logger.warning("starvell_service не передан!")
        return
    
    # Теперь безопасно использовать
    await starvell_service.send_message(...)
```

### 3. Обрабатывайте исключения

Всегда оборачивайте код в try/except:

```python
async def on_new_message(message_data: dict, starvell_service=None, **kwargs):
    try:
        chat_id = message_data.get('chat_id')
        if starvell_service and chat_id:
            await starvell_service.send_message(chat_id, "Привет!")
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
```

### 4. Используйте логирование

Логируйте важные события и ошибки:

```python
import logging

logger = logging.getLogger(__name__)

async def on_new_order(order_data: dict, **kwargs):
    logger.info(f"📦 Получен заказ {order_data['id']}")
    logger.debug(f"Детали: {order_data}")  # Только в режиме отладки
```

### 5. Сохраняйте данные правильно

Используйте JSON для хранения данных плагина:

```python
import json
from pathlib import Path

PLUGIN_DATA_FILE = Path("storage/my_plugin_data.json")

def save_data(data: dict):
    """Сохранить данные плагина"""
    PLUGIN_DATA_FILE.parent.mkdir(exist_ok=True)
    with open(PLUGIN_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data() -> dict:
    """Загрузить данные плагина"""
    if not PLUGIN_DATA_FILE.exists():
        return {}
    with open(PLUGIN_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
```

## FAQ

### Как получить chat_id для отправки сообщений?

**Вариант 1:** Использовать `order_data['chat_id']` (если уже есть):

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    chat_id = order_data.get('chat_id')
    if chat_id and starvell_service:
        await starvell_service.send_message(chat_id, "Привет!")
```

**Вариант 2:** Получить из деталей заказа:

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    if not starvell_service:
        return
    
    # Получаем полные детали заказа
    details = await starvell_service.get_order_details(order_data['id'])
    page_props = details.get("pageProps", {})
    
    # chat находится в pageProps.chat, а НЕ в pageProps.order!
    chat_data = page_props.get("chat", {})
    chat_id = chat_data.get("id")
    
    if chat_id:
        await starvell_service.send_message(chat_id, "Сообщение")
```

### Почему message_data['author'] это число, а не имя?

`author` содержит **ID покупателя** (buyerId), а не имя. Чтобы получить имя:

**Вариант 1:** Сохранить соответствие при создании заказа:

```python
# В on_new_order сохраняем buyer_id
order_info = {
    'buyer': order_data['buyer'],      # "Hackep"
    'buyer_id': str(buyer_id)          # "142989"
}

# В on_new_message ищем по author
author = message_data['author']  # "142989"
# Находим заказ где buyer_id == author
```

**Вариант 2:** Получить из деталей заказа:

```python
details = await starvell_service.get_order_details(order_id)
buyer = details["pageProps"]["order"]["buyer"]
buyer_name = buyer["username"]  # "Hackep"
buyer_id = buyer["id"]          # 142989
```

### Как обрабатывать количество товара?

Количество хранится в `order.quantity` в деталях заказа:

```python
async def on_new_order(order_data: dict, starvell_service=None, **kwargs):
    # Получаем детали
    details = await starvell_service.get_order_details(order_data['id'])
    order_info = details["pageProps"]["order"]
    
    quantity = order_info.get("quantity", 1)  # Количество единиц
    
    # Если в описании есть множитель (например #Quan:10)
    import re
    lot_description = order_data['lot_description']
    match_quan = re.search(r'#Quan:\s*(\d+)', lot_description)
    quan_per_unit = int(match_quan.group(1)) if match_quan else 1
    
    # Итоговое количество
    final_quantity = quantity * quan_per_unit
    print(f"Заказано: {quantity} × {quan_per_unit} = {final_quantity}")
```

### Как отключить плагин программно?

Используйте `plugin_manager`:

```python
async def on_init(bot, starvell, db, plugin_manager):
    # Отключить себя
    plugin_manager.disable_plugin("my-plugin-uuid")
    
    # Отключить другой плагин
    plugin_manager.disable_plugin("other-plugin-uuid")
```

## Поддержка

- GitHub: <https://github.com/Hackep1551/Starvell-cardinal>
- Telegram: @kapystus
---

**Starvell Cardinal** - мощная система автоматизации для Starvell.com
