"""
Обработчики команд бота
"""

import hashlib
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.core.config import BotConfig, get_config_manager
from bot.keyboards import (
    get_main_menu,
    get_global_switches_menu,
    get_notifications_menu,
    get_auto_delivery_lots_menu,
    get_blacklist_menu,
    get_plugins_menu,
    CBT,
)
from bot.handlers import auto_delivery_handlers, blacklist_handlers, plugins_handlers


router = Router()
router.include_router(auto_delivery_handlers.router)
router.include_router(blacklist_handlers.router)
router.include_router(plugins_handlers.router)


# === Состояния ===

class AuthState(StatesGroup):
    """Состояния для авторизации"""
    waiting_for_password = State()


class ReplyState(StatesGroup):
    """Состояния для быстрого ответа на сообщения"""
    waiting_for_reply = State()


# === Функции авторизации ===

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def is_user_authorized(user_id: int) -> bool:
    """Проверка авторизации пользователя"""
    admin_ids = BotConfig.ADMIN_IDS()
    return user_id in admin_ids


async def authorize_user(user_id: int):
    """Добавить пользователя в список админов"""
    admin_ids = BotConfig.ADMIN_IDS()
    if user_id not in admin_ids:
        admin_ids.append(user_id)
        BotConfig.set_admin_ids(admin_ids)

# === Команды ===

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, auto_update, **kwargs):
    """Команда /start"""
    # Загружаем текущий язык
    
    
    # Проверяем авторизацию
    if not is_user_authorized(message.from_user.id):
        await message.answer("🔒 Для доступа к боту введите пароль:")
        await state.set_state(AuthState.waiting_for_password)
        return
    
    # Проверяем наличие обновлений
    update_available = auto_update.update_available if auto_update else False
    
    await message.answer(
        "🌟 <b>Starvell Bot</b>\n\nПривет! Я помогу управлять вашим магазином на Starvell.\n\nИспользуйте меню ниже для управления ботом.",
        reply_markup=get_main_menu(update_available=update_available)
    )


@router.message(Command("update"))
async def cmd_update(message: Message, auto_update, **kwargs):
    """Команда /update - обновить бот"""
    # Проверяем авторизацию
    if not is_user_authorized(message.from_user.id):
        return
    
    # Проверяем наличие обновлений
    status_msg = await message.answer("🔍 Проверка обновлений...")
    
    update_available = await auto_update.check_for_updates()
    
    if not update_available:
        await status_msg.edit_text(
            f"✅ Установлена последняя версия: <code>{auto_update.current_version}</code>"
        )
        return
    
    # Обновление доступно
    await status_msg.edit_text(
        f"✨ Доступно обновление!\n\n"
        f"📌 Текущая: <code>{auto_update.current_version}</code>\n"
        f"✨ Новая: <code>{auto_update.latest_version}</code>\n\n"
        f"🔄 Начинаю обновление..."
    )
    
    # Выполняем обновление
    result = await auto_update.perform_update()
    
    if result["success"]:
        # Сбрасываем флаг уведомления после успешного обновления
        auto_update.reset_notification_flag()
        
        await status_msg.edit_text(
            result["message"] + "\n\n"
            f"<tg-spoiler>Git output:\n{result['output']}</tg-spoiler>\n\n"
            f"🔄 Перезапуск бота через 3 секунды..."
        )
        
        # Даём время прочитать сообщение и перезапускаем бот
        await asyncio.sleep(3)
        
        import os
        import sys
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        await status_msg.edit_text(
            result["message"] + "\n\n"
            f"<tg-spoiler>Error:\n{result['output']}</tg-spoiler>"
        )


