"""
Клавиатуры для управления плагинами
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



def plugins_list(plugin_manager, CBT, offset: int = 0) -> InlineKeyboardMarkup:
    """Список плагинов с пагинацией"""
    keyboard = []
    
    plugins = list(plugin_manager.plugins.values())
    per_page = 5
    start = offset
    end = min(offset + per_page, len(plugins))
    
    for i in range(start, end):
        plugin = plugins[i]
        status = "🟢" if plugin.enabled else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {plugin.name} v{plugin.version}",
                callback_data=f"{CBT.EDIT_PLUGIN}:{plugin.uuid}:{offset}"
            )
        ])
    
    # Навигация
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"{CBT.PLUGINS_LIST}:{offset - per_page}"
            )
        )
    if end < len(plugins):
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"{CBT.PLUGINS_LIST}:{offset + per_page}"
            )
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Загрузить плагин
    keyboard.append([
        InlineKeyboardButton(
            text="⤴️ Загрузить плагин",
            callback_data=CBT.UPLOAD_PLUGIN
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=CBT.MAIN
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def edit_plugin(plugin_data, CBT, uuid: str, offset: int, ask_delete: bool = False) -> InlineKeyboardMarkup:
    """Меню редактирования плагина"""
    keyboard = []
    
    if ask_delete:
        # Подтверждение удаления
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=f"{CBT.CONFIRM_DELETE_PLUGIN}:{uuid}:{offset}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"{CBT.EDIT_PLUGIN}:{uuid}:{offset}"
            )
        ])
    else:
        # Обычное меню
        status_text = "🔴 Включить" if not plugin_data.enabled else "🟢 Выключить"
        keyboard.append([
            InlineKeyboardButton(
                text=status_text,
                callback_data=f"{CBT.TOGGLE_PLUGIN}:{uuid}:{offset}"
            )
        ])
        
        # Если есть команды
        if plugin_data.commands:
            keyboard.append([
                InlineKeyboardButton(
                    text="⚙️ Команды плагина",
                    callback_data=f"{CBT.PLUGIN_COMMANDS}:{uuid}:{offset}"
                )
            ])
        
        # Если есть страница настроек
        if plugin_data.has_settings:
            keyboard.append([
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data=f"{CBT.PLUGIN_SETTINGS}:{uuid}:{offset}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🗑️ Удалить плагин",
                callback_data=f"{CBT.DELETE_PLUGIN}:{uuid}:{offset}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="? �����",
            callback_data=f"{CBT.PLUGINS_LIST}:{offset}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def plugin_commands(plugin_data, CBT, uuid: str, offset: int) -> InlineKeyboardMarkup:
    """Список команд плагина"""
    keyboard = []
    
    for cmd_name, cmd_desc in plugin_data.commands.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"/{cmd_name} - {cmd_desc}",
                callback_data="empty"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="? �����",
            callback_data=f"{CBT.EDIT_PLUGIN}:{uuid}:{offset}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

