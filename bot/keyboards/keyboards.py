"""
Клавиатуры для бота
"""

import logging
import os
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from bot.core.config import BotConfig

logger = logging.getLogger(__name__)


class CBT:
    """Типы callback кнопок"""
    # Главное меню
    MAIN = "main"
    MAIN_PAGE_2 = "main:p2"
    MAIN_PAGE_3 = "main:p3"
    GLOBAL_SWITCHES = "global"
    NOTIFICATIONS = "notif"
    PLUGINS = "plugins"
    ABOUT = "about"
    AUTO_DELIVERY = "autodelivery"
    BLACKLIST = "blacklist"
    TEMPLATES = "templates"
    
    # Вторая страница главного меню
    ORDER_CONFIRM_RESPONSE = "order_confirm_resp"
    REVIEW_RESPONSE = "review_resp"
    WELCOME_MESSAGE = "welcome_msg"
    CONFIGS_MENU = "configs"
    AUTHORIZED_USERS = "auth_users"
    
    # Кастомные команды
    CUSTOM_COMMANDS = "custom_cmds"
    ADD_CUSTOM_COMMAND = "custom_cmd_add"
    TOGGLE_CUSTOM_COMMANDS = "custom_cmd_toggle"
    CHANGE_PREFIX = "custom_cmd_prefix"
    
    # Конфиги
    CONFIG_DOWNLOAD = "cfg_download"
    CONFIG_UPLOAD = "cfg_upload"
    
    # Авторизованные пользователи
    REMOVE_AUTH_USER = "rm_auth"
    
    # Переключатели
    SWITCH_AUTO_BUMP = "switch:auto_bump"
    SWITCH_AUTO_DELIVERY = "switch:auto_delivery"
    SWITCH_AUTO_RESTORE = "switch:auto_restore"
    SWITCH_AUTO_READ = "switch:auto_read"
    SWITCH_AUTO_TICKET = "switch:auto_ticket"
    SWITCH_AUTO_INSTALL = "switch:auto_install"
    SWITCH_ORDER_CONFIRM = "switch:order_confirm"
    SWITCH_REVIEW_RESPONSE = "switch:review_resp"
    SWITCH_USE_WATERMARK = "switch:use_watermark"
    SWITCH_WELCOME_MESSAGE = "switch:welcome_msg"
    SWITCH_KEEP_ALIVE = "switch:keep_alive"
    SWITCH_PRIVACY_OFFERS = "switch:privacy_offers"

    # Приватность предложений
    PRIVACY_OFFERS = "privacy_offers"
    PRIVACY_OFFERS_MODE = "privacy_offers:mode"
    PRIVACY_OFFERS_TZ = "privacy_offers:tz"
    PRIVACY_OFFERS_ADD = "privacy_offers:add"
    PRIVACY_OFFERS_DELETE = "privacy_offers:del"
    
    # Настройки авто-тикета
    AUTO_TICKET_SETTINGS = "autoticket_settings"
    AUTO_TICKET_SET_INTERVAL = "autoticket_set_interval"
    AUTO_TICKET_SET_MAX = "autoticket_set_max"
    SWITCH_AUTO_TICKET_NOTIFY = "switch:autoticket_notify"
    SWITCH_AUTO_TICKET_INTERNAL = "switch:auto_ticket_internal"
    
    # Уведомления
    NOTIF_MESSAGES = "notif:messages"
    NOTIF_SUPPORT_MESSAGES = "notif:support"
    NOTIF_ORDERS = "notif:orders"
    NOTIF_RESTORE = "notif:restore"
    NOTIF_START = "notif:start"
    NOTIF_STOP = "notif:stop"
    NOTIF_AUTO_TICKET = "notif:auto_ticket"
    NOTIF_ORDER_CONFIRMED = "notif:order_confirmed"
    NOTIF_REVIEW = "notif:review"
    NOTIF_AUTO_RESPONSES = "notif:auto_responses"
    NOTIF_LOT_DEACTIVATE = "notif:lot_deactivate"
    NOTIF_LOT_BUMP = "notif:lot_bump"
    
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
    
    # Заготовки ответов
    ADD_TEMPLATE = "tpl_add"
    TEMPLATE_DETAIL = "tpl_detail"
    EDIT_TEMPLATE = "tpl_edit"
    EDIT_TEMPLATE_NAME = "tpl_edit_name"
    EDIT_TEMPLATE_TEXT = "tpl_edit_text"
    DELETE_TEMPLATE = "tpl_delete"
    SELECT_TEMPLATE = "tpl_select"
    
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

    # Прокси
    PROXY = "proxy_menu"
    PROXY_ADD = "proxy_add"
    PROXY_DISABLE = "proxy_disable"
    PROXY_ENABLE = "proxy_enable"
    PROXY_RESTART = "proxy_restart"


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
                text="🤖 Настройка автоответов",
                callback_data=CBT.CUSTOM_COMMANDS
            ),
        ],
        [
            InlineKeyboardButton(
                text="📦 Автовыдача",
                callback_data=CBT.AUTO_DELIVERY
            ),
        ],
        [
            InlineKeyboardButton(
                text="📋 Заготовки ответов",
                callback_data=CBT.TEMPLATES
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔌 Плагины",
                callback_data=CBT.PLUGINS
            ),
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ О боте",
                callback_data=CBT.ABOUT
            ),
        ],
        [
            InlineKeyboardButton(
                text="1/3",
                callback_data="empty"
            ),
            InlineKeyboardButton(
                text="➡️ Вперёд",
                callback_data=CBT.MAIN_PAGE_2
            ),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_main_menu_page_2(update_available: bool = False) -> InlineKeyboardMarkup:
    """Вторая страница главного меню"""
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
                text="✅ Ответ на подтверждение заказа",
                callback_data=CBT.ORDER_CONFIRM_RESPONSE
            ),
        ],
        [
            InlineKeyboardButton(
                text="⭐ Ответ на отзыв",
                callback_data=CBT.REVIEW_RESPONSE
            ),
        ],
        [
            InlineKeyboardButton(
                text="👋 Приветственное сообщение",
                callback_data=CBT.WELCOME_MESSAGE
            ),
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Авто-тикеты",
                callback_data=CBT.AUTO_TICKET_SETTINGS
            ),
        ],
        [
            InlineKeyboardButton(
                text="👁️ Приватность предложений",
                callback_data=CBT.PRIVACY_OFFERS
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=CBT.MAIN
            ),
            InlineKeyboardButton(
                text="2/3",
                callback_data="empty"
            ),
            InlineKeyboardButton(
                text="➡️ Вперёд",
                callback_data=CBT.MAIN_PAGE_3
            ),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_main_menu_page_3(update_available: bool = False) -> InlineKeyboardMarkup:
    """Третья страница главного меню"""
    keyboard = []

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
                text="📁 Конфиги",
                callback_data=CBT.CONFIGS_MENU
            ),
        ],
        [
            InlineKeyboardButton(
                text="🚫 Чёрный список",
                callback_data=CBT.BLACKLIST
            ),
        ],
        [
            InlineKeyboardButton(
                text="👥 Авторизованные пользователи",
                callback_data=CBT.AUTHORIZED_USERS
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔗 Сообщить об проблеме",
                url=os.environ.get('TELEGRAM_SUPPORT_URL', 'https://t.me/starvellbugreport_bot')
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔒 Прокси",
                callback_data=CBT.PROXY
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=CBT.MAIN_PAGE_2
            ),
            InlineKeyboardButton(
                text="3/3",
                callback_data="empty"
            ),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_global_switches_menu(
    auto_bump: bool, 
    auto_delivery: bool, 
    auto_restore: bool, 
    auto_read: bool = True,
    auto_ticket: bool = False,
    auto_install: bool = False,
    order_confirm: bool = False,
    review_response: bool = False,
    privacy_offers: bool | None = None,
) -> InlineKeyboardMarkup:
    """Меню глобальных переключателей"""
    
    def switch_text(name: str, enabled: bool) -> str:
        emoji = bool_to_emoji(enabled)
        return f"{emoji} {name}"

    if privacy_offers is None:
        privacy_offers = BotConfig.PRIVACY_OFFERS_ENABLED()
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=switch_text("Авто-поднятие", auto_bump),
                callback_data=CBT.SWITCH_AUTO_BUMP
            ),
            InlineKeyboardButton(
                text=switch_text("Авто-выдача", auto_delivery),
                callback_data=CBT.SWITCH_AUTO_DELIVERY
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Авто-восстановление", auto_restore),
                callback_data=CBT.SWITCH_AUTO_RESTORE
            ),
            InlineKeyboardButton(
                text=switch_text("Авто-прочтение", auto_read),
                callback_data=CBT.SWITCH_AUTO_READ
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Ответ на подтверждение заказа", order_confirm),
                callback_data=CBT.SWITCH_ORDER_CONFIRM
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Ответ на отзыв", review_response),
                callback_data=CBT.SWITCH_REVIEW_RESPONSE
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Авто-тикет", auto_ticket),
                callback_data=CBT.SWITCH_AUTO_TICKET
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
                text=switch_text("Использовать вотермарку", BotConfig.USE_WATERMARK()),
                callback_data=CBT.SWITCH_USE_WATERMARK
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Вечный онлайн", BotConfig.KEEP_ALIVE_ENABLED()),
                callback_data=CBT.SWITCH_KEEP_ALIVE
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Приватность предложений", privacy_offers),
                callback_data=CBT.SWITCH_PRIVACY_OFFERS
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
    stop: bool = False,
    auto_ticket: bool = False,
    order_confirm: bool = False,
    review: bool = False,
    auto_responses: bool = False,
    support_messages: bool = True,
) -> InlineKeyboardMarkup:
    """Меню настроек уведомлений

    Поддерживает дополнительные переключатели:
    - stop: уведомления об остановке бота
    - auto_ticket: уведомления об отправке авто-тикетов
    - order_confirm: уведомления о подтверждении заказа
    - review: уведомления о новых отзывах
    - auto_responses: уведомления о выполнении автоответов/команд
    - support_messages: уведомления о сообщениях от поддержки/модерации
    """
    
    def switch_text(name: str, enabled: bool) -> str:
        emoji = bool_to_emoji(enabled)
        return f"{emoji} {name}"
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=switch_text("Новые сообщения", messages),
                callback_data=CBT.NOTIF_MESSAGES
            ),
            InlineKeyboardButton(
                text=switch_text("Новые заказы", orders),
                callback_data=CBT.NOTIF_ORDERS
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Сообщения от поддержки", support_messages),
                callback_data=CBT.NOTIF_SUPPORT_MESSAGES
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Получена команда (автоответы)", auto_responses),
                callback_data=CBT.NOTIF_AUTO_RESPONSES
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Подтверждение заказа", order_confirm),
                callback_data=CBT.NOTIF_ORDER_CONFIRMED
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
                text=switch_text("Отправка тикета", auto_ticket),
                callback_data=CBT.NOTIF_AUTO_TICKET
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Ответ на отзыв", review),
                callback_data=CBT.NOTIF_REVIEW
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Деактивация лота", BotConfig.NOTIFY_LOT_DEACTIVATE()),
                callback_data=CBT.NOTIF_LOT_DEACTIVATE
            ),
            InlineKeyboardButton(
                text=switch_text("Поднятие лотов", BotConfig.NOTIFY_LOT_BUMP()),
                callback_data=CBT.NOTIF_LOT_BUMP
            ),
        ],
        [
            InlineKeyboardButton(
                text=switch_text("Запуск бота", start),
                callback_data=CBT.NOTIF_START
            ),
            InlineKeyboardButton(
                text=switch_text("Остановка бота", stop),
                callback_data=CBT.NOTIF_STOP
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
                callback_data=CBT.MAIN_PAGE_3
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
                callback_data=f"upload_plugin:{offset}"
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


def get_templates_menu(templates: list) -> InlineKeyboardMarkup:
    """
    Меню заготовок ответов
    
    Args:
        templates: Список заготовок [{"id": "...", "name": "...", "text": "..."}, ...]
    """
    keyboard = []
    
    # Список быстрых ответов
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📝 {template['name']}",
                callback_data=f"{CBT.TEMPLATE_DETAIL}:{template['id']}"
            )
        ])
    
    # Кнопка добавления быстрого ответа
    keyboard.append([
        InlineKeyboardButton(
            text="➕ Добавить быстрый ответ",
            callback_data=CBT.ADD_TEMPLATE
        )
    ])
    
    # Назад в главное меню
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data=CBT.MAIN
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_template_detail_menu(template_id: str) -> InlineKeyboardMarkup:
    """
    Детальное меню заготовки
    
    Args:
        template_id: ID заготовки
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"{CBT.EDIT_TEMPLATE}:{template_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"{CBT.DELETE_TEMPLATE}:{template_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 К списку",
                callback_data=CBT.TEMPLATES
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_template_edit_menu(template_id: str) -> InlineKeyboardMarkup:
    """
    Меню редактирования заготовки
    
    Args:
        template_id: ID заготовки
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Изменить название",
                callback_data=f"{CBT.EDIT_TEMPLATE_NAME}:{template_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Изменить текст",
                callback_data=f"{CBT.EDIT_TEMPLATE_TEXT}:{template_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"{CBT.TEMPLATE_DETAIL}:{template_id}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_select_template_menu(chat_id: str, templates: list = None) -> InlineKeyboardMarkup:
    """
    Меню выбора заготовки для отправки
    
    Args:
        chat_id: ID чата для отправки (строка, может быть UUID)
        templates: Список заготовок (если None - загрузит автоматически)
    """
    from bot.core.templates import get_template_manager
    
    if templates is None:
        template_manager = get_template_manager()
        templates = template_manager.get_all()
    
    keyboard = []
    
    if templates:
        for template in templates:
            callback_data = f"{CBT.SELECT_TEMPLATE}:{template['id']}:{chat_id}"
            # Проверяем длину callback_data (лимит Telegram - 64 байта)
            if len(callback_data.encode('utf-8')) <= 64:
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"📝 {template['name']}",
                        callback_data=callback_data
                    )
                ])
            else:
                # Если callback_data слишком длинный, используем только template_id
                # Обработчик должен будет искать chat_id из контекста сообщения
                logger.warning(f"Callback data слишком длинный ({len(callback_data.encode('utf-8'))} байт), используем короткую версию")
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"📝 {template['name']}",
                        callback_data=f"{CBT.SELECT_TEMPLATE}:{template['id']}"
                    )
                ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="➕ Добавить быстрый ответ",
                callback_data=CBT.ADD_TEMPLATE
            )
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