@router.message(Command("logs"))
async def cmd_logs(message: Message, **kwargs):
    """Команда /logs - отправить логи"""
    # Проверяем авторизацию
    if not is_user_authorized(message.from_user.id):
        return
    
    from pathlib import Path
    from aiogram.types import FSInputFile, BufferedInputFile
    
    log_file = Path("logs/bot.log")
    
    # Проверяем существование файла
    if not log_file.exists():
        await message.answer("❌ Файл логов не найден")
        return
    
    try:
        # Читаем последние ошибки из лога
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Ищем последнюю ошибку
        last_error = None
        error_lines = []
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if ' - ERROR - ' in line or ' [E] ' in line:
                # Нашли ошибку, собираем её и следующие строки (traceback)
                error_lines = []
                for j in range(i, min(i + 20, len(lines))):
                    error_lines.append(lines[j])
                    if j > i and (' - INFO - ' in lines[j] or ' [I] ' in lines[j] or ' - WARNING - ' in lines[j] or ' [W] ' in lines[j]):
                        break
                last_error = ''.join(error_lines)
                break
        
        # Формируем сообщение
        if last_error:
            error_msg = f"📋 <b>Последняя ошибка:</b>\n\n<code>{last_error[:3500]}</code>"
        else:
            error_msg = "✅ Ошибок не обнаружено"
        
        # Отправляем сообщение
        await message.answer(error_msg)
        
        # Отправляем файл логов
        await message.answer_document(
            FSInputFile(log_file),
            caption="📄 Полный лог-файл бота"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при чтении логов: {e}")


@router.message(Command("restart"))
async def cmd_restart(message: Message, **kwargs):
    """Команда /restart - перезапустить бот"""
    # Проверяем авторизацию
    if not is_user_authorized(message.from_user.id):
        return
    
    import os
    import sys
    
    await message.answer(
        "🔄 <b>Перезапуск бота...</b>\n\n"
        "⏳ Бот будет перезапущен через несколько секунд"
    )
    
    # Даём время отправить сообщение
    await asyncio.sleep(1)
    
    # Перезапускаем процесс
    os.execv(sys.executable, [sys.executable] + sys.argv)


@router.message(AuthState.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    """Обработка ввода пароля"""
    password = message.text
    password_hash = hash_password(password)
    stored_hash = BotConfig.PASSWORD_HASH()
    
    # Удаляем сообщение с паролем
    try:
        await message.delete()
    except:
        pass
    
    if password_hash == stored_hash:
        # Пароль верный - авторизуем пользователя
        await authorize_user(message.from_user.id)
        await state.clear()
        
        await message.answer(
            "✅ Авторизация успешна!" + "\n\n" + "🌟 <b>Starvell Bot</b>\n\nПривет! Я помогу управлять вашим магазином на Starvell.\n\nИспользуйте меню ниже для управления ботом.",
            reply_markup=get_main_menu()
        )
    else:
        # Пароль неверный
        await message.answer("❌ Неверный пароль. Попробуйте ещё раз:")


# === Callback обработчики ===

@router.callback_query(F.data == "update_now")
async def callback_update_now(callback: CallbackQuery, auto_update, **kwargs):
    """Обработчик кнопки 'Обновить сейчас'"""
    await callback.answer()
    
    # Редактируем сообщение, показываем процесс
    await callback.message.edit_text("🔄 Выполняется обновление...")
    
    try:
        # Выполняем обновление
        result = await auto_update.perform_update()
        
        if result["success"]:
            # Сбрасываем флаг уведомления после успешного обновления
            auto_update.reset_notification_flag()
            
            response = (
                f"{result['message']}\n\n"
                f"<tg-spoiler>Git output:\n{result['output']}</tg-spoiler>\n\n"
                f"🔄 Перезапуск бота через 3 секунды..."
            )
            await callback.message.edit_text(response, parse_mode="HTML")
            
            # Даём время прочитать сообщение и перезапускаем бот
            await asyncio.sleep(3)
            
            import os
            import sys
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            response = (
                f"{result['message']}\n\n"
                f"<tg-spoiler>Error:\n{result['output']}</tg-spoiler>"
            )
            await callback.message.edit_text(response, parse_mode="HTML")
    except Exception as e:
        response = f"❌ <b>Ошибка при обновлении:</b>\n{str(e)}"
        await callback.message.edit_text(response, parse_mode="HTML")


@router.callback_query(F.data == CBT.MAIN)
async def callback_main_menu(callback: CallbackQuery, auto_update, **kwargs):
    """Главное меню"""
    await callback.answer()
    
    # Загружаем текущий язык
    
    # Проверяем наличие обновлений
    update_available = auto_update.update_available if auto_update else False
    
    await callback.message.edit_text(
        "🌟 <b>Starvell Bot</b>\n\nПривет! Я помогу управлять вашим магазином на Starvell.\n\nИспользуйте меню ниже для управления ботом.",
        reply_markup=get_main_menu(update_available=update_available)
    )


@router.callback_query(F.data == CBT.GLOBAL_SWITCHES)
async def callback_global_switches(callback: CallbackQuery):
    """Меню глобальных переключателей"""
    await callback.answer()
    
    # Загружаем текущий язык
    
    
    # Получаем текущие настройки
    auto_bump = BotConfig.AUTO_BUMP_ENABLED()
    auto_delivery = BotConfig.AUTO_DELIVERY_ENABLED()
    auto_restore = BotConfig.AUTO_RESTORE_ENABLED()
    auto_update = BotConfig.AUTO_UPDATE_ENABLED()
    auto_install = BotConfig.AUTO_UPDATE_INSTALL()
    
    # Формируем описание
    status_text = "⚙️ <b>Глобальные переключатели</b>\n\nЗдесь вы можете включать и отключать основные функции бота.\n\n"
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_global_switches_menu(auto_bump, auto_delivery, auto_restore, auto_update, auto_install)
    )


@router.callback_query(F.data == CBT.SWITCH_AUTO_BUMP)
async def callback_switch_auto_bump(callback: CallbackQuery):
    """Переключить авто-поднятие"""
    # Переключаем
    current = BotConfig.AUTO_BUMP_ENABLED()
    BotConfig.update(**{"auto_bump.enabled": not current})
    
    # Загружаем текущий язык
    
    
    # Уведомление об изменении
    status = "включено" if not current else "выключено"
    await callback.answer(f"Авто-поднятие {status}", show_alert=False)
    
    # Обновляем меню
    auto_bump = not current
    auto_delivery = BotConfig.AUTO_DELIVERY_ENABLED()
    auto_restore = BotConfig.AUTO_RESTORE_ENABLED()
    auto_update = BotConfig.AUTO_UPDATE_ENABLED()
    
    status_text = "⚙️ <b>Глобальные переключатели</b>\n\nЗдесь вы можете включать и отключать основные функции бота.\n\n<b>Текущее состояние:</b>\n✨ Авто-поднятие: {}\n📦 Авто-выдача: {}\n♻️ Авто-восстановление лотов: {}\n🔄 Автообновление: {}".format(
        "включено" if auto_bump else "выключено",
        "включена" if auto_delivery else "выключена",
        "включено" if auto_restore else "выключено",
        "включено" if auto_update else "выключено"
    )
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_global_switches_menu(auto_bump, auto_delivery, auto_restore, auto_update)
    )


