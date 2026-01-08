"""
Хэндлеры панели управления плагинами
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.keyboards import (
    get_plugins_menu,
    get_plugin_info_menu
)

logger = logging.getLogger(__name__)

router = Router()


# ==================== Список плагинов ====================

@router.callback_query(F.data.startswith("plugins_list:"))
async def show_plugins_list(callback: CallbackQuery, plugin_manager, **kwargs):
    """Показать список плагинов"""
    try:
        offset = int(callback.data.split(":")[1])
        
        # Получаем плагины
        plugins_data = []
        for uuid, plugin in plugin_manager.plugins.items():
            plugins_data.append({
                "uuid": uuid,
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "enabled": plugin.enabled
            })
        
        keyboard = get_plugins_menu(plugins_data, offset)
        
        enabled_count = sum(1 for p in plugins_data if p["enabled"])
        disabled_count = len(plugins_data) - enabled_count
        
        text = "🧩 <b>Управление плагинами</b>\n\n"
        text += f"🧩 Всего плагинов: <code>{len(plugins_data)}</code>\n"
        text += f"✅ Активных: <code>{enabled_count}</code>\n"
        text += f"❌ Отключенных: <code>{disabled_count}</code>\n\n"
        text += "⚠️ После активации/деактивации/удаления плагина необходимо перезапустить бота! /restart"
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа списка плагинов: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке", show_alert=True)


# ==================== Просмотр плагина ====================

@router.callback_query(F.data.startswith("plugin_info:"))
async def show_plugin_info(callback: CallbackQuery, plugin_manager, **kwargs):
    """Показать информацию о плагине"""
    try:
        uuid = callback.data.split(":")[1]
        offset = int(callback.data.split(":")[2])
        
        if uuid not in plugin_manager.plugins:
            await callback.answer("❌ Плагин не найден", show_alert=True)
            return
        
        plugin = plugin_manager.plugins[uuid]
        
        text = f"🧩 <b>{plugin.name}</b>\n\n"
        text += f"<b>Версия:</b> {plugin.version}\n"
        text += f"<b>Автор:</b> {plugin.author}\n"
        text += f"<b>UUID:</b> <code>{uuid}</code>\n\n"
        text += f"<b>Описание:</b>\n{plugin.description}\n\n"
        text += f"<b>Статус:</b> {'✅ Включен' if plugin.enabled else '❌ Выключен'}"
        
        keyboard = get_plugin_info_menu(uuid, offset, plugin.enabled)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка показа информации о плагине: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


# ==================== Переключение плагина ====================

@router.callback_query(F.data.startswith("plugin_toggle:"))
async def toggle_plugin(callback: CallbackQuery, plugin_manager, **kwargs):
    """Переключить плагин"""
    try:
        uuid = callback.data.split(":")[1]
        offset = int(callback.data.split(":")[2])
        
        if uuid not in plugin_manager.plugins:
            await callback.answer("❌ Плагин не найден", show_alert=True)
            return
        
        # Переключаем
        plugin_manager.toggle_plugin(uuid)
        
        # Получаем обновлённый статус
        plugin = plugin_manager.plugins[uuid]
        status_text = "включен ✅" if plugin.enabled else "выключен ❌"
        
        logger.info(f"Плагин {plugin.name} {status_text} пользователем {callback.from_user.id}")
        
        # Обновляем текст и клавиатуру
        text = f"🧩 <b>{plugin.name}</b>\n\n"
        text += f"<b>Версия:</b> {plugin.version}\n"
        text += f"<b>Автор:</b> {plugin.author}\n"
        text += f"<b>UUID:</b> <code>{uuid}</code>\n\n"
        text += f"<b>Описание:</b>\n{plugin.description}\n\n"
        text += f"<b>Статус:</b> {'✅ Включен' if plugin.enabled else '❌ Выключен'}\n\n"
        text += "⚠️ После активации/деактивации/удаления плагина необходимо перезапустить бота! /restart"
        
        keyboard = get_plugin_info_menu(uuid, offset, plugin.enabled)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        
        # Уведомление
        await callback.answer(f"Плагин {status_text}", show_alert=False)
        
    except Exception as e:
        logger.error(f"Ошибка переключения плагина: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


# ==================== Удаление плагина ====================

@router.callback_query(F.data.startswith("plugin_delete_ask:"))
async def plugin_delete_ask(callback: CallbackQuery, plugin_manager, **kwargs):
    """Подтверждение удаления плагина"""
    try:
        uuid = callback.data.split(":")[1]
        offset = int(callback.data.split(":")[2])
        
        if uuid not in plugin_manager.plugins:
            await callback.answer("❌ Плагин не найден", show_alert=True)
            return
        
        plugin = plugin_manager.plugins[uuid]
        
        text = f"⚠️ <b>Удаление плагина</b>\n\n"
        text += f"Вы уверены, что хотите удалить плагин:\n"
        text += f"<b>{plugin.name}</b> v{plugin.version}?\n\n"
        text += f"<i>Файл плагина будет удалён безвозвратно!</i>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"plugin_delete_confirm:{uuid}:{offset}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"plugin_info:{uuid}:{offset}"
                )
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при запросе удаления плагина: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("plugin_delete_confirm:"))
async def plugin_delete_confirm(callback: CallbackQuery, plugin_manager, **kwargs):
    """Подтверждённое удаление плагина"""
    try:
        uuid = callback.data.split(":")[1]
        offset = int(callback.data.split(":")[2])
        
        if uuid not in plugin_manager.plugins:
            await callback.answer("❌ Плагин не найден", show_alert=True)
            return
        
        plugin = plugin_manager.plugins[uuid]
        plugin_name = plugin.name
        
        # Удаляем плагин
        success = plugin_manager.delete_plugin(uuid)
        
        if success:
            logger.info(f"Плагин {plugin_name} удалён пользователем {callback.from_user.id}")
            await callback.answer(f"✅ Плагин {plugin_name} удалён", show_alert=True)
            
            # Возвращаемся к списку плагинов - пересоздаём список вручную
            plugins_data = []
            for p_uuid, p in plugin_manager.plugins.items():
                plugins_data.append({
                    "uuid": p_uuid,
                    "name": p.name,
                    "version": p.version,
                    "description": p.description,
                    "enabled": p.enabled
                })
            
            keyboard = get_plugins_menu(plugins_data, offset)
            
            enabled_count = sum(1 for p in plugins_data if p["enabled"])
            disabled_count = len(plugins_data) - enabled_count
            
            text = "🧩 <b>Управление плагинами</b>\n\n"
            text += f"🧩 Всего плагинов: <code>{len(plugins_data)}</code>\n"
            text += f"✅ Активных: <code>{enabled_count}</code>\n"
            text += f"❌ Отключенных: <code>{disabled_count}</code>\n\n"
            text += "⚠️ После активации/деактивации/удаления плагина необходимо перезапустить бота! /restart"
            
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.answer("❌ Ошибка при удалении", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка удаления плагина: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


