"""
Сервис для работы со Starvell API
"""

import asyncio
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
        
    async def start(self):
        """Запустить сервис"""
        self.api = StarAPI(
            session_cookie=BotConfig.STARVELL_SESSION(),
            user_agent=BotConfig.USER_AGENT()
        )
        await self.api.session.start()
        
    async def stop(self):
        """Остановить сервис"""
        if self.api:
            await self.api.close()
            
    async def get_user_info(self) -> Dict[str, Any]:
        """Получить информацию о пользователе"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.get_user_info()
        
    async def get_chats(self) -> List[Dict[str, Any]]:
        """Получить список чатов"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
            
        data = await self.api.get_chats()
        return data.get("pageProps", {}).get("chats", [])
        
    async def get_unread_chats(self) -> List[Dict[str, Any]]:
        """Получить чаты с непрочитанными сообщениями"""
        chats = await self.get_chats()
        return [chat for chat in chats if chat.get("unreadCount", 0) > 0]
        
    async def get_messages(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить сообщения из чата"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.get_messages(chat_id, limit)
        
    async def send_message(self, chat_id: str, content: str) -> Dict[str, Any]:
        """Отправить сообщение в чат"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
            
        async with self._lock:
            result = await self.api.send_message(chat_id, content)
            await self.db.add_sent_message(chat_id, content)
            return result
    
    async def find_chat_by_user_id(self, user_id: str) -> Optional[str]:
        """Найти ID чата с конкретным пользователем"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
        return await self.api.find_chat_by_user_id(user_id)
            
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Получить список заказов"""
        if not self.api:
            raise RuntimeError("API не инициализирован")
            
        data = await self.api.get_sells()
        return data.get("pageProps", {}).get("orders", [])
        
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
                await self.db.add_bump_history(game_id, category_ids, False)
                raise
                
    async def get_new_messages_count(self) -> int:
        """Получить количество новых сообщений"""
        chats = await self.get_unread_chats()
        return sum(chat.get("unreadCount", 0) for chat in chats)
        
    async def check_new_messages(self) -> List[Dict[str, Any]]:
        """Проверить новые сообщения"""
        new_messages = []
        
        # Получаем ВСЕ чаты (не только с unread)
        chats = await self.get_chats()
        
        for chat in chats:
            chat_id = chat.get("id")
            if not chat_id:
                continue
                
            # Получаем последнее известное сообщение
            last_known_id = await self.db.get_last_message(chat_id)
            
            # Получаем последние сообщения
            messages = await self.get_messages(chat_id, limit=10)
            
            if not messages:
                continue
            
            # Если это первый раз - просто сохраняем последнее и не уведомляем
            if not last_known_id:
                latest_id = messages[0].get("id")
                if latest_id:
                    await self.db.set_last_message(chat_id, latest_id)
                continue
            
            # Фильтруем новые (все сообщения после last_known_id)
            found_last_known = False
            for msg in messages:
                msg_id = msg.get("id")
                
                if msg_id == last_known_id:
                    found_last_known = True
                    break
                    
                # Это новое сообщение
                new_messages.append({
                    "chat_id": chat_id,
                    "message": msg,
                    "chat": chat,
                })
                    
            # Обновляем последнее сообщение
            if messages:
                latest_id = messages[0].get("id")
                if latest_id:
                    await self.db.set_last_message(chat_id, latest_id)
                    
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
            # TODO: Реализовать активацию через API Starvell
            # result = await self.api.activate_lot(lot_id, amount)
            # Пока возвращаем заглушку
            return True
        except Exception as e:
            raise RuntimeError(f"Ошибка активации лота {lot_id}: {e}")
    
    async def keep_alive(self) -> bool:
        """
        Поддержка онлайн статуса
        
        Returns:
            True если успешно
        """
        if not self.api:
            raise RuntimeError("API не инициализирован")
        
        return await self.api.keep_alive()
    
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