@router.callback_query(F.data == CBT.SWITCH_AUTO_DELIVERY)
async def callback_switch_auto_delivery(callback: CallbackQuery):
    """Переключить авто-выдачу"""
    # Переключаем
    current = BotConfig.AUTO_DELIVERY_ENABLED()
    BotConfig.update(**{"auto_delivery.enabled": not current})
    
    # Загружаем текущий язык
    
    
    # Уведомление об изменении
    status = "включена" if not current else "выключена"
    await callback.answer(f"Авто-выдача {status}", show_alert=False)
    
    # Обновляем меню
    auto_bump = BotConfig.AUTO_BUMP_ENABLED()
    auto_delivery = not current
    auto_restore = BotConfig.AUTO_RESTORE_ENABLED()
    auto_update = BotConfig.AUTO_UPDATE_ENABLED()
    
    status_text = "⚙️ <b>Глобальные переключатели</b>\n\nЗдесь вы можете включать и отключать основные функции бота.\n\n<b>Текущее состояние:</b>\n✨ Авто-поднятие: {}\n📦 Авто-выдача: {}\n♻️ Авто-восстановление лотов: {}\n🔄 Автообновление: {}".format(
        "включено" if auto_bump else "выключено",
        "включена" if auto_delivery else "выключена",
        "включено" if auto_restore else "выключено",
        "включено" if auto_update else "выключено"
    )
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_global_switches_menu(auto_bump, auto_delivery, auto_restore, auto_update)
    )


