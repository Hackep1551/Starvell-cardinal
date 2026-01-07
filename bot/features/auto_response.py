"""
Система автоматических ответов на подтверждение заказа и отзывы
"""

import logging
from typing import Dict, Set, Optional
from bot.core.config import BotConfig, get_config_manager
from bot.core.services import StarvellService
from bot.core.storage import Database

logger = logging.getLogger("AutoResponse")


class AutoResponseService:
    """Сервис автоматических ответов"""
    
    def __init__(self, starvell: StarvellService, db: Database):
        self.starvell = starvell
        self.db = db
        
        # Отслеживание уже обработанных заказов
        self._confirmed_orders: Set[str] = set()
        self._reviewed_orders: Set[str] = set()
        
    async def start(self):
        """Запуск сервиса"""
        logger.info("Сервис автоответов запущен")
        
    async def stop(self):
        """Остановка сервиса"""
        logger.info("Сервис автоответов остановлен")
        
    async def check_and_respond(self):
        """
        Проверить заказы и отправить автоответы где необходимо
        """
        try:
            # Проверяем, включены ли автоответы
            order_confirm_enabled = BotConfig.ORDER_CONFIRM_RESPONSE_ENABLED()
            review_response_enabled = BotConfig.REVIEW_RESPONSE_ENABLED()
            
            if not order_confirm_enabled and not review_response_enabled:
                return
            
            # Получаем все заказы
            orders = await self.starvell.get_orders()
            
            for order in orders:
                order_id = order.get("id")
                if not order_id:
                    continue
                
                # Проверяем ответ на подтверждение заказа
                if order_confirm_enabled:
                    await self._check_order_confirmation(order)
                
                # Проверяем ответ на отзыв
                if review_response_enabled:
                    await self._check_review_response(order)
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке автоответов: {e}", exc_info=True)
            
    async def _check_order_confirmation(self, order: Dict):
        """
        Проверить, нужно ли отправить ответ на подтверждение заказа
        """
        order_id = order.get("id")
        status = order.get("status", "")
        
        # Заказ должен быть завершён (COMPLETED)
        if status != "COMPLETED" and status != "completed":
            return
        
        # Проверяем, не отправляли ли уже ответ
        if order_id in self._confirmed_orders:
            return
        
        # Проверяем черный список (по buyer ID если есть)
        buyer_id = order.get("buyerId") or order.get("buyer_id")
        if buyer_id:
            config = get_config_manager()
            blacklist_section = f"Blacklist.{buyer_id}"
            if config._config.has_section(blacklist_section):
                logger.debug(f"Автоответ на заказ {order_id[:8]} пропущен (покупатель {buyer_id} в ЧС)")
                self._confirmed_orders.add(order_id)  # Помечаем как обработанный
                return
        
        try:
            # Получаем детали заказа для получения chat_id
            order_details = await self.starvell.get_order_details(order_id)
            
            # Извлекаем chat_id
            chat_id = None
            page_props = order_details.get("pageProps", {})
            
            # Пробуем разные варианты
            if "chat" in page_props and isinstance(page_props["chat"], dict):
                chat_id = page_props["chat"].get("id")
            elif "chatId" in order:
                chat_id = order.get("chatId")
            elif "chat_id" in order:
                chat_id = order.get("chat_id")
                
            if not chat_id:
                logger.warning(f"Не удалось найти chat_id для заказа {order_id}")
                # Помечаем как обработанный, чтобы не спамить логи
                self._confirmed_orders.add(order_id)
                return
            
            # Отправляем ответ
            response_text = BotConfig.ORDER_CONFIRM_RESPONSE_TEXT()
            await self.starvell.send_message(chat_id, response_text)
            
            # Помечаем как обработанный
            self._confirmed_orders.add(order_id)
            
            logger.info(f"✅ Отправлен автоответ на подтверждение заказа {order_id[:8]}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа на подтверждение заказа {order_id}: {e}")
            # Не добавляем в обработанные, чтобы попробовать ещё раз
            
    async def _check_review_response(self, order: Dict):
        """
        Проверить, нужно ли отправить ответ на отзыв
        """
        order_id = order.get("id")
        
        # Проверяем, есть ли отзыв
        review = order.get("review")
        if not review:
            return
        
        # Проверяем, не отправляли ли уже ответ
        if order_id in self._reviewed_orders:
            return
        
        # Проверяем черный список (по buyer ID если есть)
        buyer_id = order.get("buyerId") or order.get("buyer_id")
        if buyer_id:
            config = get_config_manager()
            blacklist_section = f"Blacklist.{buyer_id}"
            if config._config.has_section(blacklist_section):
                logger.debug(f"Автоответ на отзыв заказа {order_id[:8]} пропущен (покупатель {buyer_id} в ЧС)")
                self._reviewed_orders.add(order_id)  # Помечаем как обработанный
                return
        
        try:
            # Получаем детали заказа для получения chat_id
            order_details = await self.starvell.get_order_details(order_id)
            
            # Извлекаем chat_id
            chat_id = None
            page_props = order_details.get("pageProps", {})
            
            # Пробуем разные варианты
            if "chat" in page_props and isinstance(page_props["chat"], dict):
                chat_id = page_props["chat"].get("id")
            elif "chatId" in order:
                chat_id = order.get("chatId")
            elif "chat_id" in order:
                chat_id = order.get("chat_id")
                
            if not chat_id:
                logger.warning(f"Не удалось найти chat_id для заказа {order_id} (отзыв)")
                # Помечаем как обработанный, чтобы не спамить логи
                self._reviewed_orders.add(order_id)
                return
            
            # Получаем информацию об отзыве
            rating = review.get("rating", "N/A")
            comment = review.get("comment", "")
            
            # Отправляем ответ
            response_text = BotConfig.REVIEW_RESPONSE_TEXT()
            await self.starvell.send_message(chat_id, response_text)
            
            # Помечаем как обработанный
            self._reviewed_orders.add(order_id)
            
            logger.info(f"⭐ Отправлен автоответ на отзыв (рейтинг: {rating}) для заказа {order_id[:8]}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа на отзыв для заказа {order_id}: {e}")
            # Не добавляем в обработанные, чтобы попробовать ещё раз
