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
        # Загружаем все текущие заказы как уже обработанные
        # Это предотвращает отправку автоответов на старые заказы при первом запуске
        await self._initialize_processed_orders()
        logger.info("Сервис автоответов запущен")
        
    async def stop(self):
        """Остановка сервиса"""
        logger.info("Сервис автоответов остановлен")
    
    async def _initialize_processed_orders(self):
        """
        Инициализация: загружаем все текущие заказы как уже обработанные
        Это предотвращает отправку автоответов на старые заказы при включении функции
        """
        try:
            logger.info("Инициализация автоответов: загрузка существующих заказов...")
            
            # Получаем все заказы
            orders = await self.starvell.get_orders()
            
            for order in orders:
                order_id = order.get("id")
                if not order_id:
                    continue
                
                status = order.get("status", "")
                review = order.get("review")
                
                # Добавляем завершённые заказы в обработанные
                if status == "COMPLETED" or status == "completed":
                    self._confirmed_orders.add(order_id)
                
                # Добавляем заказы с отзывами в обработанные
                if review:
                    self._reviewed_orders.add(order_id)
            
            logger.info(f"Загружено {len(self._confirmed_orders)} завершённых заказов и {len(self._reviewed_orders)} отзывов")
            logger.info("✅ Автоответы будут отправляться только на новые заказы")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации обработанных заказов: {e}", exc_info=True)
        
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

            # Получаем все заказы (свежий кэш от мониторинга переиспользуем)
            orders = await self.starvell.get_orders(max_age=20)
            
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
            if get_config_manager().is_blacklisted(buyer_id):
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
            if get_config_manager().is_blacklisted(buyer_id):
                logger.debug(f"Автоответ на отзыв заказа {order_id[:8]} пропущен (покупатель {buyer_id} в ЧС)")
                self._reviewed_orders.add(order_id)  # Помечаем как обработанный
                return
        
        try:
            # Получаем детали заказа - там chat_id и полные данные отзыва
            order_details = await self.starvell.get_order_details(order_id)
            page_props = order_details.get("pageProps", {})

            # Извлекаем chat_id
            chat_id = None
            order_obj = page_props.get("order") or {}
            if "chat" in page_props and isinstance(page_props["chat"], dict):
                chat_id = page_props["chat"].get("id")
            elif order_obj.get("chatId"):
                chat_id = order_obj.get("chatId")
            elif "chatId" in order:
                chat_id = order.get("chatId")
            elif "chat_id" in order:
                chat_id = order.get("chat_id")

            if not chat_id:
                logger.warning(f"Не удалось найти chat_id для заказа {order_id} (отзыв)")
                # Помечаем как обработанный, чтобы не спамить логи
                self._reviewed_orders.add(order_id)
                return

            # Полный отзыв из деталей заказа (в списке заказов он урезанный)
            full_review = page_props.get("review") or order_obj.get("review") or review
            rating = full_review.get("rating", "N/A")
            comment = full_review.get("content") or full_review.get("comment") or ""

            # Отправляем ответ
            response_text = BotConfig.REVIEW_RESPONSE_TEXT()
            await self.starvell.send_message(chat_id, response_text)

            # Помечаем как обработанный
            self._reviewed_orders.add(order_id)

            logger.info(f"⭐ Отправлен автоответ на отзыв (рейтинг: {rating}) для заказа {order_id[:8]}")

            # Уведомляем админов о новом отзыве
            await self._notify_new_review(order, full_review, rating, comment)

        except Exception as e:
            logger.error(f"Ошибка при отправке ответа на отзыв для заказа {order_id}: {e}")
            # Не добавляем в обработанные, чтобы попробовать ещё раз

    async def _notify_new_review(self, order: Dict, review: Dict, rating, comment: str):
        """Отправить админам уведомление о новом отзыве"""
        try:
            from bot.core.notifications import get_notification_manager, NotificationType
            notif_manager = get_notification_manager()
            if not notif_manager:
                return

            stars = "⭐" * rating if isinstance(rating, int) else str(rating)

            buyer = order.get("user") or {}
            author = buyer.get("username") or buyer.get("nickname") or "Покупатель"

            text = f"<b>Оценка:</b> {stars}\n<b>От:</b> {author}"
            if comment:
                text += f"\n\n<i>{comment[:500]}</i>"

            # Доп. оценки скорости (Starvell отдаёт их в деталях отзыва)
            delivery_speed = review.get("deliverySpeedRating")
            response_speed = review.get("responseSpeedRating")
            if delivery_speed:
                text += f"\n\n<b>Скорость выдачи:</b> {delivery_speed}/5"
            if response_speed:
                text += f"\n<b>Скорость ответа:</b> {response_speed}/5"

            await notif_manager.notify_all_admins(NotificationType.NEW_REVIEW, text)
        except Exception as e:
            logger.debug(f"Не удалось отправить уведомление об отзыве: {e}")
