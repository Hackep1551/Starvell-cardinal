"""
Модуль авто-поднятия лотов 
"""

import asyncio
import logging
import time
from typing import Dict, Optional
from datetime import datetime

from bot.core.config import BotConfig


logger = logging.getLogger("RAIS")


class AutoRaiseService:
    """Сервис автоматического поднятия лотов)"""
    
    def __init__(self, starvell_service, notification_manager=None):
        self.starvell = starvell_service
        self.notifier = notification_manager
        self.raise_time: Dict[int, int] = {}  # game_id -> timestamp следующего поднятия
        self.raised_time: Dict[int, int] = {}  # game_id -> timestamp последнего поднятия
        self._task: asyncio.Task = None
        
    async def start(self):
        """Запустить сервис"""
        if not await self._has_lots():
            logger.info("🔵 Цикл авто-поднятия не запущен: лоты не обнаружены на аккаунте")
            return
            
        self._task = asyncio.create_task(self._raise_loop())
        logger.info("🔵 Цикл авто-поднятия запущен (это не значит что auto-raise включен)")
    
    async def stop(self):
        """Остановить сервис"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Сервис авто-поднятия остановлен")
    
    async def _has_lots(self) -> bool:
        """Проверить наличие лотов"""
        try:
            user_info = await self.starvell.get_user_info()
            user_id = user_info.get("user", {}).get("id")
            
            if not user_id:
                return False
                
            offers = await self.starvell.api.get_user_offers(user_id)
            return offers and len(offers) > 0
        except Exception as e:
            logger.debug(f"Ошибка проверки лотов: {e}")
            return False
    
    async def _raise_loop(self):
        """Бесконечный цикл поднятия лотов"""
        while True:
            try:
                # Проверяем, включено ли автоподнятие
                if not BotConfig.AUTO_BUMP_ENABLED():
                    await asyncio.sleep(10)
                    continue
                
                # Поднимаем лоты и получаем время следующего вызова
                next_time = await self._raise_lots()
                
                # Рассчитываем задержку
                delay = next_time - int(time.time())
                
                if delay <= 0:
                    continue
                    
                await asyncio.sleep(delay)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле поднятия: {e}", exc_info=True)
                await asyncio.sleep(10)
    
    async def _raise_lots(self) -> int:
        """
        Поднять лоты
        
        Returns:
            Timestamp следующего вызова
        """
        next_call = float("inf")
        current_time = int(time.time())
        
        # Получаем настройки из конфига
        game_id = BotConfig.AUTO_BUMP_GAME_ID()
        categories = BotConfig.AUTO_BUMP_CATEGORIES()
        interval = BotConfig.AUTO_BUMP_INTERVAL()
        
        # Проверяем, не рано ли поднимать
        saved_time = self.raise_time.get(game_id)
        
        if saved_time and saved_time > current_time:
            # Ещё не время - обновляем next_call и выходим
            next_call = saved_time if saved_time < next_call else next_call
            return int(next_call) if next_call < float("inf") else 10
        
        # Пытаемся поднять лоты
        raise_ok = False
        error_text = ""
        time_delta = ""
        
        try:
            await asyncio.sleep(1)
            
            # Вызываем API поднятия через StarvellService
            result = await self.starvell.bump_offers(game_id, categories)
            
            # Проверяем успешность
            response = result.get("response", {})
            
            if response.get("success") or not response.get("error"):
                logger.info(f"⤴️ Все лоты игры ID={game_id} подняты!")
                raise_ok = True
                
                # Обновляем временные метки
                last_time = self.raised_time.get(game_id)
                new_time = int(time.time())
                self.raised_time[game_id] = new_time
                
                # Форматируем время с последнего поднятия
                if last_time:
                    delta = new_time - last_time
                    time_delta = f" Последнее поднятие: {self._time_to_str(delta)} назад."
                
                # Рассчитываем следующее поднятие
                next_time = new_time + interval
                self.raise_time[game_id] = next_time
                next_call = next_time if next_time < next_call else next_call
                
                # Отправляем уведомление
                if self.notifier:
                    try:
                        await self.notifier.notify_lots_raised(game_id, time_delta)
                    except Exception as e:
                        logger.debug(f"Ошибка отправки уведомления: {e}")
                
        except Exception as e:
            error_msg = str(e)
            
            # Проверяем, содержит ли ошибка информацию о времени ожидания
            if any(keyword in error_msg.lower() for keyword in ["подождите", "wait", "зачекайте"]):
                # Парсим время ожидания
                wait_time = self._parse_wait_time(error_msg)
                
                if wait_time:
                    logger.warning(
                        f"⏳ Не удалось поднять лоты игры ID={game_id}. "
                        f"Starvell говорит: \"{error_msg}\". "
                        f"Следующая попытка через {self._time_to_str(wait_time)}."
                    )
                    next_time = current_time + wait_time
                else:
                    logger.error(f"❌ Непредвиденная ошибка при поднятии лотов игры ID={game_id}. Пауза на 10 секунд...")
                    logger.debug("TRACEBACK", exc_info=True)
                    await asyncio.sleep(10)
                    next_time = current_time + 1
                    
                self.raise_time[game_id] = next_time
                next_call = next_time if next_time < next_call else next_call
                
            elif "429" in error_msg or "403" in error_msg or "503" in error_msg:
                # Ошибка сервера - ждём 1 минуту
                logger.warning(f"⚠️ Ошибка сервера при поднятии лотов игры ID={game_id}. Пауза на 1 минуту...")
                await asyncio.sleep(60)
                next_time = current_time + 60
                next_call = next_time if next_time < next_call else next_call
                
            else:
                # Другая ошибка
                logger.error(f"❌ Ошибка при поднятии лотов игры ID={game_id}: {e}")
                logger.debug("TRACEBACK", exc_info=True)
                await asyncio.sleep(10)
                next_time = current_time + 1
                next_call = next_time if next_time < next_call else next_call
        
        return int(next_call) if next_call < float("inf") else 10
    
    def _parse_wait_time(self, message: str) -> int:
        """
        Извлечь время ожидания из сообщения об ошибке
        
        Args:
            message: Сообщение об ошибке от API
            
        Returns:
            Время ожидания в секундах, или 0 если не удалось распарсить
        """
        import re
        
        message_lower = message.lower()
        
        # Ищем часы (hours)
        hours_patterns = [
            r'(\d+)\s*час',  # "2 часа"
            r'(\d+)\s*hour',  # "2 hours"
            r'(\d+)\s*hr',    # "2 hr"
            r'(\d+)\s*h',     # "2h"
        ]
        
        for pattern in hours_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return int(match.group(1)) * 3600
        
        # Ищем минуты (minutes)
        minutes_patterns = [
            r'(\d+)\s*мин',   # "30 минут"
            r'(\d+)\s*min',   # "30 minutes"
            r'(\d+)\s*м',     # "30 м"
            r'(\d+)\s*m(?!s)', # "30m" (но не "30ms")
        ]
        
        for pattern in minutes_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return int(match.group(1)) * 60
        
        # Ищем секунды (seconds)
        seconds_patterns = [
            r'(\d+)\s*сек',   # "45 секунд"
            r'(\d+)\s*sec',   # "45 seconds"
            r'(\d+)\s*с(?!м)', # "45 с" (но не "см")
            r'(\d+)\s*s(?!m)', # "45s" (но не "sm")
        ]
        
        for pattern in seconds_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return int(match.group(1))
        
        return 0
    
    @staticmethod
    def _time_to_str(seconds: int) -> str:
        """
        Преобразовать секунды в читабельный формат
        
        Args:
            seconds: Количество секунд
            
        Returns:
            Форматированная строка вида "2ч 30мин" или "45сек"
        """
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}ч {minutes}мин"
            return f"{hours}ч"
        elif seconds >= 60:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes}мин {secs}сек"
            return f"{minutes}мин"
        else:
            return f"{seconds}сек"
