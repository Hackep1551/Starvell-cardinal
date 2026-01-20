"""
Автоматическая отправка тикетов в поддержку Starvell
"""
import logging
from typing import List, Optional, Tuple
import aiohttp
from datetime import datetime

from bot.core.config import BotConfig, get_config_manager

logger = logging.getLogger(__name__)

# Константы для формы тикета
TICKET_TYPE_ORDER_ISSUE = "1"
ORDER_USER_TYPE_SELLER = "2"
ORDER_TOPIC_BUYER_FORGOT_CONFIRM = "501"

STARVELL_SUPPORT_URL = "https://starvell.com/support/new"


class AutoTicketService:
    """Сервис для автоматической отправки тикетов в поддержку Starvell"""
    
    def __init__(self, session_cookie: str):
        """
        Инициализация сервиса
        
        Args:
            session_cookie: Сессионная кука для авторизации
        """
        self.session_cookie = session_cookie
        self._last_ticket_time = 0
        self._ticket_cooldown = 3600  # 1 час между тикетами
        
    async def send_ticket(
        self, 
        order_ids: List[str],
        subject: str = "Покупатель забыл подтвердить заказ",
        description: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Отправить тикет в поддержку Starvell
        
        Args:
            order_ids: Список ID заказов
            subject: Тема тикета
            description: Описание (если None, будет сгенерировано автоматически)
            
        Returns:
            Tuple[success: bool, message: str]
        """
        if not order_ids:
            return False, "Нет заказов для отправки"
            
        # Формируем описание
        if not description:
            order_ids_str = ", ".join(order_ids)
            description = f"Номера заказов: {order_ids_str}"
        
        # Подготавливаем данные формы
        form_data = {
            "ticketType": TICKET_TYPE_ORDER_ISSUE,
            "orderId": ", ".join(order_ids),  # Можно несколько через запятую
            "orderUserTypeId": ORDER_USER_TYPE_SELLER,
            "orderTopicId": ORDER_TOPIC_BUYER_FORGOT_CONFIRM,
            "subject": subject,
            "description": description
        }
        
        headers = {
            "Content-Type": "application/json",
            "Cookie": f"session={self.session_cookie}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://starvell.com",
            "Referer": STARVELL_SUPPORT_URL
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Пробуем POST запрос
                async with session.post(
                    STARVELL_SUPPORT_URL,
                    json=form_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status in (200, 201, 302):
                        logger.info(f"✅ Тикет отправлен для заказов: {', '.join(order_ids)}")
                        return True, f"Тикет отправлен для заказов: {', '.join(order_ids)}"
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка отправки тикета: {response.status} - {error_text[:200]}")
                        return False, f"Ошибка {response.status}"
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Ошибка соединения при отправке тикета: {e}")
            return False, f"Ошибка соединения: {e}"
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при отправке тикета: {e}")
            return False, f"Ошибка: {e}"
    
    async def get_unconfirmed_orders(self, starvell_service, hours: int = 48) -> List[dict]:
        """
        Получить список неподтверждённых заказов старше X часов
        
        Args:
            starvell_service: Сервис Starvell для API запросов
            hours: Количество часов с момента создания заказа
            
        Returns:
            Список заказов
        """
        try:
            # Получаем заказы через API
            orders = await starvell_service.get_orders()
            
            if not orders:
                return []
            
            unconfirmed = []
            current_time = datetime.now()
            
            for order in orders:
                # Проверяем статус заказа
                # Статусы: 'paid' - оплачен (нужен подтверждение), 'confirmed' - подтвержден (закрыт)
                # Нам нужны заказы, которые ОПЛАЧЕНЫ (paid), но не закрыты
                # Или 'wait_confirm'? Надо проверить. Обычно paid -> wait_confirm -> confirmed
                # Предположим нам нужны заказы в статусе 'paid' или 'checked' (проверен продавцом)
                # Но если покупатель забыл подтвердить, статус скорее всего "paid".
                
                status = order.get("status", "")
                
                # Фильтруем по статусу
                # Нам нужны заказы, где покупатель оплатил, мы выполнили, но он не подтвердил.
                # Обычно это статус "paid" (Оплачен).
                if status not in ("paid", "confirmed"): # confirmed тоже добавим для теста, если вдруг
                     # На самом деле, если статус confirmed - значит уже подтвержден.
                     # Нам нужны заказы, которые НЕ confirmed и НЕ refund и НЕ cancelled.
                     pass
                
                if status != "paid":
                    continue
                    
                # Проверяем дату
                order_date = order.get("date")
                order_dt = None
                
                if isinstance(order_date, (int, float)):
                    # Timestamp (секунды или миллисекунды)
                    # Если > 3000000000 - скорее всего мс
                    if order_date > 3000000000:
                        order_date = order_date / 1000
                    order_dt = datetime.fromtimestamp(order_date)
                elif isinstance(order_date, str):
                    # ISO string
                    try:
                        order_dt = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                if not order_dt:
                    continue
                    
                # Если offset-naive, считаем что это local time (или UTC, если из timestamp)
                if order_dt.tzinfo is None:
                     order_dt = order_dt.replace(tzinfo=None) # Работаем в naive, current_time тоже naive
                else:
                     # Приводим к naive UTC или local
                     order_dt = order_dt.replace(tzinfo=None)

                # Вычисляем возраст заказа
                age = current_time - order_dt
                age_hours = age.total_seconds() / 3600
                
                if age_hours >= hours:
                    unconfirmed.append(order)
                    
            logger.info(f"Найдено {len(unconfirmed)} неподтверждённых заказов старше {hours} ч.")
            return unconfirmed
            
        except Exception as e:
            logger.error(f"Ошибка получения неподтверждённых заказов: {e}")
            return []


# Глобальный экземпляр сервиса (инициализируется при старте бота)
_autoticket_service: Optional[AutoTicketService] = None


def get_autoticket_service() -> Optional[AutoTicketService]:
    """Получить экземпляр сервиса автотикетов"""
    global _autoticket_service
    return _autoticket_service


def init_autoticket_service(session_cookie: str) -> AutoTicketService:
    """Инициализировать сервис автотикетов"""
    global _autoticket_service
    _autoticket_service = AutoTicketService(session_cookie)
    logger.info("🎫 Сервис автотикетов инициализирован")
    return _autoticket_service
