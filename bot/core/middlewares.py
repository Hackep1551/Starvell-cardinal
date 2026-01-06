"""
Middleware для проверки доступа
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from aiogram.fsm.context import FSMContext
from bot.core.config import BotConfig


class AuthMiddleware(BaseMiddleware):
    """Middleware для проверки прав доступа"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем ID пользователя
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif hasattr(event, 'from_user'):
            user_id = event.from_user.id
        
        # Разрешаем команду /start и состояние ввода пароля для всех
        if isinstance(event, Message):
            # Получаем FSM контекст
            state: FSMContext = data.get('state')
            current_state = await state.get_state() if state else None
            
            # Разрешаем /start и состояние авторизации
            if event.text and (event.text.startswith('/start') or current_state == 'AuthState:waiting_for_password'):
                return await handler(event, data)
            
        # Проверяем доступ
        if user_id and user_id in BotConfig.ADMIN_IDS():
            data['is_admin'] = True
            return await handler(event, data)
        
        # Если нет доступа
        if isinstance(event, Message):
            await event.answer("❌ У вас нет доступа к этому боту. Используйте /start для авторизации.")
        
        return None
