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
PLUGIN_NAME = "Мой плагин"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Описание плагина"
PLUGIN_AUTHOR = "Ваше имя"
PLUGIN_UUID = "unique-plugin-id-12345"  # Уникальный ID

# === ФУНКЦИИ-ОБРАБОТЧИКИ ===
def on_init():
    """Вызывается при загрузке плагина"""
    print(f"Плагин {PLUGIN_NAME} загружен!")

# === ПРИВЯЗКА К СОБЫТИЯМ ===
BIND_TO_PRE_INIT = [on_init]
```

## Обязательные переменные

| Переменная | Тип | Описание |
|-----------|------|----------|
| `PLUGIN_NAME` | str | Название плагина |
| `PLUGIN_VERSION` | str | Версия плагина |
| `PLUGIN_DESCRIPTION` | str | Описание плагина |
| `PLUGIN_AUTHOR` | str | Автор плагина |
| `PLUGIN_UUID` | str | Уникальный ID плагина |

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
def on_init():
    print("Бот запущен!")

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
def on_new_message(message_data, *args):
    """
    message_data: dict с данными сообщения
    {
        'chat_id': str,
        'author': str,
        'content': str,
        'message_id': str
    }
    """
    print(f"Новое сообщение от {message_data['author']}: {message_data['content']}")

BIND_TO_NEW_MESSAGE = [on_new_message]
```

#### `BIND_TO_NEW_ORDER`
Вызывается при получении нового заказа.

```python
def on_new_order(order_data, *args):
    """
    order_data: dict с данными заказа
    {
        'id': str,
        'buyer': str,
        'amount': float,
        'lot_name': str,
        'status': str
    }
    """
    print(f"📦 Новый заказ #{order_data['id']} от {order_data['buyer']}")

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

Плагины могут использовать API Starvell через переданные аргументы.

```python
def on_new_order(order_data, starvell_service=None, *args):
    """
    starvell_service: StarvellService - доступ к API
    """
    if starvell_service:
        # Пример: отправить сообщение
        # await starvell_service.send_message(chat_id, "текст")
        pass

BIND_TO_NEW_ORDER = [on_new_order]
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
PLUGIN_NAME = "Автоответчик"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Автоматически отвечает на сообщения"
PLUGIN_AUTHOR = "@kapystus"
PLUGIN_UUID = "auto-reply-plugin-001"

# === НАСТРОЙКИ ===
TRIGGER_WORDS = ["помощь", "help", "info"]
AUTO_REPLY = "Здравствуйте! Я сейчас не могу ответить. Напишите позже."

# === ОБРАБОТЧИКИ ===
def on_init():
    logger.info(f"✅ {PLUGIN_NAME} v{PLUGIN_VERSION} загружен")

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

Смотрите `plugins/example_plugin.py` для примера реализации всех возможностей.

## Поддержка

- GitHub: https://github.com/Hackep1551/Starvell-cardinal
- Telegram: @kapystus
- Документация: https://github.com/Hackep1551/Starvell-cardinal/wiki

---

**Starvell Cardinal** - мощная система автоматизации для Starvell.com