@router.callback_query(F.data == CBT.SWITCH_AUTO_RESTORE)
async def callback_switch_auto_restore(callback: CallbackQuery):
    """Переключить авто-восстановление"""
    # Переключаем
    current = BotConfig.AUTO_RESTORE_ENABLED()
    BotConfig.update(**{"auto_restore.enabled": not current})
    
    # Загружаем текущий язык
    
    
    # Уведомление об изменении
    status = "включено" if not current else "выключено"
    await callback.answer(f"Авто-восстановление {status}", show_alert=False)
    
    # Обновляем меню
    auto_bump = BotConfig.AUTO_BUMP_ENABLED()
    auto_delivery = BotConfig.AUTO_DELIVERY_ENABLED()
    auto_restore = not current
    auto_update = BotConfig.AUTO_UPDATE_ENABLED()
    auto_install = BotConfig.AUTO_UPDATE_INSTALL()
    
    status_text = "⚙️ <b>Глобальные переключатели</b>\n\nЗдесь вы можете включать и отключать основные функции бота.\n\n"
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_global_switches_menu(auto_bump, auto_delivery, auto_restore, auto_update, auto_install)
    )


@router.callback_query(F.data == CBT.SWITCH_AUTO_UPDATE)
async def callback_switch_auto_update(callback: CallbackQuery):
    """Переключить автообновление"""
    # Переключаем
    current = BotConfig.AUTO_UPDATE_ENABLED()
    BotConfig.update(**{"auto_update.enabled": not current})
    
    # Уведомление об изменении
    status = "включено" if not current else "выключено"
    await callback.answer(f"Автообновление {status}", show_alert=False)
    
    # Обновляем меню
    auto_bump = BotConfig.AUTO_BUMP_ENABLED()
    auto_delivery = BotConfig.AUTO_DELIVERY_ENABLED()
    auto_restore = BotConfig.AUTO_RESTORE_ENABLED()
    auto_update = not current
    auto_install = BotConfig.AUTO_UPDATE_INSTALL()
    
    # Загружаем текущий язык
    
    
    status_text = "⚙️ <b>Глобальные переключатели</b>\n\nЗдесь вы можете включать и отключать основные функции бота.\n\n"
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_global_switches_menu(auto_bump, auto_delivery, auto_restore, auto_update, auto_install)
    )


@router.callback_query(F.data == CBT.SWITCH_AUTO_INSTALL)
async def callback_switch_auto_install(callback: CallbackQuery):
    """Переключить автоматическую установку обновлений"""
    # Переключаем
    current = BotConfig.AUTO_UPDATE_INSTALL()
    BotConfig.update(**{"AutoUpdate.auto_install": not current})
    
    # Уведомление об изменении
    status = "включена" if not current else "выключена"
    await callback.answer(f"Авто-установка обновлений {status}", show_alert=False)
    
    # Обновляем меню
    auto_bump = BotConfig.AUTO_BUMP_ENABLED()
    auto_delivery = BotConfig.AUTO_DELIVERY_ENABLED()
    auto_restore = BotConfig.AUTO_RESTORE_ENABLED()
    auto_update = BotConfig.AUTO_UPDATE_ENABLED()
    auto_install = not current
    
    status_text = "⚙️ <b>Глобальные переключатели</b>\n\nЗдесь вы можете включать и отключать основные функции бота.\n\n"
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_global_switches_menu(auto_bump, auto_delivery, auto_restore, auto_update, auto_install)
    )


@router.callback_query(F.data == "empty")
async def callback_empty(callback: CallbackQuery):
    """Пустой callback (для неактивных кнопок)"""
    await callback.answer()