def get_order_confirm_response_menu(enabled: bool, text: str) -> InlineKeyboardMarkup:
    """Меню настройки ответа на подтверждение заказа"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if enabled else '❌'} Включено: {'Да' if enabled else 'Нет'}",
                callback_data=CBT.SWITCH_ORDER_CONFIRM
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить текст ответа",
                callback_data="edit_order_confirm_text"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN_PAGE_3
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_welcome_message_menu(enabled: bool, text: str) -> InlineKeyboardMarkup:
    """Меню настройки приветственного сообщения"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if enabled else '❌'} Включено: {'Да' if enabled else 'Нет'}",
                callback_data=CBT.SWITCH_WELCOME_MESSAGE
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить текст приветствия",
                callback_data="edit_welcome_text"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN_PAGE_2
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_review_response_menu(enabled: bool, text: str) -> InlineKeyboardMarkup:
    """Меню настройки ответа на отзыв"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if enabled else '❌'} Включено: {'Да' if enabled else 'Нет'}",
                callback_data=CBT.SWITCH_REVIEW_RESPONSE
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить текст ответа",
                callback_data="edit_review_text"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN_PAGE_2
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_auto_ticket_settings_menu(
    enabled: bool,
    interval: int,
    max_orders: int,
    notify: bool
) -> InlineKeyboardMarkup:
    """Меню настроек авто-тикета"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if enabled else '❌'} Статус: {'Включено' if enabled else 'Выключено'}",
                callback_data=CBT.SWITCH_AUTO_TICKET_INTERNAL
            )
        ],
        [
            InlineKeyboardButton(
                text=f"⏱ Интервал: {interval} сек",
                callback_data=CBT.AUTO_TICKET_SET_INTERVAL
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🔢 Макс. заказов: {max_orders}",
                callback_data=CBT.AUTO_TICKET_SET_MAX
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'🔔' if notify else '🔕'} Уведомления: {'Вкл' if notify else 'Выкл'}",
                callback_data=CBT.SWITCH_AUTO_TICKET_NOTIFY
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.GLOBAL_SWITCHES
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_configs_menu() -> InlineKeyboardMarkup:
    """Меню управления конфигами"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="📥 Скачать конфиг",
                callback_data=CBT.CONFIG_DOWNLOAD
            )
        ],
        [
            InlineKeyboardButton(
                text="📤 Загрузить конфиг",
                callback_data=CBT.CONFIG_UPLOAD
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN_PAGE_2
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_authorized_users_menu(admin_ids: list) -> InlineKeyboardMarkup:
    """Меню авторизованных пользователей"""
    keyboard = []
    
    for admin_id in admin_ids:
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {admin_id}",
                callback_data="empty"
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"{CBT.REMOVE_AUTH_USER}:{admin_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=CBT.MAIN_PAGE_3
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_custom_commands_menu(commands: list, page: int = 0, enabled: bool = False, prefix: str = "!") -> InlineKeyboardMarkup:
    """Меню кастомных команд с пагинацией"""
    keyboard = []
    
    # Кнопка включения/выключения
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅ Включено' if enabled else '❌ Выключено'}",
            callback_data=CBT.TOGGLE_CUSTOM_COMMANDS
        )
    ])
    
    # Кнопка изменения префикса
    keyboard.append([
        InlineKeyboardButton(
            text=f"🔧 Изменить префикс ({prefix})",
            callback_data=CBT.CHANGE_PREFIX
        )
    ])
    
    # Кнопка добавления команды
    keyboard.append([
        InlineKeyboardButton(
            text="➕ Добавить команду",
            callback_data=CBT.ADD_CUSTOM_COMMAND
        )
    ])
    
    # Команды (по 5 на страницу)
    items_per_page = 5
    start = page * items_per_page
    end = start + items_per_page
    page_commands = commands[start:end]
    
    for cmd in page_commands:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{prefix}{cmd['name']}",
                callback_data=f"custom_cmd_view:{cmd['name']}"
            )
        ])
    
    # Пагинация
    if len(commands) > items_per_page:
        pagination_row = []
        
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=f"custom_cmd_page:{page-1}"
                )
            )
        
        total_pages = (len(commands) + items_per_page - 1) // items_per_page
        pagination_row.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                callback_data="empty"
            )
        )
        
        if end < len(commands):
            pagination_row.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=f"custom_cmd_page:{page+1}"
                )
            )
        
        keyboard.append(pagination_row)
    
    # Кнопка назад
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=CBT.MAIN
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_proxy_menu(enabled: bool, proxy_set: bool, proxy_type: str = 'socks5', ip: str = '', port: str = '') -> InlineKeyboardMarkup:
    """Меню настройки прокси"""
    status = bool_to_emoji(enabled) + (" Включён" if enabled else " Выключён")
    addr = f"{proxy_type}://{ip}:{port}" if ip and port else "не настроен"

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📡 {status}  |  {addr}",
                callback_data="empty"
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить / изменить прокси",
                callback_data=CBT.PROXY_ADD
            )
        ],
    ]

    if proxy_set:
        toggle_text = "❌ Выключить прокси" if enabled else "✅ Включить прокси"
        toggle_cb = CBT.PROXY_DISABLE if enabled else CBT.PROXY_ENABLE
        keyboard.append([
            InlineKeyboardButton(text=toggle_text, callback_data=toggle_cb)
        ])
        # Прокси для Telegram применяется только при старте сессии бота
        keyboard.append([
            InlineKeyboardButton(text="🔄 Перезапустить бота (применить)", callback_data=CBT.PROXY_RESTART)
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data=CBT.MAIN_PAGE_3)
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_privacy_offers_menu(
    enabled: bool,
    mode: str,
    timezone: str,
    windows: list,
) -> InlineKeyboardMarkup:
    mode_text = "Офлайн" if mode == "offline" else "Онлайн"
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{bool_to_emoji(enabled)} Автопереключение",
                callback_data=CBT.SWITCH_PRIVACY_OFFERS
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🔁 Режим: {mode_text}",
                callback_data=CBT.PRIVACY_OFFERS_MODE
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🌐 Часовой пояс: {timezone}",
                callback_data=CBT.PRIVACY_OFFERS_TZ
            )
        ],
    ]

    for index, window in enumerate(windows):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{index + 1}. {window.get('start')} - {window.get('end')}",
                callback_data="empty"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"{CBT.PRIVACY_OFFERS_DELETE}:{index}"
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton(
                text="➕ Добавить окно",
                callback_data=CBT.PRIVACY_OFFERS_ADD
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=CBT.MAIN_PAGE_2
            )
        ],
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
