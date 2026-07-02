"""
Сервис для работы со Starvell API
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
from api import StarAPI, StarAPIError
from bot.core.config import BotConfig
from bot.core.storage import Database


class StarvellService:
    """Сервис для работы с Starvell"""
    
    def __init__(self, db: Database):
        self.db = db
        self.api: Optional[StarAPI] = None
        self._lock = asyncio.Lock()
        self._session_error_notified = False  # Флаг для уведомления об ошибке сессии (1 раз)
        self.last_user_info: Dict[str, Any] = {}
        self._orders_cache: Optional[List[Dict[str, Any]]] = None
        self._orders_cache_at: float = 0.0
        
    async def start(self):
        """Запустить сервис"""
        self.api = StarAPI(
            session_cookie=BotConfig.STARVELL_SESSION(),
            user_agent=BotConfig.USER_AGENT()
        )
        await self.api.session.start()
        # Сбрасываем флаг при старте/перезапуске
        self._session_error_notified = False
        
    async def stop(self):
        """Остановить сервис"""
        if self.api:
            await self.api.close()
    
    async def _notify_session_error(self):
        """Отправить уведомление об ошибке сессии (только один раз)"""
        if self._session_error_notified:
            return
        
        self._session_error_notified = True
        
        import logging
        logger = logging.getLogger(__name__)
        logger.error("⚠️ СЕССИЯ STARVELL УСТАРЕЛА! Токен невалиден или истёк. Обновите session_cookie в конфигурации.")
        
        # Пытаемся отправить уведомление админам
        try:
            from bot.core.notifications import get_notification_manager
            notification_manager = get_notification_manager()
            if notification_manager:
                await notification_manager.notify_all_admins(
                    "error",
                    "⚠️ <b>Сессия Starvell устарела!</b>\n\n"
                    "Токен (session_cookie) невалиден или истёк.\n"
                    "Starvell сбросил сессию.\n\n"
                    "🔧 <b>Необходимо:</b>\n"
                    "1. Получить новый session_cookie из браузера\n"
                    "2. Обновить его в конфигурации (_main.cfg)\n"
                    "3. Перезапустить бота",
                    force=True
                )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление об ошибке сессии: {e}")
            
    async def get_user_info(self) -> Dict[str, Any]:
        """Получить информацию о пользователе"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        try:
            info = await self.api.get_user_info()
            self.last_user_info = info
            # Starvell на протухшей куке отдаёт страницу без user, а не 401
            if not info.get("authorized"):
                await self._notify_session_error()
            return info
        except Exception as e:
            from api.exceptions import AuthenticationError
            if isinstance(e, AuthenticationError):
                await self._notify_session_error()
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить профиль пользователя по ID
        
        Args:
            user_id: ID пользователя в Starvell
            
        Returns:
            dict: Данные профиля (nickname, name, id и др.) или None если не найден
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.get_user_profile(user_id)
        
    async def get_chats(self) -> List[Dict[str, Any]]:
        """Получить список чатов"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        try:
            data = await self.api.get_chats()
            return data.get("pageProps", {}).get("chats", [])
        except Exception as e:
            from api.exceptions import AuthenticationError
            if isinstance(e, AuthenticationError):
                await self._notify_session_error()
            raise
        
    async def get_unread_chats(self) -> List[Dict[str, Any]]:
        """Получить чаты с непрочитанными сообщениями"""
        chats = await self.get_chats()
        return [chat for chat in chats if (chat.get("unreadMessageCount") or chat.get("unreadCount") or 0) > 0]
        
    async def get_messages(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить сообщения из чата"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        try:
            return await self.api.get_messages(chat_id, limit)
        except Exception as e:
            from api.exceptions import AuthenticationError
            if isinstance(e, AuthenticationError):
                await self._notify_session_error()
            raise
        
    async def send_message(self, chat_id: str, content: str) -> Dict[str, Any]:
        """Отправить сообщение в чат"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
            
        async with self._lock:
            # Добавляем вотермарк в сообщение при отправке в Starvell, если включено
            try:
                from bot.core.config import BotConfig
                if BotConfig.USE_WATERMARK():
                    wm = BotConfig.WATERMARK() or ''
                    if wm:
                        # Добавляем в начало, затем пустая строка и оригинальное сообщение
                        content = f"{wm}\n\n{content}"
            except Exception:
                # Не критично — продолжаем без вотермарки
                pass

            result = await self.api.send_message(chat_id, content)
            await self.db.add_sent_message(chat_id, content)
            return result
    
    async def mark_chat_as_read(self, chat_id: str) -> bool:
        """Пометить чат как прочитанный"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.mark_chat_as_read(chat_id)
    
    async def find_chat_by_user_id(self, user_id: str) -> Optional[str]:
        """Найти ID чата с конкретным пользователем"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.find_chat_by_user_id(user_id)
            
    async def get_orders(self, max_age: float = 0) -> List[Dict[str, Any]]:
        """
        Получить список заказов

        Args:
            max_age: Отдать закэшированный список, если он не старше
                     этого количества секунд (0 — всегда свежий запрос)
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        now = time.monotonic()

        # Кэш: заказы дёргают три потребителя (мониторинг, автоответы,
        # авто-тикеты) — не ходим в API, если данные ещё свежие
        if max_age > 0 and self._orders_cache is not None:
            if now - self._orders_cache_at < max_age:
                return self._orders_cache

        try:
            # Используем новый метод для получения ВСЕХ заказов
            orders = await self.api.get_all_orders()
            orders = orders if orders else []
            self._orders_cache = orders
            self._orders_cache_at = time.monotonic()
            return orders
        except Exception as e:
            from api.exceptions import AuthenticationError
            if isinstance(e, AuthenticationError):
                await self._notify_session_error()
            raise
    
    async def get_all_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить ВСЕ заказы с опциональным фильтром по статусу
        
        Args:
            status: Фильтр по статусу ("CREATED", "COMPLETED", "REFUND", "PRE_CREATED")
                   Если None - возвращает все заказы
        
        Returns:
            list: Список всех заказов
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        try:
            orders = await self.api.get_all_orders(status=status)
            return orders if orders else []
        except Exception as e:
            from api.exceptions import AuthenticationError
            if isinstance(e, AuthenticationError):
                await self._notify_session_error()
            raise
        
    async def refund_order(self, order_id: str) -> Dict[str, Any]:
        """Вернуть деньги за заказ"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.refund_order(order_id)
        
    async def confirm_order(self, order_id: str) -> Dict[str, Any]:
        """Подтвердить заказ"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.confirm_order(order_id)
    
    async def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Получить детальную информацию о заказе"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.get_order_details(order_id)
        
    async def bump_offers(
        self,
        game_id: Optional[int] = None,
        category_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Поднять офферы в топ"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
            
        # Используем значения из конфига, если не переданы
        game_id = game_id or BotConfig.AUTO_BUMP_GAME_ID()
        category_ids = category_ids or BotConfig.AUTO_BUMP_CATEGORIES()
        
        async with self._lock:
            try:
                # Сначала получаем user_info для SID
                await self.api.get_user_info()
                
                # Поднимаем
                result = await self.api.bump_offers(game_id, category_ids)
                
                # Сохраняем в БД
                await self.db.add_bump_history(game_id, category_ids, True)
                
                return result
            except Exception as e:
                from api.exceptions import AuthenticationError
                if isinstance(e, AuthenticationError):
                    await self._notify_session_error()
                await self.db.add_bump_history(game_id, category_ids, False)
                raise
                
    async def get_new_messages_count(self) -> int:
        """Получить количество новых сообщений"""
        chats = await self.get_unread_chats()
        return sum((chat.get("unreadMessageCount") or chat.get("unreadCount") or 0) for chat in chats)
        
    async def check_new_messages(self) -> List[Dict[str, Any]]:
        """
        Проверить новые сообщения
        
        ОПТИМИЗИРОВАНО: проверяем только чаты с непрочитанными сообщениями
        вместо всех чатов, чтобы снизить количество API запросов.
        """
        import logging
        from bot.core.config import BotConfig
        logger = logging.getLogger(__name__)
        
        new_messages = []
        
        # Получаем все чаты
        chats = await self.get_chats()
        
        # ОПТИМИЗАЦИЯ: фильтруем только чаты с непрочитанными сообщениями
        unread_chats = [c for c in chats if (c.get("unreadMessageCount") or c.get("unreadCount") or 0) > 0]
        
        logger.debug(f"📬 Всего чатов: {len(chats)}, с непрочитанными: {len(unread_chats)}")
        
        # Проверяем настройку авто-прочтения
        auto_read_enabled = BotConfig.AUTO_READ_ENABLED()
        
        for chat in unread_chats:
            chat_id = chat.get("id")
            if not chat_id:
                continue
            
            chat_new_messages = []
            
            # Получаем последнее известное сообщение из БД
            last_known_id = await self.db.get_last_message(chat_id)
            
            # Получаем последние 10 сообщений чата
            messages = await self.get_messages(chat_id, limit=10)
            
            if not messages:
                continue
            
            # Если это первый раз (нет в БД), определяем непрочитанные
            if not last_known_id:
                unread_count = chat.get("unreadMessageCount") or chat.get("unreadCount") or 0
                if unread_count > 0:
                    # Берем последние unread_count сообщений как новые
                    for i in range(min(unread_count, len(messages))):
                        chat_new_messages.append({
                            "chat_id": chat_id,
                            "message": messages[i],
                            "chat": chat,
                        })
                    logger.debug(f"🆕 Обнаружено {len(chat_new_messages)} нов. сообщений в новом чате {chat_id}")
                
                # Сохраняем ID последнего сообщения
                await self.db.set_last_message(chat_id, messages[0].get("id"))
                
                if chat_new_messages:
                    new_messages.extend(chat_new_messages)
                    if auto_read_enabled:
                        await self.mark_chat_as_read(chat_id)
                continue

            for msg in messages:
                msg_id = msg.get("id")
                
                if msg_id == last_known_id:
                    break
                    
                # Это новое сообщение
                chat_new_messages.append({
                    "chat_id": chat_id,
                    "message": msg,
                    "chat": chat,
                })
            
            # Добавляем в общий список
            new_messages.extend(chat_new_messages)
                    
            # Обновляем последнее сообщение
            if messages:
                latest_id = messages[0].get("id")
                if latest_id:
                    await self.db.set_last_message(chat_id, latest_id)
            
            # Помечаем чат как прочитанный после обработки (если включено)
            if auto_read_enabled:
                await self.mark_chat_as_read(chat_id)
                    
        return new_messages
        
    async def check_new_orders(self) -> List[Dict[str, Any]]:
        """Проверить новые заказы"""
        new_orders = []
        
        orders = await self.get_orders()
        
        for order in orders:
            order_id = order.get("id")
            status = order.get("status")
            
            if not order_id:
                continue
                
            # Проверяем, знаем ли мы этот заказ
            last_known = await self.db.get_last_order(order_id)
            
            if not last_known:
                # Новый заказ
                new_orders.append(order)
                await self.db.set_last_order(order_id, status)
            elif last_known["status"] != status:
                # Статус изменился
                new_orders.append(order)
                await self.db.set_last_order(order_id, status)
                
        return new_orders
    
    async def get_lots(self) -> List[Dict[str, Any]]:
        """Получить список лотов пользователя"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        try:
            # Получаем информацию о текущем пользователе
            user_info = await self.api.get_user_info()
            user = user_info.get("user")
            
            if not user or not user.get("id"):
                raise RuntimeError("Не удалось получить ID пользователя")
            
            user_id = user.get("id")
            
            # Получаем офферы этого пользователя
            offers = await self.api.get_user_offers(user_id)
            return offers
        except Exception as e:
            from api.exceptions import AuthenticationError
            if isinstance(e, AuthenticationError):
                await self._notify_session_error()
            raise RuntimeError(f"Ошибка получения лотов: {e}")
    
    async def activate_lot(self, lot_id: str, amount: Optional[int] = None) -> bool:
        """
        Активировать лот с указанным количеством
        
        Args:
            lot_id: ID лота
            amount: Количество товара (опционально)
        
        Returns:
            True если успешно, False otherwise
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")

        try:
            await self.api.update_offer(lot_id, availability=amount, is_active=True)
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Ошибка активации лота {lot_id}: {e}")
            return False

    async def update_lot(
        self,
        lot_id,
        availability: Optional[int] = None,
        is_active: Optional[bool] = None,
        price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Изменить настройки лота: активность, количество, цену

        Args:
            lot_id: ID лота
            availability: Количество товара
            is_active: Включить/выключить лот
            price: Цена (в копейках)
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")

        return await self.api.update_offer(
            lot_id,
            availability=availability,
            is_active=is_active,
            price=price,
        )
    
    async def keep_alive(self) -> bool:
        """
        Поддержка онлайн статуса
        
        Returns:
            True если успешно
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")

        return await self.api.keep_alive()

    async def is_socket_io_available(self) -> bool:
        """Проверить доступность Socket.IO для вечного онлайна"""
        if not self.api:
            raise RuntimeError("API не инициализирован")

        return await self.api.is_socket_io_available()

    async def connect_online_socket(self):
        """Открыть websocket для поддержания онлайна"""
        if not self.api:
            raise RuntimeError("API не инициализирован")

        return await self.api.connect_online_socket()
    
    async def raise_lots(self, game_id: int, category_ids: List[int]) -> bool:
        """
        Поднять лоты категорий
        
        Args:
            game_id: ID игры
            category_ids: Список ID категорий
        
        Returns:
            True если успешно, False otherwise
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        try:
            async with self._lock:
                # Используем существующий метод bump_offers
                result = await self.bump_offers(game_id, category_ids)
                return result.get('success', False)
        except Exception as e:
            # Пробрасываем исключение дальше для обработки wait time
            raise RuntimeError(f"Ошибка поднятия лотов: {e}")