@router.callback_query(F.data == CBT.AUTO_DELIVERY)
async def callback_auto_delivery_menu(callback: CallbackQuery, auto_delivery, **kwargs):
    """Меню автовыдачи"""
    await callback.answer()
    
    lots = await auto_delivery.get_lots()
    
    keyboard = get_auto_delivery_lots_menu(lots, offset=0)
    
    text = "📦 <b>Лоты с автовыдачей</b>\n\n"
    text += f"Всего лотов: <code>{len(lots)}</code>"
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == CBT.BLACKLIST)
async def callback_blacklist_menu(callback: CallbackQuery, **kwargs):
    """Меню чёрного списка"""
    await callback.answer()
    
    # Получаем список из конфига
    blacklist = []
    config = get_config_manager()
    if config._config.has_section("Blacklist"):
        sections = [s for s in config._config.sections() if s.startswith("Blacklist.")]
        
        for section in sections:
            username = section.replace("Blacklist.", "", 1)
            block_delivery = BotConfig.get(f"{section}.block_delivery", True, bool)
            block_response = BotConfig.get(f"{section}.block_response", True, bool)
            
            blacklist.append({
                "username": username,
                "block_delivery": block_delivery,
                "block_response": block_response
            })
    
    keyboard = get_blacklist_menu(blacklist, offset=0)
    
    text = "🚫 <b>Чёрный список</b>\n\n"
    text += f"Заблокировано пользователей: <code>{len(blacklist)}</code>"
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == CBT.PLUGINS)
async def callback_plugins_menu(callback: CallbackQuery, plugin_manager, **kwargs):
    """Меню плагинов"""
    await callback.answer()
    
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
    
    keyboard = get_plugins_menu(plugins_data, offset=0)
    
    enabled_count = sum(1 for p in plugins_data if p["enabled"])
    
    text = "🧩 <b>Плагины</b>\n\n"
    text += f"Всего плагинов: <code>{len(plugins_data)}</code>\n"
    text += f"Активно: <code>{enabled_count}</code>"
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == CBT.NOTIFICATIONS)
async def callback_notifications(callback: CallbackQuery):
    """Меню настроек уведомлений"""
    await callback.answer()
    
    # Загружаем текущий язык
    
    
    # Получаем текущие настройки
    messages = BotConfig.NOTIFY_NEW_MESSAGES()
    orders = BotConfig.NOTIFY_NEW_ORDERS()
    restore = BotConfig.NOTIFY_LOT_RESTORE()
    start = BotConfig.NOTIFY_BOT_START()
    deactivate = BotConfig.NOTIFY_LOT_DEACTIVATE()
    bump = BotConfig.NOTIFY_LOT_BUMP()
    
    # Формируем описание
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


@router.callback_query(F.data == CBT.NOTIF_MESSAGES)
async def callback_notif_messages(callback: CallbackQuery):
    """Переключить уведомления о новых сообщениях"""
    current = BotConfig.NOTIFY_NEW_MESSAGES()
    BotConfig.update(**{"notifications.new_messages": not current})
    
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"Уведомления о сообщениях {status}", show_alert=False)
    
    # Обновляем меню
    messages = not current
    orders = BotConfig.NOTIFY_NEW_ORDERS()
    restore = BotConfig.NOTIFY_LOT_RESTORE()
    start = BotConfig.NOTIFY_BOT_START()
    deactivate = BotConfig.NOTIFY_LOT_DEACTIVATE()
    bump = BotConfig.NOTIFY_LOT_BUMP()
    
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


@router.callback_query(F.data == CBT.NOTIF_ORDERS)
async def callback_notif_orders(callback: CallbackQuery):
    """Переключить уведомления о новых заказах"""
    current = BotConfig.NOTIFY_NEW_ORDERS()
    BotConfig.update(**{"notifications.new_orders": not current})
    
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"Уведомления о заказах {status}", show_alert=False)
    
    # Обновляем меню
    messages = BotConfig.NOTIFY_NEW_MESSAGES()
    orders = not current
    restore = BotConfig.NOTIFY_LOT_RESTORE()
    start = BotConfig.NOTIFY_BOT_START()
    deactivate = BotConfig.NOTIFY_LOT_DEACTIVATE()
    bump = BotConfig.NOTIFY_LOT_BUMP()
    
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


