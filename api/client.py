"""Основной клиент API"""

import logging
from typing import Optional, List, Dict, Any

from .config import Config
from .session import SessionManager
from .utils import BuildIdCache, extract_build_id, extract_sid_from_cookies
from .exceptions import NotFoundError

logger = logging.getLogger("API")

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
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить профиль пользователя по ID
        
        Args:
            user_id: ID пользователя в Starvell
            
        Returns:
            dict: Данные профиля (nickname, name, id и др.) или None если не найден
        """
        try:
            # Используем URL вида https://starvell.com/_next/data/{build_id}/user/{user_id}.json
            data = await self._get_next_data(f"user/{user_id}.json")
            page_props = data.get("pageProps", {})
            
            # Извлекаем данные пользователя
            user_data = page_props.get("user")
            if user_data:
                return {
                    "id": user_data.get("id"),
                    "nickname": user_data.get("nickname") or user_data.get("name"),
                    "name": user_data.get("name"),
                    "username": user_data.get("username"),
                    "avatar": user_data.get("avatar"),
                }
            
            return None
        except Exception as e:
            logger.debug(f"Не удалось получить профиль пользователя {user_id}: {e}")
            return None
        
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
    
    async def find_chat_by_user_id(self, user_id: str) -> Optional[str]:
        """
        Найти ID чата с конкретным пользователем
        
        Args:
            user_id: ID пользователя для поиска
            
        Returns:
            str | None: ID чата если найден, иначе None
        """
        try:
            chats_data = await self.get_chats()
            chats = chats_data.get("pageProps", {}).get("chats", [])
            
            for chat in chats:
                # Проверяем companion (для личных чатов)
                companion = chat.get("companion", {})
                if companion and str(companion.get("id")) == str(user_id):
                    return chat.get("id")
                
                # Проверяем members (для групповых чатов)
                members = chat.get("members", [])
                for member in members:
                    if str(member.get("id")) == str(user_id):
                        return chat.get("id")
            
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска чата для пользователя {user_id}: {e}")
            return None
        
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
    
    async def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Получить детальную информацию о заказе
        
        Args:
            order_id: ID заказа (например, 019b95a8-df7d-683c-17a9-3889985947d6)
            
        Returns:
            dict: Полные данные заказа включая chat_id, buyer, lot и т.д.
        """
        return await self._get_next_data(
            f"order/{order_id}.json",
            params=f"?order_id={order_id}",
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
        logger.debug(f"🚀 Отправка bump запроса: game_id={game_id}, categories={category_ids}")
        
        # Убедимся, что у нас есть SID перед bump запросом
        if not self.session.get_sid():
            logger.debug("⚠️ SID отсутствует, получаем через user_info...")
            await self.get_user_info()
        
        response = await self.session.post_json(
            f"{self.config.API_URL}/offers/bump",
            data={"gameId": game_id, "categoryIds": category_ids},
            referer=referer or self.config.BASE_URL,
            include_sid=True,
        )
        
        logger.debug(f"📨 Ответ bump API: {response}")
        
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
        logger.debug(f"🔍 Запрашиваю страницу пользователя {user_id}...")
        
        html = await self.session.get_text(
            f"{self.config.BASE_URL}/users/{user_id}",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "cache-control": "max-age=0",
                "upgrade-insecure-requests": "1",
            },
        )
        
        logger.debug(f"📄 Получена HTML-страница, размер: {len(html)} байт")
        
        # Парсим __NEXT_DATA__
        import re
        import json
        
        marker = '<script id="__NEXT_DATA__" type="application/json">'
        idx = html.find(marker)
        if idx == -1:
            logger.warning("⚠️ Не найден маркер __NEXT_DATA__ на странице")
            return []
            
        json_start = html.find('{', idx)
        if json_start == -1:
            logger.warning("⚠️ Не найдено начало JSON в __NEXT_DATA__")
            return []
            
        json_end = html.find('</script>', json_start)
        if json_end == -1:
            logger.warning("⚠️ Не найден конец JSON в __NEXT_DATA__")
            return []
            
        data = json.loads(html[json_start:json_end])
        logger.debug("✅ JSON успешно распарсен")
        
        page_props = data.get("props", {}).get("pageProps", {})
        categories = page_props.get("categoriesWithOffers", [])
        
        logger.debug(f"📊 Найдено категорий: {len(categories)}")
        
        offers = []
        for category in categories:
            category_offers = category.get("offers", [])
            logger.debug(f"  - Категория: {len(category_offers)} лотов")
            
            for offer in category_offers:
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
        
        logger.debug(f"✅ Всего собрано лотов: {len(offers)}")
        return offers
    
    async def get_user_categories(self, user_id: int) -> Dict[int, List[int]]:
        """
        Получить все категории с лотами пользователя, сгруппированные по играм
        
        Args:
            user_id: ID пользователя
            
        Returns:
            dict: Словарь {game_id: [category_ids]} - все категории пользователя по играм
        """
        logger.debug(f"🔍 Запрашиваю категории пользователя {user_id}...")
        
        html = await self.session.get_text(
            f"{self.config.BASE_URL}/users/{user_id}",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "cache-control": "max-age=0",
                "upgrade-insecure-requests": "1",
            },
        )
        
        # Парсим __NEXT_DATA__
        import json
        
        marker = '<script id="__NEXT_DATA__" type="application/json">'
        idx = html.find(marker)
        if idx == -1:
            logger.warning("⚠️ Не найден маркер __NEXT_DATA__ на странице")
            return {}
            
        json_start = html.find('{', idx)
        json_end = html.find('</script>', json_start)
        if json_start == -1 or json_end == -1:
            logger.warning("⚠️ Ошибка парсинга JSON")
            return {}
            
        data = json.loads(html[json_start:json_end])
        page_props = data.get("props", {}).get("pageProps", {})
        
        logger.debug(f"📊 pageProps keys: {list(page_props.keys())}")
        
        # Правильный путь - userProfileOffers, а не categoriesWithOffers!
        categories = page_props.get("userProfileOffers", [])
        
        logger.debug(f"📊 RAW userProfileOffers: {categories[:2] if categories else 'EMPTY'}")
        logger.debug(f"📊 Всего userProfileOffers: {len(categories)}")
        
        # Группируем категории по играм
        game_categories = {}
        for idx, category in enumerate(categories):
            logger.debug(f"  - Категория #{idx}: keys={list(category.keys())}")
            
            game_id = category.get("gameId")
            category_id = category.get("id")  # ID самой категории
            offers = category.get("offers", [])
            offer_count = len(offers)
            
            logger.debug(f"    gameId={game_id}, categoryId={category_id}, offers={offer_count}")
            
            if game_id and category_id and offer_count > 0:
                if game_id not in game_categories:
                    game_categories[game_id] = []
                if category_id not in game_categories[game_id]:
                    game_categories[game_id].append(category_id)
                    logger.debug(f"    ✅ Добавлено: game {game_id} -> category {category_id}")
                    
        logger.debug(f"📦 Найдено игр: {len(game_categories)}")
        for game_id, cat_ids in game_categories.items():
            logger.debug(f"  🎮 Game {game_id}: категории {cat_ids}")
            
        return game_categories
    
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
