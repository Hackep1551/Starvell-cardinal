"""
Обработчики для дополнительных функций
(автоответы, конфиги, авторизованные пользователи)
"""

import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import (
    get_main_menu_page_2,
    get_main_menu_page_3,
    get_order_confirm_response_menu,
    get_review_response_menu,
    get_welcome_message_menu,
    get_configs_menu,
    get_authorized_users_menu,
    get_proxy_menu,
    CBT,
)
from bot.core.config import BotConfig, get_config_manager


router = Router()


class EditTextStates(StatesGroup):
    """Состояния для редактирования текстов"""
    waiting_for_order_confirm_text = State()
    waiting_for_review_text = State()
    waiting_for_welcome_text = State()
    waiting_for_config = State()


class ProxyState(StatesGroup):
    """Состояния для настройки прокси"""
    waiting_for_proxy = State()


# === Вторая страница главного меню ===

@router.callback_query(F.data == CBT.MAIN_PAGE_2)
async def callback_main_page_2(callback: CallbackQuery):
    """Вторая страница главного меню"""
    await callback.answer()
    
    # Проверяем наличие обновлений
    # (можно добавить проверку позже)
    update_available = False
    
    await callback.message.edit_text(
        "⚙️ <b>Дополнительные настройки</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=get_main_menu_page_2(update_available)
    )


@router.callback_query(F.data == CBT.MAIN_PAGE_3)
async def callback_main_page_3(callback: CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "🧩 <b>Системные настройки</b>\n\n"
        "Выберите нужный раздел:",
        reply_markup=get_main_menu_page_3(False)
    )


# === Ответ на подтверждение заказа ===

@router.callback_query(F.data == CBT.ORDER_CONFIRM_RESPONSE)
async def callback_order_confirm_response(callback: CallbackQuery):
    """Меню настройки ответа на подтверждение заказа"""
    await callback.answer()
    
    enabled = BotConfig.ORDER_CONFIRM_RESPONSE_ENABLED()
    text = BotConfig.ORDER_CONFIRM_RESPONSE_TEXT()
    
    message_text = (
        "✅ <b>Ответ на подтверждение заказа</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Текущий текст ответа:</b>\n<i>{text}</i>\n\n"
        "При завершении заказа бот автоматически отправит это сообщение покупателю."
    )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=get_order_confirm_response_menu(enabled, text)
    )


