"""Ограничитель частоты запросов к Starvell"""

import asyncio
import time
from typing import Optional


class RequestLimiter:
    """
    Держит минимальный интервал между запросами к API.

    Starvell (особенно за QRATOR) банит за слишком частые запросы,
    поэтому все HTTP-вызовы проходят через wait() перед отправкой.
    """

    def __init__(self, max_per_minute: int = 40):
        max_per_minute = max(1, min(int(max_per_minute), 60))
        self._min_interval = 60.0 / max_per_minute
        self._lock = asyncio.Lock()
        self._next_allowed = 0.0

    async def wait(self):
        """Подождать, пока не наступит окно для следующего запроса"""
        async with self._lock:
            now = time.monotonic()
            delay = self._next_allowed - now

            if delay > 0:
                await asyncio.sleep(delay)
                now = time.monotonic()

            self._next_allowed = now + self._min_interval


_limiter: Optional[RequestLimiter] = None


def setup_limiter(max_per_minute: int) -> RequestLimiter:
    """Создать глобальный limiter с заданным лимитом"""
    global _limiter
    _limiter = RequestLimiter(max_per_minute)
    return _limiter


async def throttle():
    """Притормозить перед запросом (общий лимит на весь процесс)"""
    global _limiter
    if _limiter is None:
        _limiter = RequestLimiter()
    await _limiter.wait()