@router.callback_query(F.data == CBT.NOTIF_RESTORE)
async def callback_notif_restore(callback: CallbackQuery):
    """Переключить уведомления о восстановлении лота"""
    current = BotConfig.NOTIFY_LOT_RESTORE()
    BotConfig.update(**{"notifications.lot_restore": not current})
    
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"Уведомления о восстановлении {status}", show_alert=False)
    
    # Обновляем меню
    messages = BotConfig.NOTIFY_NEW_MESSAGES()
    orders = BotConfig.NOTIFY_NEW_ORDERS()
    restore = not current
    start = BotConfig.NOTIFY_BOT_START()
    deactivate = BotConfig.NOTIFY_LOT_DEACTIVATE()
    bump = BotConfig.NOTIFY_LOT_BUMP()
    
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


@router.callback_query(F.data == CBT.NOTIF_START)
async def callback_notif_start(callback: CallbackQuery):
    """Переключить уведомления о запуске бота"""
    current = BotConfig.NOTIFY_BOT_START()
    BotConfig.update(**{"notifications.bot_start": not current})
    
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"Уведомления о запуске {status}", show_alert=False)
    
    # Обновляем меню
    messages = BotConfig.NOTIFY_NEW_MESSAGES()
    orders = BotConfig.NOTIFY_NEW_ORDERS()
    restore = BotConfig.NOTIFY_LOT_RESTORE()
    start = not current
    deactivate = BotConfig.NOTIFY_LOT_DEACTIVATE()
    bump = BotConfig.NOTIFY_LOT_BUMP()
    
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


@router.callback_query(F.data == CBT.NOTIF_DEACTIVATE)
async def callback_notif_deactivate(callback: CallbackQuery):
    """Переключить уведомления о деактивации лота"""
    current = BotConfig.NOTIFY_LOT_DEACTIVATE()
    BotConfig.update(**{"notifications.lot_deactivate": not current})
    
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"Уведомления о деактивации {status}", show_alert=False)
    
    # Обновляем меню
    messages = BotConfig.NOTIFY_NEW_MESSAGES()
    orders = BotConfig.NOTIFY_NEW_ORDERS()
    restore = BotConfig.NOTIFY_LOT_RESTORE()
    start = BotConfig.NOTIFY_BOT_START()
    deactivate = not current
    bump = BotConfig.NOTIFY_LOT_BUMP()
    
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."
    
    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


@router.callback_query(F.data == CBT.NOTIF_BUMP)
async def callback_notif_bump(callback: CallbackQuery):
    """Переключить уведомления о поднятии лота"""
    current = BotConfig.NOTIFY_LOT_BUMP()
    BotConfig.update(**{"notifications.lot_bump": not current})
    
    
    status = "включены" if not current else "выключены"
    await callback.answer(f"Уведомления о поднятии {status}", show_alert=False)
    
    # Обновляем меню
    messages = BotConfig.NOTIFY_NEW_MESSAGES()
    orders = BotConfig.NOTIFY_NEW_ORDERS()
    restore = BotConfig.NOTIFY_LOT_RESTORE()
    start = BotConfig.NOTIFY_BOT_START()
    deactivate = BotConfig.NOTIFY_LOT_DEACTIVATE()
    bump = not current
    
    status_text = "🔔 <b>Настройки уведомлений</b>\n\nНастройте какие уведомления, которые вам нужны получать."

    await callback.message.edit_text(
        status_text,
        reply_markup=get_notifications_menu(messages, orders, restore, start, deactivate, bump)
    )


# === Обработчик кнопки "Ответить" из уведомлений ===

