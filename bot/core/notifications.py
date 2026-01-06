"""
Система уведомлений Starvell Cardinal
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.core.config import BotConfig

logger = logging.getLogger(__name__)


class NotificationType:
    """Типы уведомлений"""
    NEW_MESSAGE = "new_message"
    NEW_ORDER = "new_order"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_CANCELLED = "order_cancelled"
    LOT_DEACTIVATED = "lot_deactivated"
    LOT_RESTORED = "lot_restored"
    LOT_BUMPED = "lot_bumped"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    AUTO_DELIVERY = "auto_delivery"
    AUTO_RESTORE = "auto_restore"
    AUTO_BUMP = "auto_bump"
    UPDATE_AVAILABLE = "update_available"


class NotificationManager:
    """Менеджер уведомлений"""
    
    # Эмодзи для разных типов уведомлений
    EMOJI_MAP = {
        NotificationType.NEW_MESSAGE: "💬",
        NotificationType.NEW_ORDER: "📦",
        NotificationType.ORDER_CONFIRMED: "✅",
        NotificationType.ORDER_CANCELLED: "❌",
        NotificationType.LOT_DEACTIVATED: "🚫",
        NotificationType.LOT_RESTORED: "🔄",
        NotificationType.LOT_BUMPED: "⬆️",
        NotificationType.BOT_STARTED: "🟢",
        NotificationType.BOT_STOPPED: "🔴",
        NotificationType.ERROR: "❌",
        NotificationType.WARNING: "⚠️",
        NotificationType.UPDATE_AVAILABLE: "✨",
        NotificationType.INFO: "ℹ️",
        NotificationType.AUTO_DELIVERY: "🤖",
        NotificationType.AUTO_RESTORE: "♻️",
        NotificationType.AUTO_BUMP: "🔀",
    }
    
    # Заголовки для разных типов
    TITLE_MAP = {
        NotificationType.NEW_MESSAGE: "Новое сообщение",
        NotificationType.NEW_ORDER: "Новый заказ",
        NotificationType.ORDER_CONFIRMED: "Заказ подтверждён",
        NotificationType.ORDER_CANCELLED: "Заказ отменён",
        NotificationType.LOT_DEACTIVATED: "Лот деактивирован",
        NotificationType.LOT_RESTORED: "Лот восстановлен",
        NotificationType.LOT_BUMPED: "Лот поднят",
        NotificationType.BOT_STARTED: "Бот запущен",
        NotificationType.BOT_STOPPED: "Бот остановлен",
        NotificationType.ERROR: "Ошибка",
        NotificationType.WARNING: "Предупреждение",
        NotificationType.INFO: "Информация",
        NotificationType.AUTO_DELIVERY: "Автовыдача",
        NotificationType.AUTO_RESTORE: "Авто-восстановление",
        NotificationType.AUTO_BUMP: "Авто-поднятие",
    }
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self._enabled_notifications: Dict[int, Dict[str, bool]] = {}
        
    def _check_notification_enabled(self, user_id: int, notif_type: str) -> bool:
        """Проверка, включён ли тип уведомления для пользователя"""
        # Маппинг типов на настройки конфига
        config_map = {
            NotificationType.NEW_MESSAGE: BotConfig.NOTIFY_NEW_MESSAGES,
            NotificationType.NEW_ORDER: BotConfig.NOTIFY_NEW_ORDERS,
            NotificationType.LOT_RESTORED: BotConfig.NOTIFY_LOT_RESTORE,
            NotificationType.LOT_BUMPED: BotConfig.NOTIFY_LOT_BUMP,
            NotificationType.LOT_DEACTIVATED: BotConfig.NOTIFY_LOT_DEACTIVATE,
            NotificationType.BOT_STARTED: BotConfig.NOTIFY_BOT_START,
        }
        
        # Если есть соответствующая настройка в конфиге
        if notif_type in config_map:
            return config_map[notif_type]()
        
        # По умолчанию включено
        return True
    
    async def send_notification(
        self,
        user_id: int,
        notif_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        force: bool = False
    ) -> bool:
        """
        Отправить уведомление пользователю
        
        Args:
            user_id: ID пользователя
            notif_type: Тип уведомления из NotificationType
            message: Текст сообщения
            details: Дополнительные детали для форматирования
            keyboard: Клавиатура (опционально)
            force: Отправить принудительно, игнорируя настройки
            
        Returns:
            True если уведомление отправлено успешно
        """
        # Проверяем настройки уведомлений
        if not force and not self._check_notification_enabled(user_id, notif_type):
            logger.debug(f"Уведомление {notif_type} для {user_id} отключено")
            return False
        
        try:
            # Формируем текст уведомления
            emoji = self.EMOJI_MAP.get(notif_type, "📌")
            title = self.TITLE_MAP.get(notif_type, "Уведомление")
            
            text = f"{emoji} <b>{title}</b>\n\n"
            text += message
            
            # Добавляем детали если есть
            if details:
                text += "\n\n"
                for key, value in details.items():
                    text += f"<b>{key}:</b> {value}\n"
            
            # Отправляем
            await self.bot.send_message(
                user_id,
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            logger.debug(f"Уведомление {notif_type} отправлено пользователю {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление {notif_type} пользователю {user_id}: {e}")
            return False
    
    async def notify_all_admins(
        self,
        notif_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        force: bool = False
    ) -> int:
        """
        Отправить уведомление всем админам
        
        Returns:
            Количество успешно отправленных уведомлений
        """
        count = 0
        for admin_id in BotConfig.ADMIN_IDS():
            if await self.send_notification(admin_id, notif_type, message, details, keyboard, force):
                count += 1
        return count
    
    async def notify_new_message(
        self,
        chat_id: str,
        author: str,
        content: str,
        message_id: Optional[str] = None,
        author_nickname: Optional[str] = None
    ):
        """Уведомление о новом сообщении"""
        # Используем nickname если есть, иначе ID
        display_name = author_nickname or author
        
        # Форматируем сообщение: смайлик + Nickname: message
        message = f"💬 <b>{display_name}:</b> {content}"
        
        # Создаём кнопки
        buttons = []
        
        # Кнопка "Ответить" - используем короткий формат
        short_chat_id = chat_id[-12:] if len(chat_id) > 12 else chat_id
        callback_data = f"r:{short_chat_id}"
        
        if len(callback_data) <= 64:
            buttons.append([
                InlineKeyboardButton(
                    text="💬 Ответить",
                    callback_data=callback_data
                )
            ])
        
        # Кнопка "Перейти в чат" - URL кнопка
        chat_url = f"https://starvell.com/chat/{chat_id}"
        buttons.append([
            InlineKeyboardButton(
                text="🔗 Перейти в чат",
                url=chat_url
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        await self.notify_all_admins(
            NotificationType.NEW_MESSAGE,
            message,
            keyboard=keyboard
        )
    
    async def notify_new_order(
        self,
        order_id: str,
        short_id: str,
        buyer: str,
        amount: float,
        lot_name: str,
        status: str = "CREATED",
        order_data: dict = None
    ):
        """Уведомление о новом заказе"""
        # Форматируем сообщение (без статуса)
        message = f"🆔 <b>ID заказа:</b> #{short_id}\n\n"
        message += f"👤 <b>Покупатель:</b> {buyer}\n"
        message += f"📦 <b>Лот:</b> {lot_name}\n"
        message += f"💰 <b>Сумма:</b> {amount} ₽"
        
        # Создаём только кнопку для открытия заказа
        buttons = []
        
        # Кнопка ссылки на заказ (используем полный order_id)
        order_url = f"https://starvell.com/order/{order_id}"
        buttons.append([
            InlineKeyboardButton(
                text="🔗 Открыть заказ",
                url=order_url
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        await self.notify_all_admins(
            NotificationType.NEW_ORDER,
            message,
            keyboard=keyboard
        )

    async def notify_lots_raised(
        self,
        game_id: int,
        time_info: str = ""
    ):
        """Уведомление о поднятии лотов"""
        message = f"⤴️ <b><i>Поднял все лоты игры</i></b> <code>ID={game_id}</code>\n"
        
        if time_info:
            # Добавляем информацию о времени в spoiler
            message += f"<tg-spoiler>{time_info}</tg-spoiler>"
        
        await self.notify_all_admins(
            NotificationType.LOT_BUMPED,
            message,
            force=False
        )
    
    async def notify_lot_action(
        self,
        action: str,
        lot_id: str,
        lot_name: str,
        reason: Optional[str] = None
    ):
        """Уведомление о действии с лотом"""
        type_map = {
            'deactivated': NotificationType.LOT_DEACTIVATED,
            'restored': NotificationType.LOT_RESTORED,
            'bumped': NotificationType.LOT_BUMPED,
        }
        
        notif_type = type_map.get(action, NotificationType.INFO)
        
        message = f"<b>Лот:</b> {lot_name}\n"
        message += f"<b>ID:</b> {lot_id}\n"
        
        if reason:
            message += f"\n<b>Причина:</b> {reason}"
        
        await self.notify_all_admins(notif_type, message)
    
    async def notify_auto_delivery(
        self,
        order_id: str,
        buyer: str,
        lot_name: str,
        delivered_items: List[str],
        success: bool = True
    ):
        """Уведомление об автовыдаче"""
        if success:
            message = f"<b>Заказ #{order_id} автоматически выполнен</b>\n\n"
            message += f"<b>Покупатель:</b> {buyer}\n"
            message += f"<b>Лот:</b> {lot_name}\n"
            message += f"<b>Выдано товаров:</b> {len(delivered_items)}\n\n"
            
            if delivered_items:
                message += "<b>Товары:</b>\n"
                for i, item in enumerate(delivered_items[:5], 1):
                    message += f"{i}. {item}\n"
                if len(delivered_items) > 5:
                    message += f"... и ещё {len(delivered_items) - 5}"
        else:
            message = f"<b>❌ Ошибка автовыдачи</b>\n\n"
            message += f"<b>Заказ:</b> #{order_id}\n"
            message += f"<b>Покупатель:</b> {buyer}\n"
            message += f"<b>Лот:</b> {lot_name}"
        
        await self.notify_all_admins(
            NotificationType.AUTO_DELIVERY,
            message
        )
    
    async def notify_error(
        self,
        error_message: str,
        context: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Уведомление об ошибке"""
        message = error_message
        
        if context:
            message = f"<b>Контекст:</b> {context}\n\n{message}"
        
        await self.notify_all_admins(
            NotificationType.ERROR,
            message,
            details=details,
            force=True
        )
    
    async def notify_update_available(self, current_version: str, latest_version: str):
        """Уведомление о доступном обновлении"""
        message = (
            f"╔══════════════════════╗\n"
            f"║  <b>ДОСТУПНО ОБНОВЛЕНИЕ!</b>     ║\n"
            f"╚══════════════════════╝\n\n"
            f"📌 <b>Текущая версия:</b> <code>{current_version}</code>\n"
            f"✨ <b>Новая версия:</b> <code>{latest_version}</code>\n\n"
            f"Используйте команду /update для обновления"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить сейчас",
                    callback_data="update_now"
                )
            ]
        ])
        
        await self.notify_all_admins(
            NotificationType.UPDATE_AVAILABLE,
            message,
            keyboard=keyboard,
            force=True
        )


# Singleton instance
_notification_manager: Optional[NotificationManager] = None


def init_notifications(bot: Bot) -> NotificationManager:
    """Инициализировать менеджер уведомлений"""
    global _notification_manager
    _notification_manager = NotificationManager(bot)
    return _notification_manager


def get_notification_manager() -> Optional[NotificationManager]:
    """Получить instance менеджера уведомлений"""
    return _notification_manager
