"""Конфигурация клиента"""

from typing import Optional


class Config:
    """Конфигурация StarAPI клиента"""
    
    BASE_URL = "https://starvell.com"
    API_URL = f"{BASE_URL}/api"
    
    # Таймауты
    DEFAULT_TIMEOUT = 20
    
    # Retry настройки
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # секунды
    
    # Кэш для build_id
    BUILD_ID_CACHE_TTL = 1800  # 30 минут
    
    # User-Agent по умолчанию
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    
    # Cookies по умолчанию
    DEFAULT_COOKIES = {
        "starvell.theme": "dark",
        "starvell.time_zone": "Europe/Moscow",
        "starvell.my_games": "1,10,11",
    }
    
    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.MAX_RETRIES
