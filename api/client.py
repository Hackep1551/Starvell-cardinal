"""Основной клиент API"""

from typing import Optional, List, Dict, Any

from .config import Config
from .session import SessionManager
from .utils import BuildIdCache, extract_build_id, extract_sid_from_cookies
from .exceptions import NotFoundError


class StarAPI:
    """
    Главный класс для работы с Starvell API
    
    Пример использования:
        async with StarAPI(session_cookie="your_cookie") as api:
            user = await api.get_user_info()
            chats = await api.get_chats()
    """
    
    def __init__(
        self,
        session_cookie: str,
        user_agent: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Инициализация клиента
        
        Args:
            session_cookie: Cookie сессии пользователя
            user_agent: Кастомный User-Agent (опционально)
            timeout: Таймаут запросов в секундах (опционально)
        """
        self.config = Config(user_agent=user_agent, timeout=timeout)
        self.session = SessionManager(session_cookie, self.config)
        self._build_id_cache = BuildIdCache(ttl=self.config.BUILD_ID_CACHE_TTL)
        
    async def __aenter__(self):
        await self.session.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        
    async def close(self):
        """Закрыть сессию"""
        await self.session.close()
        
    # ==================== Внутренние методы ====================
    
    async def _get_build_id(self) -> str:
        """Получить build_id (с кэшированием)"""
        async def fetch():
            html = await self.session.get_text(
                f"{self.config.BASE_URL}/",
                headers={"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
            )
            return extract_build_id(html)
            
        return await self._build_id_cache.get(fetch)
        
    async def _get_next_data(
        self,
        path: str,
        params: Optional[str] = None,
        include_sid: bool = False,
    ) -> dict:
        """
        Получить данные из Next.js Data API
        
        Args:
            path: Путь (например, "index.json" или "chat.json")
            params: Query параметры (например, "?offer_id=123")
            include_sid: Включить SID cookie в запрос
        """
        for attempt in range(2):
            try:
                build_id = await self._get_build_id()
                url = f"{self.config.BASE_URL}/_next/data/{build_id}/{path}"
                
                if params:
                    url += params
                    
                data = await self.session.get_json(
                    url,
                    referer=f"{self.config.BASE_URL}/",
                    headers={"x-nextjs-data": "1"},
                    include_sid=include_sid,
                )
                
                return data
                
            except NotFoundError:
                if attempt == 0:
                    # Build ID устарел, сбрасываем кэш
                    self._build_id_cache.reset()
                    continue
                raise
                
        raise RuntimeError("Не удалось получить Next.js данные")
        
    # ==================== Аутентификация ====================
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Получить информацию о текущем пользователе
        
        Returns:
            dict: Информация о пользователе и статус авторизации
        """
        data = await self._get_next_data("index.json")
        page_props = data.get("pageProps", {})
        
        # Попытка получить SID из ответа
        sid = page_props.get("sid")
        if sid:
            self.session.set_sid(sid)
        
        return {
            "authorized": bool(page_props.get("user")),
            "user": page_props.get("user"),
            "sid": sid or self.session.get_sid(),
            "theme": page_props.get("currentTheme"),
        }
        
    # ==================== Чаты ====================
    
    async def get_chats(self) -> Dict[str, Any]:
        """
        Получить список всех чатов
        
        Returns:
            dict: Данные о чатах пользователя
        """
        return await self._get_next_data("chat.json")
        
    async def get_messages(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получить сообщения из чата
        
        Args:
            chat_id: ID чата
            limit: Максимальное количество сообщений
            
        Returns:
            list: Список сообщений
        """
        data = await self.session.post_json(
            f"{self.config.API_URL}/messages/list",
            data={"chatId": chat_id, "limit": limit},
            referer=f"{self.config.BASE_URL}/chat",
        )
        
        return data if isinstance(data, list) else []
        
    async def send_message(self, chat_id: str, content: str) -> Dict[str, Any]:
        """
        Отправить сообщение в чат
        
        Args:
            chat_id: ID чата
            content: Текст сообщения
            
        Returns:
            dict: Информация об отправленном сообщении
        """
        return await self.session.post_json(
            f"{self.config.API_URL}/messages/send",
            data={"chatId": chat_id, "content": content},
            referer=f"{self.config.BASE_URL}/chat/{chat_id}",
        )
        
    # ==================== Заказы ====================
    
    async def get_sells(self) -> Dict[str, Any]:
        """
        Получить список продаж
        
        Returns:
            dict: Данные о продажах
        """
        return await self._get_next_data("account/sells.json")
        
    async def refund_order(self, order_id: str) -> Dict[str, Any]:
        """
        Вернуть деньги за заказ
        
        Args:
            order_id: ID заказа
            
        Returns:
            dict: Результат операции
        """
        return await self.session.post_json(
            f"{self.config.API_URL}/orders/refund",
            data={"orderId": order_id},
            referer=f"{self.config.BASE_URL}/order/{order_id}",
            include_sid=True,
        )
        
    async def confirm_order(self, order_id: str) -> Dict[str, Any]:
        """
        Подтвердить заказ
        
        Args:
            order_id: ID заказа
            
        Returns:
            dict: Результат операции
        """
        return await self.session.post_json(
            f"{self.config.API_URL}/orders/confirm",
            data={"orderId": order_id},
            referer=f"{self.config.BASE_URL}/order/{order_id}",
            include_sid=True,
        )
        
    # ==================== Офферы ====================
    
    async def get_offer(self, offer_id: int) -> Dict[str, Any]:
        """
        Получить детальную информацию об оффере
        
        Args:
            offer_id: ID оффера
            
        Returns:
            dict: Данные об оффере
        """
        return await self._get_next_data(
            f"offers/{offer_id}.json",
            params=f"?offer_id={offer_id}",
            include_sid=True,
        )
        
    async def bump_offers(
        self,
        game_id: int,
        category_ids: List[int],
        referer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Поднять офферы в топ (bump)
        
        Args:
            game_id: ID игры
            category_ids: Список ID категорий для поднятия
            referer: Referer для запроса (опционально)
            
        Returns:
            dict: Результат операции с деталями запроса
        """
        response = await self.session.post_json(
            f"{self.config.API_URL}/offers/bump",
            data={"gameId": game_id, "categoryIds": category_ids},
            referer=referer or self.config.BASE_URL,
            include_sid=True,
        )
        
        return {
            "request": {"gameId": game_id, "categoryIds": category_ids},
            "response": response,
        }
        
    # ==================== Пользователи ====================
    
    async def get_user_offers(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить все офферы пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            list: Список офферов пользователя
        """
        html = await self.session.get_text(
            f"{self.config.BASE_URL}/users/{user_id}",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "cache-control": "max-age=0",
                "upgrade-insecure-requests": "1",
            },
        )
        
        # Парсим __NEXT_DATA__
        import re
        import json
        
        marker = '<script id="__NEXT_DATA__" type="application/json">'
        idx = html.find(marker)
        if idx == -1:
            return []
            
        json_start = html.find('{', idx)
        if json_start == -1:
            return []
            
        json_end = html.find('</script>', json_start)
        if json_end == -1:
            return []
            
        data = json.loads(html[json_start:json_end])
        
        page_props = data.get("props", {}).get("pageProps", {})
        categories = page_props.get("categoriesWithOffers", [])
        
        offers = []
        for category in categories:
            for offer in category.get("offers", []):
                offer_id = offer.get("id")
                price = offer.get("price")
                availability = offer.get("availability")
                
                # Формируем название
                brief = (offer.get("descriptions") or {}).get("rus", {}).get("briefDescription")
                attrs = offer.get("attributes", [])
                labels = [a.get("valueLabel") for a in attrs if a.get("valueLabel")]
                title_parts = [p for p in [brief, *labels] if p]
                title = ", ".join(title_parts) if title_parts else None
                
                offers.append({
                    "id": offer_id,
                    "title": title,
                    "availability": availability,
                    "price": price,
                    "url": f"{self.config.BASE_URL}/offers/{offer_id}" if offer_id else None,
                })
                
        return offers
    
    # ==================== Поддержка онлайна ====================
    
    async def keep_alive(self) -> bool:
        """
        Поддержка онлайн статуса (heartbeat)
        Отправляет heartbeat запрос к API
        
        Returns:
            True если запрос успешен, False если ошибка
        """
        try:
            # Отправляем heartbeat запрос
            response = await self.session.post_json(
                f"{self.config.API_URL}/user/heartbeat",
                data={},
                referer=f"{self.config.BASE_URL}/",
                include_sid=True,
            )
            return True
        except Exception as e:
            # Пробуем альтернативный метод - просто запрос к чатам
            try:
                await self.get_chats()
                return True
            except Exception:
                return False
