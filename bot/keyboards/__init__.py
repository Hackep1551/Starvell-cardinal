"""
Клавиатуры для Telegram UI.
"""

from .keyboards import (
    CBT,
    get_main_menu,
    get_global_switches_menu,
    get_notifications_menu,
    get_auto_delivery_lots_menu,
    get_lot_edit_menu,
    get_back_button,
    get_blacklist_menu,
    get_blacklist_user_edit_menu,
    get_plugins_menu,
    get_plugin_info_menu,
)
from .plugins import plugins_list, edit_plugin, plugin_commands

__all__ = [
    'CBT',
    'get_main_menu',
    'get_global_switches_menu',
    'get_notifications_menu',
    'get_auto_delivery_lots_menu',
    'get_lot_edit_menu',
    'get_back_button',
    'get_blacklist_menu',
    'get_blacklist_user_edit_menu',
    'get_plugins_menu',
    'get_plugin_info_menu',
    'plugins_list',
    'edit_plugin',
    'plugin_commands',
]
