"""
Клавиатуры для бота
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# === База данных ===
class CBT:
    """Типы callback кнопок"""
    # Главное меню
    MAIN = "main"
    GLOBAL_SWITCHES = "global"
    NOTIFICATIONS = "notif"
    PLUGINS = "plugins"
    AUTO_DELIVERY = "autodelivery"
    BLACKLIST = "blacklist"
    
    # Язык
    
    # Переключатели
    SWITCH_AUTO_BUMP = "switch:auto_bump"
    SWITCH_AUTO_DELIVERY = "switch:auto_delivery"
    SWITCH_AUTO_RESTORE = "switch:auto_restore"
    SWITCH_AUTO_UPDATE = "switch:auto_update"
    SWITCH_AUTO_INSTALL = "switch:auto_install"
    
    # Уведомления
    NOTIF_MESSAGES = "notif:messages"
    NOTIF_ORDERS = "notif:orders"
    NOTIF_RESTORE = "notif:restore"
    NOTIF_START = "notif:start"
    NOTIF_DEACTIVATE = "notif:deactivate"
    NOTIF_BUMP = "notif:bump"
    
    # Автовыдача
    AD_LOTS_LIST = "ad_lots"
    EDIT_AD_LOT = "ad_edit"
    SWITCH_LOT_SETTING = "ad_switch"
    
    # Чёрный список
    BL_ADD_USER = "bl_add"
    BL_REMOVE_USER = "bl_remove"
    BL_TOGGLE_DELIVERY = "bl:delivery"
    BL_TOGGLE_RESPONSE = "bl:response"
    BL_TOGGLE_MSG_NOTIF = "bl:msg_notif"
    BL_TOGGLE_ORDER_NOTIF = "bl:order_notif"
    
    # Плагины
    PLUGINS_LIST = "plugins_list"
    EDIT_PLUGIN = "edit_plugin"
    TOGGLE_PLUGIN = "toggle_plugin"
    DELETE_PLUGIN = "delete_plugin"
    CONFIRM_DELETE_PLUGIN = "confirm_delete_plugin"
    CANCEL_DELETE_PLUGIN = "cancel_delete_plugin"
    UPLOAD_PLUGIN = "upload_plugin"
    PLUGIN_COMMANDS = "plugin_commands"
    PLUGIN_SETTINGS = "plugin_settings"


def bool_to_emoji(value: bool) -> str:
    """Преобразовать bool в эмодзи"""
    return "✅" if value else "❌"


def get_main_menu(update_available: bool = False) -> InlineKeyboardMarkup:
    """Главное меню (автоматизация и настройки)"""
    keyboard = []
    
    # Если доступно обновление - показываем его первой кнопкой
    if update_available:
        keyboard.append([
            InlineKeyboardButton(
                text="🔥 Доступно обновление!",
                callback_data="update_now"
            )
        ])
    
    keyboard.extend([
        [
            InlineKeyboardButton(
                text="⚙️ Глобальные переключатели",
                callback_data=CBT.GLOBAL_SWITCHES
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔔 Настройки уведомлений",
                callback_data=CBT.NOTIFICATIONS
            ),
        ],
        [
            InlineKeyboardButton(
                text="📦 Автовыдача (в бетатесте)",
                callback_data=CBT.AUTO_DELIVERY
            ),
        ],
        [
            InlineKeyboardButton(
                text="🚫 Чёрный список (в разработке)",
                callback_data=CBT.BLACKLIST
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔌 Плагины",
                callback_data=CBT.PLUGINS
            ),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_global_switches_menu(auto_bump: bool, auto_delivery: bool, auto_restore: bool, auto_update: bool, auto_install: bool = False) -> InlineKeyboardMarkup:
    """Меню глобальных переключателей"""
    
    def switch_text(name: str, enabled: bool) -> str:
        emoji = bool_to_emoji(enabled)
        return f"{emoji} {name}"
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=switch_text("Авто-поднятие", auto_bump),
                callback_data=CBT.SWITCH_AUTO_BUMP
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Авто-выдача", auto_delivery),
                callback_data=CBT.SWITCH_AUTO_DELIVERY
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Авто-восстановление лотов", auto_restore),
                callback_data=CBT.SWITCH_AUTO_RESTORE
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Автообновление", auto_update),
                callback_data=CBT.SWITCH_AUTO_UPDATE
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Авто-установка обновлений", auto_install),
                callback_data=CBT.SWITCH_AUTO_INSTALL
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN
            ),
        ],
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_notifications_menu(
    messages: bool,
    orders: bool,
    restore: bool,
    start: bool,
    deactivate: bool,
    bump: bool
) -> InlineKeyboardMarkup:
    """Меню настроек уведомлений"""
    
    def switch_text(name: str, enabled: bool) -> str:
        emoji = bool_to_emoji(enabled)
        return f"{emoji} {name}"
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=switch_text("Новые сообщения", messages),
                callback_data=CBT.NOTIF_MESSAGES
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Новые заказы", orders),
                callback_data=CBT.NOTIF_ORDERS
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Восстановление лота", restore),
                callback_data=CBT.NOTIF_RESTORE
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Запуск бота", start),
                callback_data=CBT.NOTIF_START
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Деактивация лота", deactivate),
                callback_data=CBT.NOTIF_DEACTIVATE
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Поднятие лота", bump),
                callback_data=CBT.NOTIF_BUMP
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN
            ),
        ],
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# === Автовыдача ===
LOTS_PER_PAGE = 10


def get_auto_delivery_lots_menu(lots: list, offset: int = 0) -> InlineKeyboardMarkup:
    """
    Генерирует список лотов с автовыдачей
    
    Args:
        lots: Список лотов
        offset: Смещение для пагинации
    """
    keyboard = []
    
    # Лоты на текущей странице
    page_lots = lots[offset:offset + LOTS_PER_PAGE]
    
    for i, lot in enumerate(page_lots):
        lot_index = offset + i
        name = lot.get('name', 'Без названия')
        enabled = lot.get('enabled', True)
        
        # Статус активен
        status = "✅" if enabled else "❌"
        
        # Количество товаров
        products_count = lot.get('products_count', 0)
        products_info = f" ({products_count} шт.)" if products_count > 0 else ""
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {name}{products_info}",
                callback_data=f"ad_edit_lot:{lot_index}:{offset}"
            )
        ])
    
    # Навигация
    nav_row = []
    
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"ad_lots_list:{offset - LOTS_PER_PAGE}"
            )
        )
    
    if offset + LOTS_PER_PAGE < len(lots):
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"ad_lots_list:{offset + LOTS_PER_PAGE}"
            )
        )
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Кнопки управления
    keyboard.extend([
        [
            InlineKeyboardButton(
                text="➕ Добавить лот",
                callback_data="ad_add_lot"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"ad_lots_list:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN
            )
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_lot_edit_menu(lot_index: int, offset: int, lot: dict) -> InlineKeyboardMarkup:
    """
    Генерирует редактирование лота
    
    Args:
        lot_index: Индекс лота в списке
        offset: Текущее смещение для возврата
        lot: Данные лота
    """
    def switch_text(label: str, value: bool) -> str:
        return f"{'✅' if value else '❌'} {label}"
    
    enabled = lot.get('enabled', True)
    disable_on_empty = lot.get('disable_on_empty', False)
    disable_auto_restore = lot.get('disable_auto_restore', False)
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📝 Изменить текст ответа",
                callback_data=f"ad_set_text:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📂 Загрузить файл товаров",
                callback_data=f"ad_upload:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Включение автовыдачи", enabled),
                callback_data=f"ad_switch:enabled:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Деактивация при опустошении", disable_on_empty),
                callback_data=f"ad_switch:disable_on_empty:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Отключить авто-восстановление", disable_auto_restore),
                callback_data=f"ad_switch:disable_auto_restore:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Файл продуктов",
                callback_data=f"ad_file_info:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить лот",
                callback_data=f"ad_delete:{lot_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 К списку лотов",
                callback_data=f"ad_lots_list:{offset}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_button(callback_data: str) -> InlineKeyboardMarkup:
    """
    Простая кнопка назад
    
    Args:
        callback_data: Данные для callback
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=callback_data
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# === Чёрный список ===
USERS_PER_PAGE = 10


