"""Исключения для StarAPI"""


class StarAPIError(Exception):
    """Базовое исключение для всех ошибок API"""
    pass


class AuthenticationError(StarAPIError):
    """Ошибка аутентификации (неверный session cookie)"""
    pass


class RateLimitError(StarAPIError):
    """Превышен лимит запросов"""
    pass


class NotFoundError(StarAPIError):
    """Ресурс не найден (404)"""
    pass


class ServerError(StarAPIError):
    """Ошибка сервера (5xx)"""
    pass


class ValidationError(StarAPIError):
    """Ошибка валидации данных"""
    pass
