"""
Панель управления плагинами (Control Panel).
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import logging
import os
from pathlib import Path

if TYPE_CHECKING:
    from bot.plugins.manager import PluginManager

from aiogram import F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards.keyboards import CBT
from bot.keyboards.plugins import plugins_list, edit_plugin, plugin_commands


logger = logging.getLogger("PluginsCP")


class PluginUploadState(StatesGroup):
    """Состояния для загрузки плагинов"""
    waiting_for_file = State()


def init_plugins_cp(bot, plugin_manager: PluginManager, router, *args):
    """
    Инициализация панели управления плагинами.
    Регистрирует обработчики для работы с плагинами через Telegram.
    
    :param bot: Экземпляр бота
    :param plugin_manager: Менеджер плагинов
    :param router: Router для регистрации обработчиков
    """
    
    def check_plugin_exists(uuid: str, message: Message) -> bool:
        """
        Проверяет существование плагина по UUID.
        Если плагин не существует - отправляет сообщение с кнопкой обновления.
        
        :param uuid: UUID плагина
        :param message: Telegram сообщение
        :return: True если плагин существует, False если нет
        """
        if uuid not in plugin_manager.plugins:
            keyboard = plugins_list(plugin_manager, CBT, 0)
            text = f"❌ Плагин с UUID `{uuid}` не найден.\n\nВозможно он был удалён."
            bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return False
        return True
    
    @router.callback_query(F.data.startswith(f"{CBT.PLUGINS_LIST}:"))
    async def open_plugins_list(callback: CallbackQuery):
        """Открывает список плагинов"""
        await callback.answer()
        
        offset = int(callback.data.split(":")[1])
        
        keyboard = plugins_list(plugin_manager, CBT, offset)
        
        total = len(plugin_manager.plugins)
        enabled = sum(1 for p in plugin_manager.plugins.values() if p.enabled)
        
        text = (
            "🧩 *Управление плагинами*\n\n"
            f"📦 Всего плагинов: {total}\n"
            f"✅ Активных: {enabled}\n"
            f"⏸️ Отключённых: {total - enabled}\n\n"
            "⚠️ *После активации/деактивации/удаления плагина "
            "необходимо перезапустить бота!* /restart"
        )
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    @router.callback_query(F.data.startswith(f"{CBT.EDIT_PLUGIN}:"))
    async def open_edit_plugin_cp(callback: CallbackQuery):
        """Открывает панель редактирования плагина"""
        await callback.answer()
        
        parts = callback.data.split(":")
        uuid, offset = parts[1], int(parts[2])
        
        if not check_plugin_exists(uuid, callback.message):
            return
        
        plugin = plugin_manager.plugins[uuid]
        
        keyboard = edit_plugin(plugin, CBT, uuid, int(offset), ask_delete=False)
        
        text = (
            f"<b><i>{plugin.name} v{plugin.version}</i></b>\n\n"
            f"{plugin.description}\n\n"
            f"<b><i>UUID:</i></b> <code>{plugin.uuid}</code>\n"
            f"<b><i>Автор:</i></b> {plugin.author}\n"
            f"<b><i>Статус:</i></b> {'✅ Активен' if plugin.enabled else '⏸️ Отключён'}\n"
        )
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    @router.callback_query(F.data.startswith(f"{CBT.PLUGIN_COMMANDS}:"))
    async def open_plugin_commands(callback: CallbackQuery):
        """Открывает список команд плагина"""
        await callback.answer()
        
        parts = callback.data.split(":")
        uuid, offset = parts[1], int(parts[2])
        
        if not check_plugin_exists(uuid, callback.message):
            return
        
        plugin = plugin_manager.plugins[uuid]
        
        if not plugin.commands:
            await callback.answer("У этого плагина нет команд", show_alert=True)
            return
        
        commands_text = []
        for cmd, desc in plugin.commands.items():
            commands_text.append(f"/{cmd} - {desc}")
        
        text = (
            f"⌨️ *Команды плагина {plugin.name}*\n\n"
            + "\n\n".join(commands_text)
        )
        
        keyboard = plugin_commands(plugin, CBT, uuid, int(offset))
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    @router.callback_query(F.data.startswith(f"{CBT.TOGGLE_PLUGIN}:"))
    async def toggle_plugin(callback: CallbackQuery):
        """Включает/выключает плагин"""
        await callback.answer()
        
        parts = callback.data.split(":")
        uuid, offset = parts[1], int(parts[2])
        
        if not check_plugin_exists(uuid, callback.message):
            return
        
        plugin_manager.toggle_plugin(uuid)
        plugin = plugin_manager.plugins[uuid]
        
        status = "активирован" if plugin.enabled else "деактивирован"
        logger.info(
            f"Пользователь {callback.from_user.username} ({callback.from_user.id}) "
            f"{status} плагин {plugin.name}"
        )
        
        # Обновляем меню
        callback.data = f"{CBT.EDIT_PLUGIN}:{uuid}:{offset}"
        await open_edit_plugin_cp(callback)
    
    @router.callback_query(F.data.startswith(f"{CBT.DELETE_PLUGIN}:"))
    async def ask_delete_plugin(callback: CallbackQuery):
        """Запрашивает подтверждение удаления плагина"""
        await callback.answer()
        
        parts = callback.data.split(":")
        uuid, offset = parts[1], int(parts[2])
        
        if not check_plugin_exists(uuid, callback.message):
            return
        
        plugin = plugin_manager.plugins[uuid]
        keyboard = edit_plugin(plugin, CBT, uuid, int(offset), ask_delete=True)
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith(f"{CBT.CANCEL_DELETE_PLUGIN}:"))
    async def cancel_delete_plugin(callback: CallbackQuery):
        """Отменяет удаление плагина"""
        await callback.answer()
        
        parts = callback.data.split(":")
        uuid, offset = parts[1], int(parts[2])
        
        if not check_plugin_exists(uuid, callback.message):
            return
        
        plugin = plugin_manager.plugins[uuid]
        keyboard = edit_plugin(plugin, CBT, uuid, int(offset), ask_delete=False)
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith(f"{CBT.CONFIRM_DELETE_PLUGIN}:"))
    async def delete_plugin(callback: CallbackQuery):
        """Удаляет плагин"""
        await callback.answer()
        
        parts = callback.data.split(":")
        uuid, offset = parts[1], int(parts[2])
        
        if not check_plugin_exists(uuid, callback.message):
            return
        
        plugin = plugin_manager.plugins[uuid]
        plugin_name = plugin.name
        
        # Удаляем плагин
        if plugin_manager.delete_plugin(uuid):
            logger.info(
                f"Пользователь {callback.from_user.username} ({callback.from_user.id}) "
                f"удалил плагин {plugin_name}"
            )
            
            await callback.answer(f"✅ Плагин {plugin_name} удалён", show_alert=True)
            
            # Возвращаемся к списку
            callback.data = f"{CBT.PLUGINS_LIST}:{offset}"
            await open_plugins_list(callback)
        else:
            await callback.answer("❌ Ошибка при удалении плагина", show_alert=True)
    
    @router.callback_query(F.data.startswith(f"{CBT.UPLOAD_PLUGIN}:"))
    async def act_upload_plugin(callback: CallbackQuery, state: FSMContext):
        """Активирует режим загрузки плагина"""
        await callback.answer()
        
        offset = int(callback.data.split(":")[1])
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"{CBT.PLUGINS_LIST}:{offset}"
            )]
        ])
        
        await callback.message.edit_text(
            text=(
                "📤 *Загрузка плагина*\n\n"
                "Отправьте файл плагина (`.py`) в этот чат.\n\n"
                "⚠️ *Внимание!* Устанавливайте плагины только из проверенных источников."
            ),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(PluginUploadState.waiting_for_file)
        await state.update_data(offset=offset)
    
    @router.message(PluginUploadState.waiting_for_file, F.document)
    async def upload_plugin(message: Message, state: FSMContext):
        """Обрабатывает загрузку файла плагина"""
        data = await state.get_data()
        offset = data.get("offset", 0)
        await state.clear()
        
        # Проверяем расширение файла
        if not message.document.file_name.endswith('.py'):
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"{CBT.PLUGINS_LIST}:{offset}"
                )]
            ])
            
            await message.answer(
                "❌ Неверный формат файла. Ожидается `.py` файл.",
                reply_markup=keyboard
            )
            return
        
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_path = Path("plugins") / message.document.file_name
        
        await bot.download_file(file.file_path, file_path)
        
        logger.info(
            f"[ВАЖНО] Пользователь @{message.from_user.username} ({message.from_user.id}) "
            f"загрузил плагин {file_path}"
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"{CBT.PLUGINS_LIST}:{offset}"
            )]
        ])
        
        await message.answer(
            f"✅ Плагин `{message.document.file_name}` загружен!\n\n"
            "⚠️ *Перезапустите бота* для применения изменений.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


# Экспорт функции инициализации для системы плагинов
BIND_TO_PRE_INIT = [init_plugins_cp]

