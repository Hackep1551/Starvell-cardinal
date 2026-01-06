"""Утилиты для работы с API"""

import re
import json
import time
import asyncio
from typing import Optional


class BuildIdCache:
    """Кэш для build_id"""
    
    def __init__(self, ttl: int = 1800):
        self.ttl = ttl
        self._build_id: Optional[str] = None
        self._cached_at: float = 0.0
        self._lock = asyncio.Lock()
        
    async def get(self, fetch_func) -> str:
        """Получить build_id из кэша или обновить"""
        async with self._lock:
            now = time.time()
            
            # Если кэш актуален, возвращаем
            if self._build_id and (now - self._cached_at) < self.ttl:
                return self._build_id
                
            # Иначе обновляем
            self._build_id = await fetch_func()
            self._cached_at = now
            return self._build_id
            
    def reset(self):
        """Сбросить кэш"""
        self._build_id = None
        self._cached_at = 0.0


def extract_next_data(html: str) -> dict:
    """Извлечь данные из __NEXT_DATA__ скрипта"""
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL
    )
    
    if not match:
        raise ValueError("Не найден __NEXT_DATA__ скрипт в HTML")
        
    try:
        data = json.loads(match.group(1))
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга __NEXT_DATA__: {e}")


def extract_build_id(html: str) -> str:
    """Извлечь build_id из HTML"""
    data = extract_next_data(html)
    build_id = data.get("buildId")
    
    if not build_id:
        raise ValueError("buildId не найден в __NEXT_DATA__")
        
    return str(build_id)


def extract_sid_from_cookies(session) -> Optional[str]:
    """Извлечь SID из cookies сессии"""
    try:
        jar_cookies = session.cookie_jar.filter_cookies("https://starvell.com")
        c = jar_cookies.get("sid")
        return c.value if c else None
    except Exception:
        return None
