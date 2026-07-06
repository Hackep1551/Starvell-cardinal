"""Основной клиент API"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from .config import Config
from .session import SessionManager
from .utils import BuildIdCache, extract_build_id, extract_sid_from_cookies, extract_next_data
from .exceptions import NotFoundError, ForbiddenError

logger = logging.getLogger("API")

class StarAPI:
    """
    Главный класс для работы с Starvell API
    
    Пример использования:
        async with StarAPI(session_cookie="your_cookie") as api:
            user = await api.get_user_info()
            chats = await api.get_chats()
    """

    # Starvell за QRATOR отдаёт Socket.IO на отдельном порту
    QRATOR_WS_PORT = 8443

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
        self._qrator_detected: Optional[bool] = None
        self._socket_io_available: Optional[bool] = None
        
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
            page_props = await self._get_user_page_props(user_id)
            user_data = self._extract_profile_user(page_props)
            if not user_data:
                return None

            return {
                "id": user_data.get("id"),
                "nickname": user_data.get("nickname") or user_data.get("name") or user_data.get("username"),
                "name": user_data.get("name"),
                "username": user_data.get("username"),
                "avatar": user_data.get("avatar"),
            }
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
        try:
            data = await self.session.post_json(
                f"{self.config.API_URL}/messages/list",
                data={"chatId": chat_id, "limit": limit},
                referer=f"{self.config.BASE_URL}/chat",
                retry=True,
            )

            return data if isinstance(data, list) else []
        except NotFoundError:
            data = await self._get_next_data(
                f"chat/{chat_id}.json",
                params=f"?chat_id={chat_id}",
            )
            active_chat = data.get("pageProps", {}).get("activeChat") or {}
            last_message = active_chat.get("lastMessage")
            if isinstance(last_message, dict):
                return [last_message]
            return []
        
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
    
    async def mark_chat_as_read(self, chat_id: str) -> bool:
        """
        Пометить чат как прочитанный
        
        Args:
            chat_id: ID чата
            
        Returns:
            bool: True если успешно
        """
        try:
            # Пробуем разные возможные эндпоинты
            endpoints = [
                f"{self.config.API_URL}/messages/read",
                f"{self.config.API_URL}/chats/read", 
                f"{self.config.API_URL}/chat/read",
            ]
            
            for endpoint in endpoints:
                try:
                    await self.session.post_json(
                        endpoint,
                        data={"chatId": chat_id},
                        referer=f"{self.config.BASE_URL}/chat/{chat_id}",
                        retry=True,  # идемпотентно, повтор безопасен
                    )
                    return True
                except Exception:
                    continue
                    
            # Если ни один endpoint не сработал, 
            # просто получаем сообщения - это может пометить как прочитанное
            await self.get_messages(chat_id, limit=1)
            return True
            
        except Exception as e:
            logger.debug(f"Не удалось пометить чат {chat_id} как прочитанный: {e}")
            return False
    
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
        Получить список продаж (только первые 20 через Next.js Data API)
        
        ⚠️ DEPRECATED: Используйте get_all_orders() для получения ВСЕХ заказов
        
        Returns:
            dict: Данные о продажах (ограничено 20 заказами)
        """
        return await self._get_next_data("account/sells.json")
    
    async def get_all_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить ВСЕ заказы с информацией о покупателях
        
        Использует гибридный подход
        
        Args:
            status: Фильтр по статусу ("CREATED", "COMPLETED", "REFUND", "PRE_CREATED")
                   Если None - возвращает все заказы
        
        Returns:
            list: Список всех заказов с информацией о покупателях
        """
        payload = {"filter": {}}
        if status:
            payload["filter"]["status"] = status
        
        all_orders = await self.session.post_json(
            f"{self.config.API_URL}/orders/list",
            data=payload,
            referer=f"{self.config.BASE_URL}/account/sells",
            retry=True,  # read-only, повтор безопасен
        )
        
        if not isinstance(all_orders, list):
            all_orders = []
        
        try:
            data = await self._get_next_data("account/sells.json")
            page_props = data.get("pageProps", {})
            recent_orders = page_props.get("orders", [])
            
            user_map = {}
            for order in recent_orders:
                order_id = order.get("id")
                user = order.get("user")
                if order_id and user:
                    user_map[order_id] = user
            
            for order in all_orders:
                order_id = order.get("id")
                if order_id in user_map:
                    order["user"] = user_map[order_id]
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Не удалось обогатить заказы данными пользователей: {e}")
        
        return all_orders
        
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

    async def create_support_ticket(self, fields: Dict[str, str]) -> Dict[str, Any]:
        """
        Создать тикет в поддержку (multipart/form-data)

        Args:
            fields: Поля формы тикета (ticketType, orderId, subject и т.д.)

        Returns:
            dict: Ответ API
        """
        import aiohttp

        form = aiohttp.FormData(quote_fields=False)
        for key, value in fields.items():
            form.add_field(key, str(value), content_type='text/plain')

        return await self.session.post_form(
            f"{self.config.API_URL}/support/create",
            form_data=form,
            referer=f"{self.config.BASE_URL}/support/new",
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
        
    async def get_offer_info(self, offer_id) -> Dict[str, Any]:
        """
        Получить данные оффера напрямую через API

        Args:
            offer_id: ID оффера

        Returns:
            dict: Данные оффера (price, availability, isActive и др.)
        """
        return await self.session.get_json(
            f"{self.config.API_URL}/offers/{offer_id}",
            referer=f"{self.config.BASE_URL}/account/sells",
        )

    async def update_offer(
        self,
        offer_id,
        availability: Optional[int] = None,
        is_active: Optional[bool] = None,
        price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Изменить настройки оффера: активность, количество, цену

        Args:
            offer_id: ID оффера
            availability: Количество товара
            is_active: Включить/выключить лот
            price: Цена (в копейках, как отдаёт API)

        Returns:
            dict: Ответ API
        """
        # API требует availability и price даже при смене только isActive —
        # недостающие значения берём из текущих данных оффера
        if is_active is not None and (availability is None or price is None):
            info = await self.get_offer_info(offer_id)
            if availability is None:
                availability = info.get("availability") or 1
            if price is None:
                raw_price = info.get("price") or 0
                try:
                    price = int(float(raw_price))
                except (ValueError, TypeError):
                    price = 0

        payload = {}
        if availability is not None:
            payload["availability"] = int(availability)
        if is_active is not None:
            payload["isActive"] = bool(is_active)
        if price is not None:
            payload["price"] = str(int(price))

        if not payload:
            raise ValueError("Не переданы параметры для изменения оффера")

        logger.debug(f"✏️ Обновление оффера {offer_id}: {payload}")

        return await self.session.post_json(
            f"{self.config.API_URL}/offers/{offer_id}/partial-update",
            data=payload,
            referer=f"{self.config.BASE_URL}/account/sells",
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
        
        # Referer как при поднятии из кабинета продавца — меньше 403 от антибота
        response = await self.session.post_json(
            f"{self.config.API_URL}/offers/bump",
            data={"gameId": game_id, "categoryIds": category_ids},
            referer=referer or f"{self.config.BASE_URL}/account/sells",
            include_sid=True,
            retry=True,  # повторный bump безвреден, сервер сам держит кулдаун
        )
        
        logger.debug(f"📨 Ответ bump API: {response}")
        
        return {
            "request": {"gameId": game_id, "categoryIds": category_ids},
            "response": response,
        }
        
    # ==================== Пользователи ====================

    async def _resolve_profile_slug(self, user_id) -> Optional[str]:
        value = str(user_id or "").strip()
        if not value:
            return None

        if not value.isdigit():
            return value

        try:
            info = await self.get_user_info()
            user = info.get("user") or {}
            if str(user.get("id") or "") == value:
                return user.get("username") or user.get("nickname") or user.get("name") or value
        except Exception as e:
            logger.debug(f"Не удалось определить username для пользователя {value}: {e}")

        return value

    @staticmethod
    def _extract_profile_user(page_props: dict) -> Optional[dict]:
        for key in ("user", "profile", "profileUser", "seller", "currentUser"):
            value = page_props.get(key)
            if isinstance(value, dict):
                return value

        if page_props.get("id") or page_props.get("username"):
            return page_props

        return None

    async def _get_user_page_props(self, user_id) -> dict:
        """
        Получить pageProps профиля пользователя.

        Сначала пробуем Next.js Data API (лёгкий JSON, QRATOR к нему лояльнее),
        HTML-страница профиля — только как запасной вариант.
        """
        profile_slug = await self._resolve_profile_slug(user_id)
        if profile_slug:
            profile_slug = str(profile_slug).strip().lower()
        attempts = []

        if profile_slug:
            attempts.extend([
                (f"profile/{profile_slug}.json", ""),
                (f"profile/{profile_slug}.json", f"?username={profile_slug}"),
                (f"profile/{profile_slug}.json", f"?slug={profile_slug}"),
            ])

        attempts.extend([
            (f"users/{user_id}.json", f"?user_id={user_id}"),
            (f"user/{user_id}.json", f"?user_id={user_id}"),
        ])

        last_error = None
        for path, params in attempts:
            try:
                data = await self._get_next_data(path, params=params)
                page_props = data.get("pageProps", {})
                if page_props:
                    return page_props
            except Exception as e:
                last_error = e
                logger.debug(f"Data API {path} не сработал: {e}")

        if not profile_slug:
            if last_error:
                raise last_error
            raise NotFoundError(f"Профиль пользователя не найден: {user_id}")

        logger.debug(f"🔍 Запрашиваю HTML-страницу профиля {profile_slug}...")
        try:
            html = await self.session.get_text(
                f"{self.config.BASE_URL}/profile/{profile_slug}",
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "cache-control": "max-age=0",
                    "upgrade-insecure-requests": "1",
                },
            )
            data = extract_next_data(html)
            return data.get("props", {}).get("pageProps", {})
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить профиль пользователя {user_id} ({profile_slug}): {e}")
            if last_error:
                raise last_error
            raise

    async def get_user_offers(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить все офферы пользователя

        Args:
            user_id: ID пользователя

        Returns:
            list: Список офферов пользователя
        """
        page_props = await self._get_user_page_props(user_id)
        categories = page_props.get("categoriesWithOffers") or page_props.get("userProfileOffers") or []
        
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

        page_props = await self._get_user_page_props(user_id)

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
        HTTP heartbeat — fallback, когда Socket.IO недоступен.
        Реальный онлайн держится через websocket namespace /online.

        Returns:
            True если запрос успешен, False если ошибка
        """
        try:
            await self.get_chats()
            return True
        except Exception as chat_error:
            logger.debug(f"KeepAlive chat.json не сработал: {chat_error}")

        try:
            await self.get_user_info()
            return True
        except Exception as info_error:
            logger.debug(f"KeepAlive index.json не сработал: {info_error}")

        return False

    async def is_qrator_protected(self) -> bool:
        """Проверить, включён ли QRATOR (по заголовку Server главной страницы)"""
        if self._qrator_detected is not None:
            return self._qrator_detected

        try:
            headers = await self.session.head_headers(
                f"{self.config.BASE_URL}/",
                referer=f"{self.config.BASE_URL}/",
            )
            server = (headers.get("Server") or "").upper()
            self._qrator_detected = server == "QRATOR"
            if self._qrator_detected:
                logger.info(f"ℹ️ Обнаружен QRATOR — Socket.IO через порт {self.QRATOR_WS_PORT}")
        except Exception as e:
            logger.debug(f"Не удалось проверить QRATOR: {e}")
            self._qrator_detected = False

        return self._qrator_detected

    def _socket_io_url(self, transport: str = "websocket") -> str:
        """URL Socket.IO с учётом QRATOR-порта"""
        base = self.config.BASE_URL.rstrip("/")
        if self._qrator_detected:
            base = f"{base}:{self.QRATOR_WS_PORT}"
        if transport == "websocket":
            base = base.replace("https://", "wss://")
        return f"{base}/socket.io/?EIO=4&transport={transport}"

    async def is_socket_io_available(self) -> bool:
        """Проверить, отвечает ли Socket.IO (результат кэшируется)"""
        if self._socket_io_available is not None:
            return self._socket_io_available

        await self.is_qrator_protected()

        if self._qrator_detected:
            # За QRATOR polling-transport закрыт, проверяем сразу websocket
            try:
                ws = await asyncio.wait_for(
                    self.session.ws_connect(
                        self._socket_io_url("websocket"),
                        referer=f"{self.config.BASE_URL}/",
                        headers={"origin": self.config.BASE_URL},
                    ),
                    timeout=12.0,
                )
                await ws.close()
                self._socket_io_available = True
                logger.info(f"✅ Socket.IO доступен (QRATOR :{self.QRATOR_WS_PORT})")
            except Exception as e:
                logger.warning(f"⚠️ Socket.IO websocket probe не прошёл: {e}")
                self._socket_io_available = False
            return self._socket_io_available

        try:
            status = await self.session.probe_status(
                self._socket_io_url("polling"),
                referer=f"{self.config.BASE_URL}/",
            )
            self._socket_io_available = status < 400
        except Exception:
            self._socket_io_available = False

        if not self._socket_io_available:
            logger.info("ℹ️ Socket.IO недоступен — онлайн через HTTP heartbeat")

        return self._socket_io_available

    async def connect_online_socket(self):
        """
        Открыть Socket.IO websocket для поддержания онлайна
        (тот же транспорт, что использует фронтенд Starvell)
        """
        if not await self.is_socket_io_available():
            raise NotFoundError("Socket.IO недоступен на Starvell")

        return await self.session.ws_connect(
            self._socket_io_url("websocket"),
            referer=f"{self.config.BASE_URL}/",
            headers={
                "origin": self.config.BASE_URL,
                "cache-control": "no-cache",
                "pragma": "no-cache",
            },
        )
