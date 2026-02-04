"""
Автоматическая отправка тикетов в поддержку Starvell
"""
import logging
from typing import List, Optional, Tuple
import aiohttp
from datetime import datetime

from bot.core.config import BotConfig, get_config_manager

logger = logging.getLogger(__name__)

# API endpoints
STARVELL_SUPPORT_API = "https://starvell.com/api/support/create"
STARVELL_BASE_URL = "https://starvell.com"

# Константы для формы тикета (из реального API)
TICKET_TYPE_ORDER_ISSUE = "1"
ORDER_USER_TYPE_SELLER = "2"
ORDER_TOPIC_BUYER_FORGOT_CONFIRM = "501"


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
        Отправить тикет в поддержку Starvell через API
        
        Args:
            order_ids: Список ID заказов (UUID формат, будет сконвертирован в short ID)
            subject: Тема тикета
            description: Описание (если None, будет сгенерировано автоматически)
            
        Returns:
            Tuple[success: bool, message: str]
        """
        if not order_ids:
            return False, "Нет заказов для отправки"
        
        if not self.session_cookie:
            return False, "Отсутствует session_cookie"
        
        # Берем первый заказ для формы (можно отправить только 1 заказ за раз)
        order_id_full = order_ids[0]
        
        # Конвертируем UUID в short ID (#41D4CCAE формат)
        # Берем последние 8 символов UUID без дефисов
        order_id_short = order_id_full.replace("-", "")[-8:].upper()
        order_id_formatted = f"#{order_id_short}"
        
        # Формируем описание
        if not description:
            description = subject
        
        # Подготавливаем данные формы (FormData, НЕ JSON!)
        form_data = aiohttp.FormData()
        form_data.add_field('ticketType', TICKET_TYPE_ORDER_ISSUE)
        form_data.add_field('subject', subject)
        form_data.add_field('description', description)
        form_data.add_field('orderId', order_id_formatted)
        form_data.add_field('orderUserTypeId', ORDER_USER_TYPE_SELLER)
        form_data.add_field('orderTopicId', ORDER_TOPIC_BUYER_FORGOT_CONFIRM)
        
        headers = {
            "Cookie": f"session={self.session_cookie}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": STARVELL_BASE_URL,
            "Referer": f"{STARVELL_BASE_URL}/support/new",
            "Accept": "*/*",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Отправка тикета для заказа {order_id_full}")
                logger.debug(f"Short ID: {order_id_formatted}")
                logger.debug(f"Тема: {subject}")
                
                async with session.post(
                    STARVELL_SUPPORT_API,
                    data=form_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()
                    
                    logger.debug(f"Ответ API: {response.status}")
                    if BotConfig.DEBUG():
                        logger.debug(f"Тело ответа: {response_text[:500]}")
                    
                    if response.status == 200:
                        logger.info(f"✅ Тикет отправлен для заказа: {order_id_formatted} ({order_id_full[:16]}...)")
                        
                        if len(order_ids) > 1:
                            return True, f"Тикет #{order_id_formatted} отправлен (из {len(order_ids)})"
                        else:
                            return True, f"Тикет {order_id_formatted} отправлен"
                    elif response.status == 401:
                        logger.error(f"❌ Ошибка авторизации (401) - проверьте session_cookie")
                        return False, "Ошибка авторизации (истекла сессия)"
                    elif response.status == 400:
                        logger.error(f"❌ Неверные данные (400)")
                        logger.error(f"Ответ: {response_text[:300]}")
                        return False, "Неверные данные запроса"
                    else:
                        logger.error(f"❌ Ошибка отправки тикета: {response.status}")
                        logger.error(f"Ответ: {response_text[:300]}")
                        return False, f"Ошибка API: {response.status}"
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Ошибка соединения при отправке тикета: {e}")
            return False, f"Ошибка соединения: {str(e)[:100]}"
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при отправке тикета: {e}", exc_info=True)
            return False, f"Ошибка: {str(e)[:100]}"
    
    async def get_unconfirmed_orders(self, starvell_service, hours: int = 48) -> List[dict]:
        """
        Получить список неподтверждённых заказов старше X часов
        
        Args:
            starvell_service: Сервис Starvell для API запросов
            hours: Количество часов с момента создания заказа
            
        Returns:
            Список заказов с ID и временем создания
        """
        try:
            # Получаем заказы через API
            orders_data = await starvell_service.get_orders()
            
            if not orders_data:
                logger.debug("Нет заказов от API")
                return []
            
            unconfirmed = []
            current_time = datetime.now()
            
            for order in orders_data:
                # ID заказа
                order_id = order.get("id")
                if not order_id:
                    continue
                
                # Проверяем статус заказа
                # Статусы Starvell: CREATED, PAID, CONFIRMED, REFUND, CANCELLED
                # Неподтвержденные = CREATED (оплачен, но покупатель не подтвердил получение)
                status = order.get("status", "")
                
                # Нам нужны заказы в статусе CREATED (awaiting confirmation)
                if status != "CREATED":
                    continue
                
                # Проверяем дату создания заказа
                created_at = order.get("createdAt")
                order_dt = None
                
                if isinstance(created_at, str):
                    # ISO string формат: "2026-02-03T14:25:48.953Z"
                    try:
                        # Убираем Z и парсим
                        created_at_clean = created_at.replace('Z', '+00:00')
                        order_dt = datetime.fromisoformat(created_at_clean)
                        # Конвертируем в naive datetime для сравнения
                        if order_dt.tzinfo is not None:
                            order_dt = order_dt.replace(tzinfo=None)
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Ошибка парсинга даты {created_at}: {e}")
                        continue
                elif isinstance(created_at, (int, float)):
                    # Timestamp (секунды или миллисекунды)
                    timestamp = created_at
                    if timestamp > 3000000000:  # Если > 2065 год, значит миллисекунды
                        timestamp = timestamp / 1000
                    order_dt = datetime.fromtimestamp(timestamp)
                
                if not order_dt:
                    logger.debug(f"Не удалось определить дату для заказа {order_id}")
                    continue
                
                # Вычисляем возраст заказа в часах
                age = current_time - order_dt
                age_hours = age.total_seconds() / 3600
                
                logger.debug(f"Заказ {order_id[:8]}... возраст {age_hours:.1f}ч (статус: {status})")
                
                # Если заказ старше указанного времени
                if age_hours >= hours:
                    unconfirmed.append({
                        "id": order_id,
                        "createdAt": created_at,
                        "age_hours": age_hours,
                        "status": status
                    })
            
            if unconfirmed:
                logger.info(f"🎫 Найдено {len(unconfirmed)} неподтверждённых заказов старше {hours}ч")
                for o in unconfirmed[:3]:  # Показываем первые 3
                    logger.info(f"  • {o['id'][:16]}... ({o['age_hours']:.1f}ч)")
            else:
                logger.debug(f"Неподтверждённых заказов старше {hours}ч не найдено")
                
            return unconfirmed
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения неподтверждённых заказов: {e}", exc_info=True)
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
