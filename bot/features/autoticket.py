"""
Автоматическая отправка тикетов в поддержку Starvell
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime
import time
import json
from pathlib import Path

from bot.core.config import BotConfig, get_config_manager
from api.exceptions import (
    StarAPIError,
    AuthenticationError,
    RateLimitError,
    ForbiddenError,
)

logger = logging.getLogger(__name__)


class AutoTicketService:
    """Сервис для автоматической отправки тикетов в поддержку Starvell"""
    
    # Путь к файлу с кешем времени последнего тикета
    CACHE_FILE = Path("cache") / "last_ticket_time.json"
    
    def __init__(self, session_cookie: str):
        """
        Инициализация сервиса
        
        Args:
            session_cookie: Сессионная кука для авторизации
        """
        self.session_cookie = session_cookie
        self._last_ticket_time = 0
        
        # Загружаем время последнего тикета из кеша
        self._load_last_ticket_time()
    
    def _load_last_ticket_time(self):
        """Загрузить время последнего тикета из файла"""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._last_ticket_time = data.get('last_ticket_time', 0)
                    
                    if self._last_ticket_time > 0:
                        last_time = datetime.fromtimestamp(self._last_ticket_time)
                        logger.info(f"📋 Загружено время последнего тикета: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить кеш последнего тикета: {e}")
            self._last_ticket_time = 0
    
    def _save_last_ticket_time(self):
        """Сохранить время последнего тикета в файл"""
        try:
            # Создаём директорию cache если её нет
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'last_ticket_time': self._last_ticket_time,
                'last_ticket_date': datetime.fromtimestamp(self._last_ticket_time).isoformat()
            }
            
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Сохранено время последнего тикета в кеш")
        except Exception as e:
            logger.error(f"❌ Не удалось сохранить кеш последнего тикета: {e}")
        
    def _get_ticket_type(self) -> str:
        """Получить тип тикета из конфига"""
        return BotConfig.AUTO_TICKET_TYPE()
    
    def _get_user_type_id(self) -> str:
        """Получить ID типа пользователя из конфига"""
        return BotConfig.AUTO_TICKET_USER_TYPE_ID()
    
    def _get_topic_id(self) -> str:
        """Получить ID темы тикета из конфига"""
        return BotConfig.AUTO_TICKET_TOPIC_ID()
    
    def can_send_ticket(self) -> bool:
        """
        Проверить, можно ли отправить тикет (прошёл ли интервал)
        
        Returns:
            bool: True если можно отправить, False если нужно подождать
        """
        if self._last_ticket_time == 0:
            # Никогда не отправляли - можно отправить
            logger.debug("📝 Тикеты ещё не отправлялись - можно создать")
            return True
        
        interval = BotConfig.AUTO_TICKET_INTERVAL()
        elapsed = time.time() - self._last_ticket_time
        
        if elapsed < interval:
            remaining = interval - elapsed
            last_time = datetime.fromtimestamp(self._last_ticket_time)
            logger.info(f"⏳ Тикет нельзя отправить - интервал не прошёл")
            logger.info(f"   Последний тикет: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"   Осталось ждать: {remaining:.0f} сек ({remaining/60:.1f} мин)")
            return False
        
        logger.debug(f"✅ Интервал прошёл ({elapsed:.0f}с) - можно создать тикет")
        return True
    
    def get_time_until_next_ticket(self) -> int:
        """
        Получить время до следующего возможного тикета в секундах
        
        Returns:
            int: Секунд до следующего тикета (0 если можно отправить сейчас)
        """
        if self._last_ticket_time == 0:
            return 0
        
        interval = BotConfig.AUTO_TICKET_INTERVAL()
        elapsed = time.time() - self._last_ticket_time
        remaining = max(0, interval - elapsed)
        
        return int(remaining)
        
    async def send_ticket(
        self,
        starvell_service,
        order_ids: List[str],
        subject: str = "Покупатель забыл подтвердить заказ",
        description: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Отправить тикет в поддержку Starvell через общий API-слой

        Args:
            starvell_service: StarvellService (даёт доступ к StarAPI)
            order_ids: Список ID заказов (первый - самый старый для поля orderId)
            subject: Тема тикета
            description: Описание (если None, будет сгенерировано из списка)

        Returns:
            Tuple[success: bool, message: str]
        """
        if not order_ids:
            return False, "Пустой список заказов"

        api = getattr(starvell_service, "api", None)
        if not api:
            return False, "API не инициализирован"

        # Первый заказ (самый старый) идёт в поле orderId
        main_order_id = order_ids[0]
        # Преобразуем в короткий ID (последние 8 символов без дефисов)
        main_order_short = main_order_id.replace('-', '')[-8:].upper()

        # Формируем описание со списком ВСЕХ заказов
        if not description:
            order_list = " ".join([
                f"#{order_id.replace('-', '')[-8:].upper()}"
                for order_id in order_ids
            ])
            description = f"{subject}\n\n{order_list}"

        fields = {
            'ticketType': self._get_ticket_type(),
            'orderId': main_order_short,  # Короткий ID (8 символов)
            'orderUserTypeId': self._get_user_type_id(),
            'orderTopicId': self._get_topic_id(),
            'subject': subject,
            'description': description,
        }

        logger.debug(f"🎫 Отправка тикета: orderId={main_order_short}, заказов={len(order_ids)}")

        try:
            await api.create_support_ticket(fields)

            # Обновляем время последнего тикета
            self._last_ticket_time = time.time()
            self._save_last_ticket_time()

            logger.info(f"✅ Тикет с {len(order_ids)} заказами создан успешно")
            return True, f"Тикет создан ({len(order_ids)} заказов)"

        except AuthenticationError:
            logger.error("❌ Ошибка авторизации — проверьте session_cookie")
            return False, "Ошибка авторизации (истекла сессия)"
        except RateLimitError:
            logger.error("❌ Rate limit — слишком много запросов")
            return False, "Слишком много запросов (rate limit)"
        except ForbiddenError:
            logger.error("❌ Доступ запрещён (антибот)")
            return False, "Доступ запрещён (антибот)"
        except StarAPIError as e:
            logger.error(f"❌ Ошибка API при отправке тикета: {e}")
            return False, f"Ошибка API: {str(e)[:100]}"
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при отправке тикета: {e}", exc_info=True)
            return False, f"Ошибка: {str(e)[:100]}"
    
    async def get_unconfirmed_orders(self, starvell_service, hours: int = 48) -> List[dict]:
        """
        Получить список неподтверждённых заказов старше X часов
        
        Args:
            starvell_service: Сервис Starvell для API запросов (StarAPI)
            hours: Количество часов с момента создания заказа
            
        Returns:
            Список заказов с ID и временем создания
        """
        try:
            orders_data = await starvell_service.get_all_orders(status="CREATED")
            
            if not orders_data:
                logger.debug("Нет заказов от API")
                return []
            
            
            unconfirmed = []
            # Starvell отдаёт даты в UTC — считаем возраст тоже в UTC,
            # иначе при локальной таймзоне возраст уезжает на её смещение
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
            
            # Счётчики для статистики
            stats = {
                "total": len(orders_data),
                "too_young": 0,
                "qualified": 0
            }
            
            for order in orders_data:
                # ID заказа
                order_id = order.get("id")
                if not order_id:
                    continue

                created_at = order.get("createdAt")
                order_dt = None
                
                if isinstance(created_at, str):
                    try:
                        # Убираем Z и парсим
                        created_at_clean = created_at.replace('Z', '+00:00')
                        order_dt = datetime.fromisoformat(created_at_clean)
                        # Дата без таймзоны — считаем что это UTC
                        if order_dt.tzinfo is None:
                            order_dt = order_dt.replace(tzinfo=timezone.utc)
                        logger.debug(f"Заказ {order_id[:8]}... дата: {created_at} → {order_dt}")
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Ошибка парсинга даты {created_at}: {e}")
                        continue
                elif isinstance(created_at, (int, float)):
                    # Timestamp (секунды или миллисекунды)
                    timestamp = created_at
                    if timestamp > 3000000000:  # Если > 2065 год, значит миллисекунды
                        timestamp = timestamp / 1000
                    order_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    logger.debug(f"Заказ {order_id[:8]}... timestamp: {created_at} → {order_dt}")
                else:
                    logger.warning(f"Заказ {order_id[:8]}... неизвестный формат даты: {type(created_at)} = {created_at}")
                
                if not order_dt:
                    logger.debug(f"Не удалось определить дату для заказа {order_id}")
                    continue
                
                # Вычисляем возраст заказа в часах
                age = current_time - order_dt
                age_hours = age.total_seconds() / 3600
                
                logger.debug(f"Заказ {order_id[:8]}... возраст {age_hours:.1f}ч (статус: CREATED)")
                
                # Если заказ старше указанного времени
                if age_hours >= hours:
                    stats["qualified"] += 1
                    unconfirmed.append({
                        "id": order_id,
                        "createdAt": created_at,
                        "age_hours": age_hours,
                        "status": "CREATED"
                    })
                else:
                    stats["too_young"] += 1
            
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
