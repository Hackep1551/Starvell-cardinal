"""
Система плагинов для Starvell Bot 
"""

import os
import sys
import importlib.util
import logging
from typing import Dict, Callable, Any, Optional
from uuid import UUID
from pathlib import Path
from types import ModuleType


logger = logging.getLogger("Plugins")


class PluginData:
    """Данные плагина"""
    
    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        uuid: str,
        path: str,
        module: ModuleType,
        has_settings: bool,
        delete_handler: Optional[Callable],
        enabled: bool
    ):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.uuid = uuid
        self.path = path
        self.module = module
        self.has_settings = has_settings
        self.delete_handler = delete_handler
        self.enabled = enabled
        self.commands: Dict[str, str] = {}  # {command: description}


class PluginManager:
    """Менеджер плагинов"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginData] = {}
        self.plugins_dir = Path("plugins")
        self.disabled_cache = Path("storage/cache/disabled_plugins.txt")
        self.disabled_plugins: list[str] = []
        
        # Хэндлеры событий
        self.init_handlers: list[Callable] = []
        self.start_handlers: list[Callable] = []
        self.stop_handlers: list[Callable] = []
        self.new_order_handlers: list[Callable] = []
        self.new_message_handlers: list[Callable] = []
        self.settings_handlers: Dict[str, list[Callable]] = {}  # {uuid: [handler]}
        
    def load_disabled_plugins(self):
        """Загрузить список отключённых плагинов"""
        if not self.disabled_cache.exists():
            return
        
        try:
            with open(self.disabled_cache, 'r', encoding='utf-8') as f:
                self.disabled_plugins = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Ошибка загрузки списка отключённых плагинов: {e}")
    
    def save_disabled_plugins(self):
        """Сохранить список отключённых плагинов"""
        self.disabled_cache.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.disabled_cache, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.disabled_plugins))
        except Exception as e:
            logger.error(f"Ошибка сохранения списка отключённых плагинов: {e}")
    
    @staticmethod
    def is_uuid_valid(uuid_str: str) -> bool:
        """Проверить валидность UUID"""
        try:
            uuid_obj = UUID(uuid_str, version=4)
            return str(uuid_obj) == uuid_str
        except ValueError:
            return False
    
    @staticmethod
    def is_plugin_enabled(file_path: Path) -> bool:
        """Проверить, не отключён ли плагин через # noplug"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#') and 'noplug' in first_line:
                    return False
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_path}: {e}")
            return False
        return True
    
    def load_plugin_module(self, file_path: Path) -> tuple[ModuleType, dict]:
        """
        Загрузить модуль плагина и извлечь данные
        
        Returns:
            (module, data_dict) где data_dict содержит NAME, VERSION, etc.
        """
        # Создаём спецификацию модуля
        module_name = f"plugins.{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Не удалось создать спецификацию для {file_path}")
        
        # Создаём модуль
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Извлекаем обязательные поля
        required_fields = {
            'NAME': str,
            'VERSION': str,
            'DESCRIPTION': str,
            'AUTHOR': str,
            'UUID': str
        }
        
        data = {}
        for field, field_type in required_fields.items():
            if not hasattr(module, field):
                raise AttributeError(f"Плагин {file_path.name} не содержит поле {field}")
            data[field] = getattr(module, field)
        
        # Опциональные поля
        data['SETTINGS_PAGE'] = getattr(module, 'SETTINGS_PAGE', False)
        data['BIND_TO_DELETE'] = getattr(module, 'BIND_TO_DELETE', None)
        
        return module, data
    
    def load_plugins(self):
        """Загрузить все плагины из папки plugins"""
        if not self.plugins_dir.exists():
            logger.warning("📁 Папка plugins не найдена")
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Загружаем список отключённых плагинов
        self.load_disabled_plugins()
        
        # Находим все .py файлы
        plugin_files = list(self.plugins_dir.glob("*.py"))
        
        if not plugin_files:
            logger.info("🧩 Плагины не обнаружены")
            return
        
        # Добавляем папку plugins в sys.path
        sys.path.insert(0, str(self.plugins_dir))
        
        loaded_count = 0
        for file_path in plugin_files:
            try:
                # Проверяем # noplug
                if not self.is_plugin_enabled(file_path):
                    logger.debug(f"Плагин {file_path.name} отключён через # noplug")
                    continue
                
                # Загружаем модуль
                module, data = self.load_plugin_module(file_path)
                
                # Проверяем UUID
                uuid = data['UUID']
                if not self.is_uuid_valid(uuid):
                    logger.error(f"❌ Плагин {file_path.name} имеет невалидный UUID: {uuid}")
                    continue
                
                # Проверяем дублирование UUID
                if uuid in self.plugins:
                    logger.error(f"❌ UUID {uuid} ({data['NAME']}) уже зарегистрирован")
                    continue
                
                # Создаём объект плагина
                enabled = uuid not in self.disabled_plugins
                plugin = PluginData(
                    name=data['NAME'],
                    version=data['VERSION'],
                    description=data['DESCRIPTION'],
                    author=data['AUTHOR'],
                    uuid=uuid,
                    path=str(file_path),
                    module=module,
                    has_settings=data['SETTINGS_PAGE'],
                    delete_handler=data['BIND_TO_DELETE'],
                    enabled=enabled
                )
                
                self.plugins[uuid] = plugin
                loaded_count += 1
                
                status = "✅" if enabled else "⏸️"
                logger.info(f"{status} Плагин {data['NAME']} v{data['VERSION']} загружен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки плагина {file_path.name}: {e}")
                logger.debug("TRACEBACK", exc_info=True)
        
        logger.info(f"📦 Загружено плагинов: {loaded_count}/{len(plugin_files)}")
    
    def register_handlers(self):
        """Зарегистрировать хэндлеры из всех плагинов"""
        for uuid, plugin in self.plugins.items():
            if not plugin.enabled:
                continue
            
            module = plugin.module
            
            # Регистрируем хэндлеры
            if hasattr(module, 'BIND_TO_INIT'):
                for handler in module.BIND_TO_INIT:
                    handler.plugin_uuid = uuid
                    self.init_handlers.append(handler)
            
            if hasattr(module, 'BIND_TO_START'):
                for handler in module.BIND_TO_START:
                    handler.plugin_uuid = uuid
                    self.start_handlers.append(handler)
            
            if hasattr(module, 'BIND_TO_STOP'):
                for handler in module.BIND_TO_STOP:
                    handler.plugin_uuid = uuid
                    self.stop_handlers.append(handler)
            
            if hasattr(module, 'BIND_TO_NEW_ORDER'):
                for handler in module.BIND_TO_NEW_ORDER:
                    handler.plugin_uuid = uuid
                    self.new_order_handlers.append(handler)
            
            if hasattr(module, 'BIND_TO_NEW_MESSAGE'):
                for handler in module.BIND_TO_NEW_MESSAGE:
                    handler.plugin_uuid = uuid
                    self.new_message_handlers.append(handler)
            
            if hasattr(module, 'BIND_TO_SETTINGS_PAGE'):
                self.settings_handlers[uuid] = module.BIND_TO_SETTINGS_PAGE
            
            logger.debug(f"Хэндлеры плагина {plugin.name} зарегистрированы")
    
    def run_handlers(self, handlers: list[Callable], *args):
        """Выполнить список хэндлеров"""
        for handler in handlers:
            try:
                # Проверяем, включён ли плагин
                plugin_uuid = getattr(handler, 'plugin_uuid', None)
                if plugin_uuid and plugin_uuid in self.plugins:
                    if not self.plugins[plugin_uuid].enabled:
                        continue
                
                handler(*args)
            except Exception as e:
                logger.error(f"Ошибка выполнения хэндлера {handler.__name__}: {e}")
                logger.debug("TRACEBACK", exc_info=True)
    
    def toggle_plugin(self, uuid: str):
        """Включить/выключить плагин"""
        if uuid not in self.plugins:
            return False
        
        plugin = self.plugins[uuid]
        plugin.enabled = not plugin.enabled
        
        if plugin.enabled and uuid in self.disabled_plugins:
            self.disabled_plugins.remove(uuid)
        elif not plugin.enabled and uuid not in self.disabled_plugins:
            self.disabled_plugins.append(uuid)
        
        self.save_disabled_plugins()
        return True
    
    def delete_plugin(self, uuid: str) -> bool:
        """Удалить плагин"""
        if uuid not in self.plugins:
            return False
        
        plugin = self.plugins[uuid]
        
        # Вызываем хэндлер удаления, если есть
        if plugin.delete_handler:
            try:
                plugin.delete_handler()
            except Exception as e:
                logger.error(f"Ошибка выполнения хэндлера удаления плагина {plugin.name}: {e}")
        
        # Удаляем файл
        try:
            os.remove(plugin.path)
        except Exception as e:
            logger.error(f"Ошибка удаления файла плагина {plugin.path}: {e}")
            return False
        
        # Удаляем из словаря
        del self.plugins[uuid]
        
        # Удаляем из отключённых, если был там
        if uuid in self.disabled_plugins:
            self.disabled_plugins.remove(uuid)
            self.save_disabled_plugins()
        
        logger.info(f"🗑️ Плагин {plugin.name} удалён")
        return True