def get_blacklist_menu(blacklist: list, offset: int = 0) -> InlineKeyboardMarkup:
    """
    Генерирует список чёрного списка
    
    Args:
        blacklist: Список пользователей
        offset: Смещение для пагинации
    """
    keyboard = []
    
    # Пользователи на текущей странице
    page_users = blacklist[offset:offset + USERS_PER_PAGE]
    
    for i, user in enumerate(page_users):
        user_index = offset + i
        username = user.get('username', 'Неизвестно')
        block_delivery = user.get('block_delivery', True)
        block_response = user.get('block_response', True)
        
        # Иконки блокировки
        delivery_icon = "📦❌" if block_delivery else "📦✅"
        response_icon = "💬❌" if block_response else "💬✅"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{delivery_icon}{response_icon} {username}",
                callback_data=f"bl_edit:{user_index}:{offset}"
            )
        ])
    
    # Навигация
    nav_row = []
    
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"bl_list:{offset - USERS_PER_PAGE}"
            )
        )
    
    if offset + USERS_PER_PAGE < len(blacklist):
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"bl_list:{offset + USERS_PER_PAGE}"
            )
        )
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Кнопки управления
    keyboard.extend([
        [
            InlineKeyboardButton(
                text="➕ Добавить пользователя",
                callback_data="bl_add"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN
            )
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_blacklist_user_edit_menu(user_index: int, offset: int, user: dict) -> InlineKeyboardMarkup:
    """
    Генерирует меню редактирования пользователя в ЧС
    
    Args:
        user_index: Индекс пользователя в списке
        offset: Текущее смещение для возврата
        user: Данные пользователя
    """
    def switch_text(label: str, value: bool) -> str:
        return f"{'✅' if value else '❌'} {label}"
    
    block_delivery = user.get('block_delivery', True)
    block_response = user.get('block_response', True)
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=switch_text("Блокировать выдачу", block_delivery),
                callback_data=f"bl_toggle:delivery:{user_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Блокировать ответы", block_response),
                callback_data=f"bl_toggle:response:{user_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить из ЧС",
                callback_data=f"bl_remove:{user_index}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 К списку",
                callback_data=f"bl_list:{offset}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# === Плагины ===
PLUGINS_PER_PAGE = 10


def get_plugins_menu(plugins: list, offset: int = 0) -> InlineKeyboardMarkup:
    """
    Генерирует список плагинов
    
    Args:
        plugins: Список плагинов
        offset: Смещение для пагинации
    """
    keyboard = []
    
    # Плагины на текущей странице
    page_plugins = plugins[offset:offset + PLUGINS_PER_PAGE]
    
    for i, plugin in enumerate(page_plugins):
        plugin_index = offset + i
        uuid = plugin.get('uuid', '')
        name = plugin.get('name', 'Без названия')
        enabled = plugin.get('enabled', False)
        version = plugin.get('version', '?')
        
        # Статус
        status = "✅" if enabled else "❌"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {name} v{version}",
                callback_data=f"plugin_info:{uuid}:{offset}"
            )
        ])
    
    # Навигация
    nav_row = []
    
    if offset > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"plugins_list:{offset - PLUGINS_PER_PAGE}"
            )
        )
    
    if offset + PLUGINS_PER_PAGE < len(plugins):
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"plugins_list:{offset + PLUGINS_PER_PAGE}"
            )
        )
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Кнопки управления
    keyboard.extend([
        [
            InlineKeyboardButton(
                text="📤 Загрузить плагин",
                callback_data="upload_plugin"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN
            )
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_plugin_info_menu(uuid: str, offset: int, enabled: bool) -> InlineKeyboardMarkup:
    """
    Генерирует меню информации о плагине
    
    Args:
        uuid: UUID плагина
        offset: Текущее смещение для возврата
        enabled: Включён ли плагин
    """
    status_text = "❌ Отключить" if enabled else "✅ Включить"
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=status_text,
                callback_data=f"plugin_toggle:{uuid}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить плагин",
                callback_data=f"plugin_delete_ask:{uuid}:{offset}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 К списку",
                callback_data=f"plugins_list:{offset}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
