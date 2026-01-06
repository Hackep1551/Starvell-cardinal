"""
Чёрный список пользователей
"""

import json
from pathlib import Path
from typing import List


class Blacklist:
    """Управление чёрным списком пользователей"""
    
    def __init__(self, storage_path: str = "storage/cache/blacklist.json"):
        self.storage_path = Path(storage_path)
        self.users: List[str] = []
        self.load()
    
    def load(self):
        """Загрузить чёрный список из файла"""
        if not self.storage_path.exists():
            self.users = []
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.users = data if isinstance(data, list) else []
        except (json.JSONDecodeError, Exception):
            self.users = []
    
    def save(self):
        """Сохранить чёрный список в файл"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def add(self, username: str) -> bool:
        """
        Добавить пользователя в ЧС
        
        Returns:
            True если пользователь добавлен, False если уже был в списке
        """
        username = username.strip()
        
        if username in self.users:
            return False
        
        self.users.append(username)
        self.save()
        return True
    
    def remove(self, username: str) -> bool:
        """
        Удалить пользователя из ЧС
        
        Returns:
            True если пользователь удалён, False если не был в списке
        """
        username = username.strip()
        
        if username not in self.users:
            return False
        
        self.users.remove(username)
        self.save()
        return True
    
    def is_blacklisted(self, username: str) -> bool:
        """Проверить, находится ли пользователь в ЧС"""
        return username.strip() in self.users
    
    def get_all(self) -> List[str]:
        """Получить весь список"""
        return self.users.copy()
    
    def clear(self):
        """Очистить весь чёрный список"""
        self.users = []
        self.save()
    
    def __len__(self) -> int:
        """Количество пользователей в ЧС"""
        return len(self.users)
    
    def __contains__(self, username: str) -> bool:
        """Проверка через 'in'"""
        return self.is_blacklisted(username)
    
    def __iter__(self):
        """Итерация по списку"""
        return iter(self.users)


# Глобальный экземпляр
_blacklist = Blacklist()


def get_blacklist() -> Blacklist:
    """Получить глобальный экземпляр чёрного списка"""
    return _blacklist
