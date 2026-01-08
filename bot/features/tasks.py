"""
Фоновые задачи бота
"""

import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.core.config import BotConfig, get_config_manager
from bot.core.services import StarvellService
from bot.core.storage import Database


logger = logging.getLogger(__name__)

# Настраиваем уровень логирования планировщика в зависимости от режима DEBUG
if BotConfig.DEBUG():
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
else:
    logging.getLogger('apscheduler').setLevel(logging.ERROR)


class BackgroundTasks:
    """Управление фоновыми задачами"""
    
    def __init__(self, bot: Bot, starvell: StarvellService, db: Database, notifier=None, auto_response=None):
        self.bot = bot
        self.starvell = starvell
        self.db = db
        self.notifier = notifier
        self.auto_response = auto_response
        self.scheduler = AsyncIOScheduler()
        self._seen_messages: dict[str, set[str]] = {}  # chat_id -> set of message_ids
        
    def start(self):
        """Запустить фоновые задачи"""
        # Проверка новых сообщений 
        chat_interval = get_config_manager().get('Monitor', 'chatPollInterval', 5)
        self.scheduler.add_job(
            self._check_new_messages_loop,
            'interval',
            seconds=max(1, int(chat_interval)),
            id='check_messages',
        )
        
        # Проверка новых заказов 
        orders_interval = get_config_manager().get('Monitor', 'ordersPollInterval', 10)
        self.scheduler.add_job(
            self._check_new_orders_loop,
            'interval',
            seconds=max(1, int(orders_interval)),
            id='check_orders',
        )
        
        # Авто-bump офферов
        if BotConfig.AUTO_BUMP_ENABLED():
            self.scheduler.add_job(
                self._auto_bump,
                'interval',
                seconds=BotConfig.AUTO_BUMP_INTERVAL(),
                id='auto_bump',
            )
        
        # Проверка автоответов (каждые 30 секунд)
        if self.auto_response:
            self.scheduler.add_job(
                self._check_auto_responses,
                'interval',
                seconds=30,
                id='auto_responses',
            )
            
        # Очистка старых данных (раз в день)
        self.scheduler.add_job(
            self._cleanup_old_data,
            'cron',
            hour=3,
            minute=0,
            id='cleanup',
        )
        
        self.scheduler.start()
        logger.info("Фоновые задачи запущены")
        
    def stop(self):
        """Остановить фоновые задачи"""
        self.scheduler.shutdown()
        logger.info("Фоновые задачи остановлены")
        
    async def _check_new_messages_loop(self):
        """Polling цикл для проверки новых сообщений"""
        try:
            # Проверяем только если уведомления включены
            if not BotConfig.NOTIFY_NEW_MESSAGES():
                return
                
            await self._check_new_messages()
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке сообщений: {e}", exc_info=True)
            
    async def _check_new_orders_loop(self):
        """Polling цикл для проверки новых заказов """
        try:
            # Проверяем только если уведомления включены
            if not BotConfig.NOTIFY_NEW_ORDERS():
                return
                
            await self._check_new_orders()
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке заказов: {e}", exc_info=True)
            
    async def _check_new_messages(self):
        """Проверка новых сообщений"""
        try:
            new_messages = await self.starvell.check_new_messages()
            
            if not self.notifier:
                logger.warning("Менеджер уведомлений не инициализирован")
                return
            
            for msg_data in new_messages:
                chat_id = str(msg_data.get("chat_id", ""))
                message = msg_data.get("message", {})
                chat = msg_data.get("chat", {})
                
                author_id = message.get("authorId", "N/A")
                content = message.get("content") or message.get("text", "")
                message_id = message.get("id")
                
                # Пропускаем сообщения без контента
                if not content:
                    continue
                
                # Проверяем черный список по ID
                config = get_config_manager()
                blacklist_section = f"Blacklist.{author_id}"
                if config._config.has_section(blacklist_section):
                    logger.debug(f"Сообщение от пользователя {author_id} игнорируется (в черном списке)")
                    continue
                
                # Получаем nickname из данных чата
                # Структура может быть: chat.companion.nickname или chat.members[].nickname
                author_nickname = None
                if chat:
                    # Пробуем получить companion (для личных чатов)
                    companion = chat.get("companion", {})
                    if companion and str(companion.get("id")) == str(author_id):
                        author_nickname = companion.get("nickname") or companion.get("name")
                    
                    # Пробуем найти в members (для групповых чатов)
                    if not author_nickname:
                        members = chat.get("members", [])
                        for member in members:
                            if str(member.get("id")) == str(author_id):
                                author_nickname = member.get("nickname") or member.get("name")
                                break
                
                # Пропускаем свои сообщения
                try:
                    user_info = await self.starvell.get_user_info()
                    if str(author_id) == str(user_info.get("user", {}).get("id")):
                        continue
                except Exception:
                    pass
                
                # Проверяем, не уведомляли ли уже об этом сообщении
                if chat_id not in self._seen_messages:
                    self._seen_messages[chat_id] = set()
                    
                if message_id and message_id in self._seen_messages[chat_id]:
                    continue
                    
                # Отправляем уведомление через NotificationManager
                await self.notifier.notify_new_message(
                    chat_id=chat_id,
                    author=str(author_id),
                    content=content,
                    message_id=str(message_id) if message_id else None,
                    author_nickname=author_nickname
                )
                
                # Запоминаем это сообщение
                if message_id:
                    self._seen_messages[chat_id].add(message_id)
                    
                # Проверяем кастомные команды
                await self._check_custom_command(chat_id, content, author_id)
                    
                # Логируем
                display_name = author_nickname or author_id
                logger.info(f"📩 Новое сообщение от {display_name}: {content[:50]}...")
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке новых сообщений: {e}", exc_info=True)
            
    async def _check_new_orders(self):
        """Проверка новых заказов"""
        try:
            new_orders = await self.starvell.check_new_orders()
            
            if not self.notifier:
                logger.warning("Менеджер уведомлений не инициализирован")
                return
            
            for order in new_orders:
                order_id = str(order.get("id", ""))
                if not order_id:
                    continue
                
                status = order.get("status", "CREATED")
                
                # Отправляем уведомление ТОЛЬКО при статусе CREATED
                if status != "CREATED":
                    continue
                
                # Получаем короткий ID (последние 8 символов без дефисов)
                short_id = order.get("shortId", "")
                if not short_id:
                    # Берём последние 8 символов ID (без дефисов)
                    clean_id = order_id.replace("-", "")
                    short_id = clean_id[-8:].upper() if len(clean_id) >= 8 else order_id[:8].upper()
                
                # Получаем цену (API возвращает в копейках, конвертируем в рубли)
                # basePrice - ваш доход, totalPrice - сколько заплатил покупатель
                amount_kopecks = order.get("totalPrice") or order.get("basePrice") or order.get("price") or order.get("amount") or 0
                amount = amount_kopecks / 100  # Конвертируем копейки в рубли
                
                # Debug: логируем все поля цены
                logger.debug(f"Поля цены в заказе {order_id[:8]}: totalPrice={order.get('totalPrice')}, basePrice={order.get('basePrice')} (конвертировано: {amount} ₽)")
                
                # Получаем данные покупателя (поле "user" согласно API)
                buyer = order.get("user") or order.get("buyer") or {}
                buyer_name = "Неизвестно"
                
                if isinstance(buyer, dict):
                    # Приоритет: username -> nickname -> name -> id
                    buyer_name = (
                        buyer.get("username") or 
                        buyer.get("nickname") or 
                        buyer.get("name") or 
                        buyer.get("displayName") or
                        str(buyer.get("id", "Неизвестно"))
                    )
                elif isinstance(buyer, str):
                    buyer_name = buyer
                
                # Получаем данные лота (в Starvell API это offerDetails)
                lot = order.get("offerDetails") or order.get("listing") or order.get("lot") or order.get("offer") or {}
                lot_name = "Неизвестно"
                
                if isinstance(lot, dict):
                    # Для Starvell API: offerDetails.descriptions.rus.briefDescription
                    descriptions = lot.get("descriptions", {})
                    if descriptions:
                        rus_desc = descriptions.get("rus", {})
                        lot_name = (
                            rus_desc.get("briefDescription") or 
                            rus_desc.get("description") or
                            lot.get("name") or 
                            lot.get("title") or
                            "Неизвестно"
                        )
                    else:
                        # Fallback для других форматов
                        lot_name = (
                            lot.get("name") or 
                            lot.get("title") or 
                            lot.get("description") or
                            "Неизвестно"
                        )
                elif isinstance(lot, str):
                    lot_name = lot
                
                # Отправляем уведомление через NotificationManager
                await self.notifier.notify_new_order(
                    order_id=order_id,
                    short_id=short_id,
                    buyer=buyer_name,
                    amount=float(amount),
                    lot_name=lot_name,
                    status=status,
                    order_data=order
                )
                
                # Логируем с полными данными для отладки
                logger.info(f"🛒 Новый заказ #{short_id} от {buyer_name}: {lot_name} - {amount}₽")
                logger.debug(f"Полные данные заказа: {order}")
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке новых заказов: {e}", exc_info=True)
            
    async def _auto_bump(self):
        """Автоматический bump офферов"""
        try:
            # Проверяем, включен ли авто-bump хотя бы у одного админа
            auto_bump_enabled = False
            
            for admin_id in BotConfig.ADMIN_IDS():
                settings = await self.db.get_user_settings(admin_id)
                if settings.get("auto_bump_enabled", False):
                    auto_bump_enabled = True
                    break
                    
            if not auto_bump_enabled:
                return
                
            # Выполняем bump
            logger.info("Выполняется авто-bump офферов...")
            
            result = await self.starvell.bump_offers()
            
            from bot.core import get_notification_manager, NotificationType
            notif_manager = get_notification_manager()
            
            if notif_manager:
                # Уведомляем админов через NotificationManager
                message = f"Время: {datetime.now().strftime('%H:%M:%S')}\n"
                message += f"Game ID: {BotConfig.AUTO_BUMP_GAME_ID()}\n"
                message += f"Категории: {', '.join(map(str, BotConfig.AUTO_BUMP_CATEGORIES()))}"
                
                await notif_manager.notify_all_admins(
                    NotificationType.AUTO_BUMP,
                    message
                )
                        
            logger.info("Авто-bump успешно выполнен")
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении авто-bump: {e}", exc_info=True)
            
            from bot.core import get_notification_manager
            notif_manager = get_notification_manager()
            
            if notif_manager:
                await notif_manager.notify_error(
                    str(e),
                    context="Авто-bump",
                    details={"Время": datetime.now().strftime('%H:%M:%S')}
                )
                    
    async def _cleanup_old_data(self):
        """Очистка старых данных"""
        try:
            logger.info("Очистка старых данных...")
            await self.db.cleanup(days=7)
            logger.info("Очистка завершена")
        except Exception as e:
            logger.error(f"Ошибка при очистке данных: {e}", exc_info=True)
    
    async def _check_custom_command(self, chat_id: str, message_text: str, author_id: str):
        """Проверить и обработать кастомную команду"""
        try:
            import json
            from pathlib import Path
            
            # Загружаем кастомные команды
            commands_file = Path("storage/custom_commands.json")
            if not commands_file.exists():
                return
            
            with open(commands_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем, включены ли кастомные команды
            if not data.get("enabled", False):
                return
            
            prefix = data.get("prefix", "!")
            commands = data.get("commands", [])
            
            # Проверяем, начинается ли сообщение с префикса
            if not message_text.startswith(prefix):
                return
            
            # Извлекаем команду (без префикса)
            command_text = message_text[len(prefix):].strip().lower()
            
            # Ищем соответствующую команду
            for cmd in commands:
                if cmd["name"].lower() == command_text:
                    # Нашли команду - отправляем ответ
                    try:
                        await self.starvell.send_message(chat_id, cmd["text"])
                        logger.info(f"🤖 Отправлен автоответ на команду '{prefix}{cmd['name']}' пользователю {author_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке автоответа на команду: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке кастомной команды: {e}", exc_info=True)
    
    async def _check_auto_responses(self):
        """Проверка и отправка автоответов"""
        try:
            if self.auto_response:
                await self.auto_response.check_and_respond()
        except Exception as e:
            logger.error(f"Ошибка при проверке автоответов: {e}", exc_info=True)
            
    async def toggle_auto_bump(self, enabled: bool):
        """Включить/выключить авто-bump"""
        if enabled and not self.scheduler.get_job('auto_bump'):
            self.scheduler.add_job(
                self._auto_bump,
                'interval',
                seconds=BotConfig.AUTO_BUMP_INTERVAL(),
                id='auto_bump',
            )
            logger.info("Авто-bump включен")
        elif not enabled and self.scheduler.get_job('auto_bump'):
            self.scheduler.remove_job('auto_bump')
            logger.info("Авто-bump выключен")
