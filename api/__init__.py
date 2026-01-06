"""
StarAPI - Unofficial Starvell.com API Client
Простой и удобный асинхронный клиент для работы с Starvell.com
"""

from .client import StarAPI
from .exceptions import (
    StarAPIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ServerError,
)

__version__ = "1.0.0"
__all__ = [
    "StarAPI",
    "StarAPIError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ServerError",
]
