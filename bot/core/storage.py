"""
Управление хранилищем данных (JSON файлы)
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class JSONStorage:
    """Базовый класс для работы с JSON хранилищем"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        
    async def _read(self) -> dict:
        """Прочитать данные из файла"""
        if not self.file_path.exists():
            return {}
            
        async with self._lock:
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
                
    async def _write(self, data: dict):
        """Записать данные в файл"""
        async with self._lock:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


class CacheStorage(JSONStorage):
    """Хранилище для кэша (последние сообщения, заказы)"""
    
    def __init__(self, storage_dir: str = "storage/cache"):
        super().__init__(f"{storage_dir}/cache.json")
        
    async def get_last_message(self, chat_id: str) -> Optional[str]:
        """Получить ID последнего сообщения в чате"""
        data = await self._read()
        messages = data.get("last_messages", {})
        return messages.get(chat_id, {}).get("message_id")
        
    async def set_last_message(self, chat_id: str, message_id: str):
        """Сохранить ID последнего сообщения"""
        data = await self._read()
        
        if "last_messages" not in data:
            data["last_messages"] = {}
            
        data["last_messages"][chat_id] = {
            "message_id": message_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._write(data)
        
    async def get_last_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о последнем заказе"""
        data = await self._read()
        orders = data.get("last_orders", {})
        return orders.get(order_id)
        
    async def set_last_order(self, order_id: str, status: str):
        """Сохранить статус заказа"""
        data = await self._read()
        
        if "last_orders" not in data:
            data["last_orders"] = {}
            
        data["last_orders"][order_id] = {
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._write(data)
        
    async def clear_old_cache(self, days: int = 7):
        """Очистить старый кэш"""
        from datetime import timedelta
        
        data = await self._read()
        cutoff = datetime.now() - timedelta(days=days)
        
        # Очищаем сообщения
        if "last_messages" in data:
            data["last_messages"] = {
                k: v for k, v in data["last_messages"].items()
                if datetime.fromisoformat(v["timestamp"]) > cutoff
            }
            
        # Очищаем заказы
        if "last_orders" in data:
            data["last_orders"] = {
                k: v for k, v in data["last_orders"].items()
                if datetime.fromisoformat(v["timestamp"]) > cutoff
            }
            
        await self._write(data)


class SettingsStorage(JSONStorage):
    """Хранилище для настроек пользователей"""
    
    def __init__(self, storage_dir: str = "storage/settings"):
        super().__init__(f"{storage_dir}/settings.json")
        
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Получить настройки пользователя"""
        data = await self._read()
        user_key = str(user_id)
        
        if user_key in data:
            return data[user_key]
            
        # Настройки по умолчанию
        return {
            "notify_messages": True,
            "notify_orders": True,
            "auto_bump_enabled": False,
            "created_at": datetime.now().isoformat(),
        }
        
    async def update_user_settings(self, user_id: int, **kwargs):
        """Обновить настройки пользователя"""
        data = await self._read()
        user_key = str(user_id)
        
        # Получаем текущие настройки
        settings = await self.get_user_settings(user_id)
        
        # Обновляем
        settings.update(kwargs)
        settings["updated_at"] = datetime.now().isoformat()
        
        # Сохраняем
        data[user_key] = settings
        await self._write(data)


class StatisticsStorage(JSONStorage):
    """Хранилище для статистики"""
    
    def __init__(self, storage_dir: str = "storage/stats"):
        super().__init__(f"{storage_dir}/statistics.json")
        
    async def add_sent_message(self, chat_id: str, content: str):
        """Добавить отправленное сообщение"""
        data = await self._read()
        
        if "sent_messages" not in data:
            data["sent_messages"] = []
            
        data["sent_messages"].append({
            "chat_id": chat_id,
            "content": content[:100],  # Храним только первые 100 символов
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем размер (храним последние 1000)
        if len(data["sent_messages"]) > 1000:
            data["sent_messages"] = data["sent_messages"][-1000:]
            
        await self._write(data)
        
    async def get_sent_messages_count(self, since: Optional[datetime] = None) -> int:
        """Получить количество отправленных сообщений"""
        data = await self._read()
        messages = data.get("sent_messages", [])
        
        if since:
            messages = [
                m for m in messages
                if datetime.fromisoformat(m["timestamp"]) >= since
            ]
            
        return len(messages)
        
    async def add_bump_history(self, game_id: int, categories: List[int], success: bool):
        """Добавить запись о bump'е"""
        data = await self._read()
        
        if "bump_history" not in data:
            data["bump_history"] = []
            
        data["bump_history"].append({
            "game_id": game_id,
            "categories": categories,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем размер
        if len(data["bump_history"]) > 500:
            data["bump_history"] = data["bump_history"][-500:]
            
        await self._write(data)
        
    async def get_bump_count(self, since: Optional[datetime] = None) -> int:
        """Получить количество успешных bump'ов"""
        data = await self._read()
        bumps = data.get("bump_history", [])
        
        # Фильтруем успешные
        bumps = [b for b in bumps if b.get("success")]
        
        if since:
            bumps = [
                b for b in bumps
                if datetime.fromisoformat(b["timestamp"]) >= since
            ]
            
        return len(bumps)
        
    async def get_last_bump_time(self) -> Optional[datetime]:
        """Получить время последнего успешного bump'а"""
        data = await self._read()
        bumps = data.get("bump_history", [])
        
        # Фильтруем успешные
        successful_bumps = [b for b in bumps if b.get("success")]
        
        if successful_bumps:
            last = successful_bumps[-1]
            return datetime.fromisoformat(last["timestamp"])
            
        return None
        
    async def get_daily_stats(self) -> Dict[str, int]:
        """Получить статистику за сегодня"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return {
            "messages_sent": await self.get_sent_messages_count(since=today),
            "bumps_done": await self.get_bump_count(since=today),
        }


class Database:
    """
    Главный класс для работы с хранилищем
    Совместимость с интерфейсом старой БД
    """
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = storage_dir
        self.cache = CacheStorage(f"{storage_dir}/cache")
        self.settings = SettingsStorage(f"{storage_dir}/settings")
        self.stats = StatisticsStorage(f"{storage_dir}/stats")
        
    async def connect(self):
        """Инициализация (для совместимости)"""
        # Создаем директории
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        
    async def close(self):
        """Закрытие (для совместимости)"""
        pass
        
    # === Делегируем методы ===
    
    async def get_last_message(self, chat_id: str) -> Optional[str]:
        return await self.cache.get_last_message(chat_id)
        
    async def set_last_message(self, chat_id: str, message_id: str):
        await self.cache.set_last_message(chat_id, message_id)
        
    async def get_last_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return await self.cache.get_last_order(order_id)
        
    async def set_last_order(self, order_id: str, status: str):
        await self.cache.set_last_order(order_id, status)
        
    async def add_sent_message(self, chat_id: str, content: str):
        await self.stats.add_sent_message(chat_id, content)
        
    async def get_sent_messages_count(self, since: Optional[datetime] = None) -> int:
        return await self.stats.get_sent_messages_count(since)
        
    async def add_bump_history(self, game_id: int, categories: List[int], success: bool):
        await self.stats.add_bump_history(game_id, categories, success)
        
    async def get_bump_count(self, since: Optional[datetime] = None) -> int:
        return await self.stats.get_bump_count(since)
        
    async def get_last_bump_time(self) -> Optional[datetime]:
        return await self.stats.get_last_bump_time()
        
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        return await self.settings.get_user_settings(user_id)
        
    async def update_user_settings(self, user_id: int, **kwargs):
        await self.settings.update_user_settings(user_id, **kwargs)
        
    async def get_daily_stats(self) -> Dict[str, int]:
        return await self.stats.get_daily_stats()
        
    async def cleanup(self, days: int = 7):
        """Очистить старые данные"""
        await self.cache.clear_old_cache(days)
