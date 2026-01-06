"""
Менеджер заготовок ответов
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import uuid


logger = logging.getLogger("TMPL")


class TemplateManager:
    """Управление заготовками ответов"""
    
    def __init__(self, templates_path: str = "configs/templates.json"):
        self.templates_path = Path(templates_path)
        self._templates: List[Dict] = []
        
        # Создаём директорию configs, если не существует
        self.templates_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._load()
    
    def _load(self):
        """Загрузить заготовки из файла"""
        if self.templates_path.exists():
            try:
                with open(self.templates_path, 'r', encoding='utf-8') as f:
                    self._templates = json.load(f)
                logger.info(f"📝 Загружено {len(self._templates)} заготовок ответов")
            except Exception as e:
                logger.error(f"Ошибка загрузки заготовок: {e}")
                self._templates = []
                self._save()
        else:
            # Создаём пустой файл с примером
            self._templates = []
            self._save()
            logger.info("📝 Создан новый файл заготовок")
    
    def _save(self):
        """Сохранить заготовки в файл"""
        try:
            with open(self.templates_path, 'w', encoding='utf-8') as f:
                json.dump(self._templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения заготовок: {e}")
    
    def get_all(self) -> List[Dict]:
        """
        Получить все заготовки
        
        Returns:
            list: Список заготовок [{"id": "...", "name": "...", "text": "..."}, ...]
        """
        return self._templates.copy()
    
    def get_by_id(self, template_id: str) -> Optional[Dict]:
        """
        Получить заготовку по ID
        
        Args:
            template_id: ID заготовки
            
        Returns:
            dict: Заготовка или None
        """
        for template in self._templates:
            if template.get("id") == template_id:
                return template.copy()
        return None
    
    def add(self, name: str, text: str) -> str:
        """
        Добавить новую заготовку
        
        Args:
            name: Название заготовки
            text: Текст заготовки
            
        Returns:
            str: ID новой заготовки
        """
        template_id = str(uuid.uuid4())
        
        template = {
            "id": template_id,
            "name": name,
            "text": text
        }
        
        self._templates.append(template)
        self._save()
        
        logger.info(f"➕ Добавлена заготовка '{name}' (ID: {template_id})")
        return template_id
    
    def update(self, template_id: str, name: Optional[str] = None, text: Optional[str] = None) -> bool:
        """
        Обновить заготовку
        
        Args:
            template_id: ID заготовки
            name: Новое название (опционально)
            text: Новый текст (опционально)
            
        Returns:
            bool: True если успешно, False если заготовка не найдена
        """
        for template in self._templates:
            if template.get("id") == template_id:
                if name is not None:
                    template["name"] = name
                if text is not None:
                    template["text"] = text
                
                self._save()
                logger.info(f"✏️ Обновлена заготовка '{template['name']}' (ID: {template_id})")
                return True
        
        return False
    
    def delete(self, template_id: str) -> bool:
        """
        Удалить заготовку
        
        Args:
            template_id: ID заготовки
            
        Returns:
            bool: True если успешно, False если заготовка не найдена
        """
        for i, template in enumerate(self._templates):
            if template.get("id") == template_id:
                name = template.get("name")
                self._templates.pop(i)
                self._save()
                
                logger.info(f"🗑️ Удалена заготовка '{name}' (ID: {template_id})")
                return True
        
        return False
    
    def count(self) -> int:
        """Получить количество заготовок"""
        return len(self._templates)


# Глобальный экземпляр менеджера
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Получить глобальный экземпляр менеджера заготовок"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