@router.callback_query(F.data == "edit_order_confirm_text")
async def callback_edit_order_confirm_text(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование текста ответа на подтверждение"""
    await callback.answer()
    
    await state.set_state(EditTextStates.waiting_for_order_confirm_text)
    
    await callback.message.edit_text(
        "✏️ <b>Изменение текста ответа на подтверждение заказа</b>\n\n"
        "Отправьте новый текст сообщения, которое будет отправляться покупателю "
        "после завершения заказа."
    )


@router.message(EditTextStates.waiting_for_order_confirm_text)
async def process_order_confirm_text(message: Message, state: FSMContext):
    """Обработка нового текста ответа на подтверждение"""
    text = message.text.strip()
    
    if not text or len(text) > 4096:
        await message.answer(
            "❌ Текст должен быть от 1 до 4096 символов. Попробуйте ещё раз:"
        )
        return
    
    # Сохраняем
    BotConfig.update(**{"AutoResponse.orderConfirmText": text})
    
    await state.clear()
    
    enabled = BotConfig.ORDER_CONFIRM_RESPONSE_ENABLED()
    
    message_text = (
        "✅ <b>Текст успешно изменён!</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Новый текст ответа:</b>\n<i>{text}</i>"
    )
    
    await message.answer(
        message_text,
        reply_markup=get_order_confirm_response_menu(enabled, text)
    )


# === Ответ на отзыв ===

@router.callback_query(F.data == CBT.REVIEW_RESPONSE)
async def callback_review_response(callback: CallbackQuery):
    """Меню настройки ответа на отзыв"""
    await callback.answer()
    
    enabled = BotConfig.REVIEW_RESPONSE_ENABLED()
    text = BotConfig.REVIEW_RESPONSE_TEXT()
    
    message_text = (
        "⭐ <b>Ответ на отзыв</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Текущий текст ответа:</b>\n<i>{text}</i>\n\n"
        "При получении отзыва бот автоматически отправит это сообщение."
    )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=get_review_response_menu(enabled, text)
    )


@router.callback_query(F.data == "edit_review_text")
async def callback_edit_review_text(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование текста ответа на отзыв"""
    await callback.answer()
    
    await state.set_state(EditTextStates.waiting_for_review_text)
    
    await callback.message.edit_text(
        "✏️ <b>Изменение текста ответа на отзыв</b>\n\n"
        "Отправьте новый текст сообщения, которое будет отправляться "
        "в ответ на отзыв."
    )


@router.message(EditTextStates.waiting_for_review_text)
async def process_review_text(message: Message, state: FSMContext):
    """Обработка нового текста ответа на отзыв"""
    text = message.text.strip()
    
    if not text or len(text) > 4096:
        await message.answer(
            "❌ Текст должен быть от 1 до 4096 символов. Попробуйте ещё раз:"
        )
        return
    
    # Сохраняем
    BotConfig.update(**{"AutoResponse.reviewResponseText": text})
    
    await state.clear()
    
    enabled = BotConfig.REVIEW_RESPONSE_ENABLED()
    
    message_text = (
        "✅ <b>Текст успешно изменён!</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Новый текст ответа:</b>\n<i>{text}</i>"
    )
    
    await message.answer(
        message_text,
        reply_markup=get_review_response_menu(enabled, text)
    )


# === Приветственное сообщение ===

@router.callback_query(F.data == CBT.WELCOME_MESSAGE)
async def callback_welcome_message(callback: CallbackQuery):
    """Меню настройки приветственного сообщения"""
    await callback.answer()

    enabled = BotConfig.WELCOME_MESSAGE_ENABLED()
    text = BotConfig.WELCOME_MESSAGE_TEXT()

    message_text = (
        "👋 <b>Приветственное сообщение</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Текущий текст:</b>\n<i>{text}</i>\n\n"
        "При первом сообщении покупателя бот автоматически отправит это приветствие.\n\n"
        "Доступные переменные: <code>$username</code>, <code>$date</code>, <code>$time</code>"
    )

    await callback.message.edit_text(
        message_text,
        reply_markup=get_welcome_message_menu(enabled, text)
    )


@router.callback_query(F.data == CBT.SWITCH_WELCOME_MESSAGE)
async def callback_switch_welcome_message(callback: CallbackQuery):
    """Переключить приветственное сообщение"""
    current = BotConfig.WELCOME_MESSAGE_ENABLED()
    BotConfig.update(**{"WelcomeMessage.enabled": not current})

    status = "включено" if not current else "выключено"
    await callback.answer(f"Приветствие {status}", show_alert=False)

    enabled = not current
    text = BotConfig.WELCOME_MESSAGE_TEXT()

    message_text = (
        "👋 <b>Приветственное сообщение</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Текущий текст:</b>\n<i>{text}</i>\n\n"
        "При первом сообщении покупателя бот автоматически отправит это приветствие.\n\n"
        "Доступные переменные: <code>$username</code>, <code>$date</code>, <code>$time</code>"
    )

    await callback.message.edit_text(
        message_text,
        reply_markup=get_welcome_message_menu(enabled, text)
    )


@router.callback_query(F.data == "edit_welcome_text")
async def callback_edit_welcome_text(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование текста приветствия"""
    await callback.answer()

    await state.set_state(EditTextStates.waiting_for_welcome_text)

    await callback.message.edit_text(
        "✏️ <b>Изменение текста приветствия</b>\n\n"
        "Отправьте новый текст сообщения, которое будет отправляться "
        "покупателю при первом сообщении.\n\n"
        "Доступные переменные: <code>$username</code>, <code>$date</code>, <code>$time</code>"
    )


@router.message(EditTextStates.waiting_for_welcome_text)
async def process_welcome_text(message: Message, state: FSMContext):
    """Обработка нового текста приветствия"""
    text = message.text.strip()

    if not text or len(text) > 4096:
        await message.answer(
            "❌ Текст должен быть от 1 до 4096 символов. Попробуйте ещё раз:"
        )
        return

    # Сохраняем
    BotConfig.update(**{"WelcomeMessage.text": text})

    await state.clear()

    enabled = BotConfig.WELCOME_MESSAGE_ENABLED()

    message_text = (
        "✅ <b>Текст успешно изменён!</b>\n\n"
        f"<b>Статус:</b> {'включено ✅' if enabled else 'выключено ❌'}\n\n"
        f"<b>Новый текст приветствия:</b>\n<i>{text}</i>"
    )

    await message.answer(
        message_text,
        reply_markup=get_welcome_message_menu(enabled, text)
    )


# === Конфиги ===

@router.callback_query(F.data == CBT.CONFIGS_MENU)
async def callback_configs_menu(callback: CallbackQuery):
    """Меню управления конфигами"""
    await callback.answer()
    
    await callback.message.edit_text(
        "📁 <b>Управление конфигами</b>\n\n"
        "• <b>Скачать конфиг</b> - получить текущий файл _main.cfg\n"
        "• <b>Загрузить конфиг</b> - заменить текущий конфиг новым\n\n"
        "⚠️ <b>Внимание!</b> При загрузке нового конфига старый будет удалён!",
        reply_markup=get_configs_menu()
    )


@router.callback_query(F.data == CBT.CONFIG_DOWNLOAD)
async def callback_config_download(callback: CallbackQuery):
    """Скачать конфиг"""
    config_manager = get_config_manager()
    config_path = config_manager.config_path
    
    if not config_path.exists():
        await callback.answer("❌ Файл конфига не найден!", show_alert=True)
        return
    
    await callback.answer()
    
    # Отправляем файл
    await callback.message.answer_document(
        FSInputFile(config_path),
        caption="📁 <b>Файл конфигурации _main.cfg</b>\n\n"
                "Сохраните этот файл в надёжном месте."
    )


@router.callback_query(F.data == CBT.CONFIG_UPLOAD)
async def callback_config_upload(callback: CallbackQuery, state: FSMContext):
    """Начать загрузку конфига"""
    await callback.answer()
    
    await state.set_state(EditTextStates.waiting_for_config)
    
    await callback.message.edit_text(
        "📤 <b>Загрузка конфига</b>\n\n"
        "Отправьте файл <code>_main.cfg</code> в чат.\n\n"
        "⚠️ <b>Внимание!</b> Текущий конфиг будет удалён и заменён новым. "
        "Бот будет перезапущен."
    )


@router.message(EditTextStates.waiting_for_config)
async def process_config_upload(message: Message, state: FSMContext, bot):
    """Обработка загрузки конфига"""
    if not message.document:
        await message.answer(
            "❌ Пожалуйста, отправьте файл конфигурации."
        )
        return
    
    # Проверяем расширение
    if not message.document.file_name.endswith('.cfg'):
        await message.answer(
            "❌ Файл должен иметь расширение .cfg"
        )
        return
    
    await state.clear()
    
    # Скачиваем файл
    file = await bot.get_file(message.document.file_id)
    
    config_manager = get_config_manager()
    config_path = config_manager.config_path
    
    # Удаляем старый конфиг
    if config_path.exists():
        config_path.unlink()
    
    # Сохраняем новый
    await bot.download_file(file.file_path, config_path)
    
    await message.answer(
        "✅ <b>Конфиг успешно загружен!</b>\n\n"
        "Бот будет перезапущен через 3 секунды..."
    )
    
    # Перезапуск бота
    import asyncio
    import sys
    import os
    await asyncio.sleep(3)
    os.execv(sys.executable, [sys.executable] + sys.argv)


# === Авторизованные пользователи ===

@router.callback_query(F.data == CBT.AUTHORIZED_USERS)
async def callback_authorized_users(callback: CallbackQuery):
    """Меню авторизованных пользователей"""
    await callback.answer()
    
    admin_ids = BotConfig.ADMIN_IDS()
    
    if admin_ids:
        message_text = (
            "👥 <b>Авторизованные пользователи</b>\n\n"
            f"Всего авторизовано: <b>{len(admin_ids)}</b>\n\n"
            "Нажмите 🗑️ чтобы удалить пользователя."
        )
    else:
        message_text = (
            "👥 <b>Авторизованные пользователи</b>\n\n"
            "Список пуст."
        )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=get_authorized_users_menu(admin_ids)
    )


@router.callback_query(F.data.startswith(f"{CBT.REMOVE_AUTH_USER}:"))
async def callback_remove_auth_user(callback: CallbackQuery):
    """Удалить авторизованного пользователя"""
    user_id = int(callback.data.split(":")[1])
    
    admin_ids = BotConfig.ADMIN_IDS()
    
    if user_id not in admin_ids:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Удаляем
    admin_ids.remove(user_id)
    BotConfig.update(**{"Telegram.adminIds": admin_ids})
    
    await callback.answer(f"✅ Пользователь {user_id} удалён", show_alert=False)
    
    # Обновляем меню
    if admin_ids:
        message_text = (
            "👥 <b>Авторизованные пользователи</b>\n\n"
            f"Всего авторизовано: <b>{len(admin_ids)}</b>\n\n"
            "Нажмите 🗑️ чтобы удалить пользователя."
        )
    else:
        message_text = (
            "👥 <b>Авторизованные пользователи</b>\n\n"
            "Список пуст."
        )
    
    await callback.message.edit_text(
        message_text,
        reply_markup=get_authorized_users_menu(admin_ids)
    )


# === Прокси ===

def _proxy_menu_text() -> str:
    enabled = BotConfig.PROXY_ENABLED()
    ip = BotConfig.PROXY_IP()
    port = BotConfig.PROXY_PORT()
    proxy_type = BotConfig.PROXY_TYPE()
    login = BotConfig.PROXY_LOGIN()
    status = "включён ✅" if enabled else "выключен ❌"
    addr = f"{proxy_type}://{ip}:{port}" if ip and port else "не настроен"
    auth = f"\n<b>Логин:</b> {login}" if login else ""
    return (
        "🔒 <b>Настройка прокси</b>\n\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Адрес:</b> <code>{addr}</code>{auth}\n\n"
        "⚠️ Прокси используется для доступа к Telegram и применяется "
        "<b>только после перезапуска бота</b>.\n\n"
        "Чтобы добавить или изменить прокси, нажмите кнопку ниже и введите адрес в формате:\n"
        "<code>тип://логин:пароль@ip:порт</code>\n"
        "или <code>тип://ip:порт</code>\n"
        "Например: <code>socks5://1.2.3.4:1080</code>\n"
        "или <code>socks5://user:pass@1.2.3.4:1080</code>"
    )


@router.callback_query(F.data == CBT.PROXY)
async def callback_proxy_menu(callback: CallbackQuery):
    """Меню прокси"""
    await callback.answer()
    enabled = BotConfig.PROXY_ENABLED()
    ip = BotConfig.PROXY_IP()
    port = BotConfig.PROXY_PORT()
    proxy_type = BotConfig.PROXY_TYPE()
    proxy_set = bool(ip and port)
    await callback.message.edit_text(
        _proxy_menu_text(),
        reply_markup=get_proxy_menu(enabled, proxy_set, proxy_type, ip, port)
    )


@router.callback_query(F.data == CBT.PROXY_ENABLE)
async def callback_proxy_enable(callback: CallbackQuery):
    """Включить прокси"""
    await callback.answer()
    BotConfig.set_proxy(
        ip=BotConfig.PROXY_IP(),
        port=BotConfig.PROXY_PORT(),
        login=BotConfig.PROXY_LOGIN(),
        password=BotConfig.PROXY_PASSWORD(),
        enabled=True,
        proxy_type=BotConfig.PROXY_TYPE(),
    )
    ip = BotConfig.PROXY_IP()
    port = BotConfig.PROXY_PORT()
    await callback.message.edit_text(
        _proxy_menu_text(),
        reply_markup=get_proxy_menu(True, bool(ip and port), BotConfig.PROXY_TYPE(), ip, port)
    )


@router.callback_query(F.data == CBT.PROXY_DISABLE)
async def callback_proxy_disable(callback: CallbackQuery):
    """Выключить прокси"""
    await callback.answer()
    BotConfig.set_proxy(
        ip=BotConfig.PROXY_IP(),
        port=BotConfig.PROXY_PORT(),
        login=BotConfig.PROXY_LOGIN(),
        password=BotConfig.PROXY_PASSWORD(),
        enabled=False,
        proxy_type=BotConfig.PROXY_TYPE(),
    )
    ip = BotConfig.PROXY_IP()
    port = BotConfig.PROXY_PORT()
    await callback.message.edit_text(
        _proxy_menu_text(),
        reply_markup=get_proxy_menu(False, bool(ip and port), BotConfig.PROXY_TYPE(), ip, port)
    )


@router.callback_query(F.data == CBT.PROXY_ADD)
async def callback_proxy_add(callback: CallbackQuery, state: FSMContext):
    """Начать ввод прокси"""
    await callback.answer()
    await state.set_state(ProxyState.waiting_for_proxy)
    await callback.message.edit_text(
        "🔒 <b>Добавление прокси</b>\n\n"
        "Введите прокси в одном из форматов:\n"
        "<code>socks5://ip:порт</code>\n"
        "<code>socks4://ip:порт</code>\n"
        "<code>http://ip:порт</code>\n"
        "<code>socks5://логин:пароль@ip:порт</code>\n\n"
        "Для отмены отправьте /cancel"
    )


@router.message(ProxyState.waiting_for_proxy)
async def process_proxy_input(message: Message, state: FSMContext):
    """Обработка введённого прокси"""
    import re
    text = message.text.strip() if message.text else ""

    if text == "/cancel":
        await state.clear()
        enabled = BotConfig.PROXY_ENABLED()
        ip = BotConfig.PROXY_IP()
        port = BotConfig.PROXY_PORT()
        proxy_type = BotConfig.PROXY_TYPE()
        proxy_set = bool(ip and port)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.answer(
            "❌ Отменено.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔒 К настройкам прокси", callback_data=CBT.PROXY)]
            ])
        )
        return

    pattern = re.compile(
        r'^(socks5|socks4|http)://'
        r'(?:([^:@]+):([^@]*)@)?'
        r'([\w\d\.\-]+):(\d{1,5})$',
        re.IGNORECASE
    )
    m = pattern.match(text)
    if not m:
        await message.answer(
            "❌ Неверный формат. Примеры:\n"
            "<code>socks5://1.2.3.4:1080</code>\n"
            "<code>socks5://user:pass@1.2.3.4:1080</code>\n\n"
            "Попробуйте ещё раз или отправьте /cancel"
        )
        return

    proxy_type, login, password, ip, port = m.group(1).lower(), m.group(2) or '', m.group(3) or '', m.group(4), m.group(5)

    BotConfig.set_proxy(
        ip=ip,
        port=port,
        login=login,
        password=password,
        enabled=True,
        proxy_type=proxy_type,
    )
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.answer(
        f"✅ <b>Прокси сохранён и включён!</b>\n\n"
        f"<b>Тип:</b> {proxy_type}\n"
        f"<b>Адрес:</b> <code>{ip}:{port}</code>"
        + (f"\n<b>Логин:</b> {login}" if login else "")
        + "\n\n⚠️ Чтобы прокси заработал, нужно перезапустить бота.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перезапустить бота", callback_data=CBT.PROXY_RESTART)],
            [InlineKeyboardButton(text="🔒 К настройкам прокси", callback_data=CBT.PROXY)]
        ])
    )


@router.callback_query(F.data == CBT.PROXY_RESTART)
async def callback_proxy_restart(callback: CallbackQuery):
    """Перезапустить бота, чтобы применить настройки прокси"""
    await callback.answer("Перезапускаю бота...", show_alert=False)
    await callback.message.edit_text(
        "🔄 <b>Перезапуск бота</b>\n\n"
        "Применяю настройки прокси. Бот будет доступен через несколько секунд."
    )

    import asyncio
    import sys
    import os
    await asyncio.sleep(2)
    os.execv(sys.executable, [sys.executable] + sys.argv)
