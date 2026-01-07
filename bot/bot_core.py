"""
Главный файл бота
"""

import asyncio
import logging
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.core.config import BotConfig, get_config_manager
from bot.core import init_notifications, NotificationType
from bot.core.storage import Database
from bot.core.services import StarvellService
from bot.handlers import router
from bot.core.middlewares import AuthMiddleware
from bot.features.tasks import BackgroundTasks
from bot.features.auto_delivery import AutoDeliveryService
from bot.features.auto_restore import AutoRestoreService
from bot.features.auto_raise import AutoRaiseService
from bot.features.auto_update import AutoUpdateService
from bot.features.keep_alive import KeepAliveService
from bot.plugins import PluginManager, init_plugins_cp


logger = logging.getLogger(__name__)


async def main():
    """Главная функция бота (вызывается из главного main.py)"""
    
    # Валидация конфигурации
    try:
        BotConfig.validate()
        BotConfig.ensure_dirs()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        logger.error("Проверьте configs/_main.cfg")
        return
        
    logger.info("=" * 60)
    logger.info("Запуск Starvell Bot")
    logger.info("=" * 60)
    
    # Инициализация компонентов
    bot = Bot(
        token=BotConfig.BOT_TOKEN(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Устанавливаем меню команд
    commands = [
        BotCommand(command="menu", description="🏠 Главное меню"),
        BotCommand(command="changelog", description="📝 Список изменений"),
        BotCommand(command="update", description="🔄 Обновить бота"),
        BotCommand(command="logs", description="📋 Получить логи"),
        BotCommand(command="restart", description="🔁 Перезапустить бота"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Меню команд установлено")
    
    # Устанавливаем описание и "что может делать бот"
    try:
        # Короткое описание (показывается в списке ботов) - БЕЗ HTML!
        await bot.set_my_short_description(
            "🤖 Starvell Cardinal - автоматизация для Starvell.com"
        )
        
        # Полное описание (показывается при открытии бота)
        description = (
            "🔥 Starvell Cardinal - мощный бот для автоматизации работы на Starvell.com\n\n"
            "Контакты:\n"
            "🛠 github.com/Hackep1551/Starvell-cardinal\n"
            "💬 @kapystus"
        )
        await bot.set_my_description(description)
        logger.info("Описание бота установлено")
    except Exception as e:
        logger.warning(f"Не удалось установить описание бота: {e}")
    
    # База данных (JSON хранилище)
    db = Database(storage_dir=BotConfig.STORAGE_DIR())
    await db.connect()
    
    # Сервис Starvell
    starvell = StarvellService(db)
    
    # Инициализация системы уведомлений
    from bot.core import init_notifications
    notifications = init_notifications(bot, starvell)
    logger.info("Система уведомлений инициализирована")
    
    # Сервис авто-выдачи (без зависимостей)
    auto_delivery = AutoDeliveryService()
    
    # Сервис авто-восстановления (требует auto_delivery для проверки товаров)
    auto_restore = AutoRestoreService(starvell, auto_delivery)
    
    # Сервис авто-поднятия
    auto_raise = AutoRaiseService(starvell)
    
    # Сервис автообновления
    auto_update = AutoUpdateService(notifications)
    
    # Сервис вечного онлайна
    keep_alive = KeepAliveService(starvell)
    
    # Менеджер плагинов
    plugin_manager = PluginManager()
    plugin_manager.load_plugins()
    
    # Устанавливаем plugin_manager в notifications для вызова хэндлеров
    notifications.plugin_manager = plugin_manager
    
    # Инициализируем панель управления плагинами
    init_plugins_cp(bot, plugin_manager, router)
    logger.info("Панель управления плагинами инициализирована")
    
    # Регистрируем хэндлеры плагинов (включая команды)
    plugin_manager.register_handlers(router)
    logger.info("Хэндлеры плагинов зарегистрированы")
    
    try:
        await starvell.start()
        await auto_delivery.start()
        await auto_restore.start()
        await auto_raise.start()
        await auto_update.start()
        await keep_alive.start()
        
        # Запускаем хэндлеры инициализации плагинов
        plugin_manager.run_handlers(plugin_manager.init_handlers, bot, starvell, db, plugin_manager)
        
        # Проверяем авторизацию
        user_info = await starvell.get_user_info()
        if not user_info.get("authorized"):
            logger.error("Не удалось авторизоваться в Starvell!")
            logger.error("Проверьте session_cookie в configs/_main.cfg")
            await starvell.stop()
            await db.close()
            return
            
        user = user_info.get("user", {})
        logger.info(f"Авторизован как: {user.get('username')} (ID: {user.get('id')})")
        
    except Exception as e:
        logger.error(f"Ошибка при подключении к Starvell: {e}")
        logger.exception("Детальная информация об ошибке:")
        await keep_alive.stop()
        await auto_update.stop()
        await auto_raise.stop()
        await auto_restore.stop()
        await auto_delivery.stop()
        await starvell.stop()
        await db.close()
        return
        
    # Middleware для проверки доступа
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Регистрируем роутер
    dp.include_router(router)
    
    # Добавляем зависимости в контекст
    dp.workflow_data.update({
        "starvell": starvell,
        "db": db,
        "auto_delivery": auto_delivery,
        "auto_restore": auto_restore,
        "auto_raise": auto_raise,
        "auto_update": auto_update,
        "plugin_manager": plugin_manager,
    })
    
    # Фоновые задачи
    tasks = BackgroundTasks(bot, starvell, db, notifications)
    tasks.start()
    
    # Уведомляем админов о запуске
    if BotConfig.NOTIFY_BOT_START():
        try:
            await notifications.notify_all_admins(
                NotificationType.BOT_STARTED,
                f"Аккаунт: {user.get('username')}\n"
                f"ID: {user.get('id')}\n",
                force=False
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление о запуске: {e}")
            
    logger.info("✅ Бот успешно запущен!")
    
    # Запускаем хэндлеры старта плагинов
    plugin_manager.run_handlers(plugin_manager.start_handlers, bot, starvell, db, plugin_manager)
    
    try:
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        # Очистка
        logger.info("Остановка бота...")
        
        # Запускаем хэндлеры остановки плагинов
        plugin_manager.run_handlers(plugin_manager.stop_handlers, bot, starvell, db, plugin_manager)
        
        tasks.stop()
        await keep_alive.stop()
        await auto_update.stop()
        await auto_raise.stop()
        await auto_restore.stop()
        await auto_delivery.stop()
        await starvell.stop()
        await db.close()
        
        # Уведомляем админов об остановке
        from bot.core import get_notification_manager
        notif_manager = get_notification_manager()
        if notif_manager:
            try:
                await notif_manager.notify_all_admins(
                    NotificationType.BOT_STOPPED,
                    "Бот был остановлен администратором.",
                    force=True
                )
            except:
                pass
        
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