@router.callback_query(F.data.startswith("r:"))
async def handle_reply_button(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Обработка нажатия кнопки 'Ответить' в уведомлении"""
    # Извлекаем chat_id из callback data (формат: r:chat_id)
    chat_id = callback.data.split(":", 1)[1]
    
    # Сохраняем chat_id в состояние
    await state.update_data(reply_chat_id=chat_id)
    await state.set_state(ReplyState.waiting_for_reply)
    
    await callback.answer()
    await callback.message.answer(
        "✍️ <b>Быстрый ответ</b>\n\n"
        "Отправьте сообщение, которое хотите отправить пользователю.\n\n"
        "Для отмены используйте /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="reply_cancel")]
        ])
    )


@router.callback_query(F.data == "reply_cancel")
async def handle_reply_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена быстрого ответа"""
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.delete()


@router.message(ReplyState.waiting_for_reply)
async def process_quick_reply(message: Message, state: FSMContext, **kwargs):
    """Обработка отправки быстрого ответа"""
    # Получаем starvell из kwargs
    starvell = kwargs.get('starvell')
    
    if not starvell:
        await message.answer("❌ Ошибка: сервис Starvell недоступен")
        await state.clear()
        return
    
    # Получаем сохраненный chat_id
    data = await state.get_data()
    chat_id = data.get("reply_chat_id")
    
    if not chat_id:
        await message.answer("❌ Ошибка: не удалось определить чат")
        await state.clear()
        return
    
    # Отправляем сообщение
    try:
        status_msg = await message.answer("📤 Отправка сообщения...")
        
        result = await starvell.send_message(chat_id, message.text)
        
        await status_msg.edit_text(
            "✅ <b>Сообщение отправлено!</b>\n\n"
            f"💬 Текст: <code>{message.text[:100]}</code>"
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")
        await state.clear()


# === Обработчик кнопки "Вернуть деньги" ===

@router.callback_query(F.data.startswith("refund:"))
async def handle_refund_button(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Вернуть деньги' - запрос подтверждения"""
    # Извлекаем короткий ID заказа
    short_order_id = callback.data.split(":", 1)[1]
    
    # Создаем кнопки подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, вернуть",
                callback_data=f"refund_confirm:{short_order_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="refund_cancel"
            )
        ]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=confirm_keyboard)
    await callback.answer("⚠️ Подтвердите возврат денег", show_alert=True)


@router.callback_query(F.data.startswith("confirm:"))
async def handle_confirm_order(callback: CallbackQuery, **kwargs):
    """Обработка подтверждения заказа"""
    short_order_id = callback.data.split(":", 1)[1]
    
    # Получаем starvell из kwargs
    starvell = kwargs.get('starvell')
    
    if not starvell:
        await callback.answer("❌ Ошибка: сервис Starvell недоступен", show_alert=True)
        return
    
    try:
        # Подтверждаем заказ
        await callback.answer("⏳ Подтверждение заказа...", show_alert=False)
        
        result = await starvell.confirm_order(short_order_id)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Заказ подтверждён!</b>",
            reply_markup=None
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка при подтверждении: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("refund_confirm:"))
async def handle_refund_confirm(callback: CallbackQuery, **kwargs):
    """Подтверждение возврата денег"""
    short_order_id = callback.data.split(":", 1)[1]
    
    # Получаем starvell из kwargs
    starvell = kwargs.get('starvell')
    
    if not starvell:
        await callback.answer("❌ Ошибка: сервис Starvell недоступен", show_alert=True)
        return
    
    try:
        # Выполняем возврат
        await callback.answer("⏳ Выполняется возврат...", show_alert=False)
        
        result = await starvell.refund_order(short_order_id)
        
        # Обновляем сообщение
        await callback.message.edit_text(
            callback.message.text + "\n\n💰 <b>Деньги возвращены!</b>",
            reply_markup=None
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка при возврате: {str(e)}", show_alert=True)
        # Восстанавливаем исходные кнопки
        await callback.message.edit_reply_markup(reply_markup=callback.message.reply_markup)


@router.callback_query(F.data == "refund_cancel")
async def handle_refund_cancel(callback: CallbackQuery):
    """Отмена возврата денег"""
    # Восстанавливаем исходные кнопки
    await callback.message.edit_reply_markup(reply_markup=callback.message.reply_markup)
    await callback.answer("Отменено")


