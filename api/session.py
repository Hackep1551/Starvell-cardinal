"""Управление HTTP сессиями"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import ClientTimeout, ClientResponseError

from .config import Config
from .rate_limiter import throttle, setup_limiter
from .exceptions import (
    StarAPIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ForbiddenError,
    ServerError,
)

logger = logging.getLogger("API")


class SessionManager:
    """Менеджер HTTP сессий с retry логикой"""
    
    def __init__(self, session_cookie: str, config: Config):
        self.session_cookie = session_cookie
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._sid_cookie: Optional[str] = None
        setup_limiter(config.MAX_REQUESTS_PER_MINUTE)
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self):
        """Создать сессию"""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
    async def close(self):
        """Закрыть сессию"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    def _get_headers(self, referer: str = None, extra: Dict[str, str] = None) -> Dict[str, str]:
        """Получить заголовки для запроса"""
        headers = {
            "accept": "*/*",
            "accept-language": "ru,en;q=0.9",
            "user-agent": self.config.user_agent,
            **Config.BROWSER_HEADERS,
        }

        if referer:
            headers["referer"] = referer
            
        if extra:
            headers.update(extra)
            
        return headers
        
    def _get_cookies(self, include_sid: bool = False) -> Dict[str, str]:
        """Получить cookies для запроса"""
        cookies = {
            "session": self.session_cookie,
            **Config.DEFAULT_COOKIES,
        }
        
        if include_sid and self._sid_cookie:
            cookies["sid"] = self._sid_cookie
            
        return cookies
        
    def set_sid(self, sid: Optional[str]):
        """Установить SID cookie"""
        self._sid_cookie = sid
        
    def get_sid(self) -> Optional[str]:
        """Получить SID cookie"""
        return self._sid_cookie

    async def _request(
        self,
        method: str,
        url: str,
        json_data: Any = None,
        form_data: Any = None,
        referer: str = None,
        headers: Dict[str, str] = None,
        include_sid: bool = False,
        retry: bool = True,
        as_text: bool = False,
    ) -> Any:
        """
        Общая логика HTTP запроса: throttle, статус-коды, retry.

        Args:
            json_data: Тело запроса как JSON
            form_data: Тело запроса как multipart/form-data (aiohttp.FormData)
            retry: Повторять ли запрос при сетевых ошибках.
                   Для мутирующих POST (отправка сообщения, рефанд) должно
                   быть False — таймаут не значит, что сервер не принял запрос,
                   и повтор может задублировать действие.
            as_text: Вернуть тело как текст вместо JSON
        """
        if self._session is None:
            await self.start()

        retry_count = self.config.max_retries if retry else 1
        request_headers = self._get_headers(referer, headers)
        cookies = self._get_cookies(include_sid)

        last_error = None

        for attempt in range(retry_count):
            try:
                await throttle()
                async with self._session.request(
                    method,
                    url,
                    headers=request_headers,
                    cookies=cookies,
                    json=json_data,
                    data=form_data,
                ) as resp:
                    # Для ошибок читаем тело ответа (там бывает message от API)
                    error_message = ""
                    if resp.status >= 400:
                        try:
                            error_body = await resp.text()
                            try:
                                error_data = json.loads(error_body)
                                error_message = error_data.get("message") or error_data.get("error") or error_body
                            except (json.JSONDecodeError, AttributeError):
                                error_message = error_body
                        except Exception:
                            error_message = f"HTTP {resp.status}"

                    # Обработка статус кодов
                    if resp.status == 400:
                        raise StarAPIError(f"Bad Request (400): {error_message}")
                    elif resp.status == 401:
                        raise AuthenticationError("Неверный session cookie")
                    elif resp.status == 403:
                        raise ForbiddenError(f"Доступ запрещён (антибот): {url}")
                    elif resp.status == 404:
                        raise NotFoundError(f"Ресурс не найден: {url}")
                    elif resp.status == 429:
                        # Rate limit: ждём сколько сказал сервер и пробуем ещё раз
                        if retry and attempt < retry_count - 1:
                            try:
                                delay = int(resp.headers.get("Retry-After", 10))
                            except ValueError:
                                delay = 10
                            delay = min(max(delay, 1), 60)
                            logger.warning(f"⏳ 429 от Starvell, жду {delay}с перед повтором: {url}")
                            await asyncio.sleep(delay)
                            continue
                        raise RateLimitError("Превышен лимит запросов")
                    elif resp.status >= 500:
                        raise ServerError(f"Ошибка сервера: {resp.status}")

                    resp.raise_for_status()

                    if as_text:
                        return await resp.text()

                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" in content_type.lower():
                        return await resp.json()

                    text = await resp.text()
                    return {"status": resp.status, "text": text}

            except (ClientResponseError, aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e

                # Последняя попытка
                if attempt == retry_count - 1:
                    break

                # Ждем перед следующей попыткой
                await asyncio.sleep(self.config.RETRY_DELAY * (attempt + 1))

        # Если все попытки провалились
        if last_error:
            raise StarAPIError(f"Не удалось выполнить запрос после {retry_count} попыток: {last_error}")
        raise StarAPIError("Неизвестная ошибка при выполнении запроса")

    async def get_json(
        self,
        url: str,
        referer: str = None,
        headers: Dict[str, str] = None,
        include_sid: bool = False,
    ) -> Any:
        """GET запрос с получением JSON"""
        return await self._request(
            "GET", url,
            referer=referer,
            headers=headers,
            include_sid=include_sid,
        )

    async def post_json(
        self,
        url: str,
        data: Any,
        referer: str = None,
        headers: Dict[str, str] = None,
        include_sid: bool = False,
        retry: bool = False,
    ) -> Any:
        """
        POST запрос с отправкой и получением JSON.

        По умолчанию без retry: повтор мутирующего запроса после таймаута
        может задублировать действие (двойное сообщение, двойной рефанд).
        Для read-only POST (списки) передавайте retry=True.
        """
        headers = dict(headers or {})
        headers["content-type"] = "application/json"
        return await self._request(
            "POST", url,
            json_data=data,
            referer=referer,
            headers=headers,
            include_sid=include_sid,
            retry=retry,
        )

    async def patch_json(
        self,
        url: str,
        data: Any,
        referer: str = None,
        headers: Dict[str, str] = None,
        include_sid: bool = False,
        retry: bool = False,
    ) -> Any:
        headers = dict(headers or {})
        headers["content-type"] = "application/json"
        return await self._request(
            "PATCH", url,
            json_data=data,
            referer=referer,
            headers=headers,
            include_sid=include_sid,
            retry=retry,
        )

    async def post_form(
        self,
        url: str,
        form_data: Any,
        referer: str = None,
        headers: Dict[str, str] = None,
        include_sid: bool = False,
        retry: bool = False,
    ) -> Any:
        """
        POST запрос с телом multipart/form-data.

        content-type не выставляем вручную — aiohttp сам проставит boundary.
        По умолчанию без retry (мутирующий запрос).
        """
        return await self._request(
            "POST", url,
            form_data=form_data,
            referer=referer,
            headers=headers,
            include_sid=include_sid,
            retry=retry,
        )

    async def get_text(
        self,
        url: str,
        referer: str = None,
        headers: Dict[str, str] = None,
    ) -> str:
        """GET запрос с получением текста"""
        return await self._request(
            "GET", url,
            referer=referer,
            headers=headers,
            as_text=True,
        )

    async def probe_status(self, url: str, referer: str = None, timeout_seconds: float = 5) -> int:
        """Быстрая проверка доступности URL без retry (возвращает HTTP статус)"""
        if self._session is None:
            await self.start()

        timeout = ClientTimeout(total=timeout_seconds, connect=timeout_seconds)
        await throttle()
        async with self._session.request(
            "GET",
            url,
            headers=self._get_headers(referer),
            cookies=self._get_cookies(False),
            timeout=timeout,
        ) as resp:
            return resp.status

    async def head_headers(self, url: str, referer: str = None, timeout_seconds: float = 5) -> Dict[str, str]:
        """HEAD запрос — вернуть заголовки ответа (для детекта QRATOR)"""
        if self._session is None:
            await self.start()

        timeout = ClientTimeout(total=timeout_seconds, connect=timeout_seconds)
        await throttle()
        async with self._session.request(
            "HEAD",
            url,
            headers=self._get_headers(referer),
            cookies=self._get_cookies(False),
            timeout=timeout,
        ) as resp:
            return dict(resp.headers)

    async def ws_connect(
        self,
        url: str,
        referer: str = None,
        headers: Dict[str, str] = None,
        include_sid: bool = False,
    ) -> aiohttp.ClientWebSocketResponse:
        """Открыть WebSocket с теми же cookies и заголовками, что у HTTP запросов"""
        if self._session is None:
            await self.start()

        request_headers = self._get_headers(referer, headers)
        cookies = self._get_cookies(include_sid)
        # aiohttp не передаёт per-request cookies в ws_connect — собираем вручную
        request_headers.setdefault(
            "cookie",
            "; ".join(f"{k}={v}" for k, v in cookies.items() if v is not None),
        )
        return await self._session.ws_connect(
            url,
            headers=request_headers,
            autoping=False,
            heartbeat=None,
        )
