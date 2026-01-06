"""
Конфигурация бота
"""

import configparser
import ast
from pathlib import Path
from typing import List, Dict, Any, Union


class ConfigManager:
    """Управление конфигурацией в CFG формате"""
    
    def __init__(self, config_path: str = "configs/_main.cfg"):
        self.config_path = Path(config_path)
        self._config = configparser.ConfigParser()
        
        # Создаём директорию configs, если не существует
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_or_create()
        
    def _load_or_create(self):
        """Загрузить или создать конфигурацию"""
        if self.config_path.exists():
            try:
                # Пробуем UTF-8
                self._config.read(self.config_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    # Если не получилось, пробуем Windows-1251
                    self._config.read(self.config_path, encoding='cp1251')
                    # Пересохраняем в UTF-8
                    self.save()
                except Exception:
                    self._create_default()
            except Exception:
                self._create_default()
        else:
            self._create_default()
            
    def _create_default(self):
        """Создать конфигурацию по умолчанию"""
        self._config['Starvell'] = {
            'session_cookie': '',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'autoRaise': '0',
            'autoDelivery': '0',
            'autoRestore': '0',
            'locale': 'ru'
        }
        
        self._config['Telegram'] = {
            'enabled': '1',
            'token': '',
            'secretKeyHash': '',
            'adminIds': '[]'
        }
        
        self._config['Notifications'] = {
            'checkInterval': '30',
            'newMessages': '1',
            'newOrders': '1',
            'lotRestore': '1',
            'botStart': '1',
            'lotDeactivate': '1',
            'lotBump': '1'
        }
        
        self._config['Monitor'] = {
            'chatPollInterval': '5',
            'ordersPollInterval': '10',
            'remoteInfoInterval': '120'
        }
        
        self._config['AutoRaise'] = {
            'interval': '3600',
            'gameId': '1',
            'categories': '[10, 11, 12]'
        }
        
        self._config['Storage'] = {
            'dir': 'storage'
        }
        
        self._config['Proxy'] = {
            'enabled': '0',
            'ip': '',
            'port': '',
            'login': '',
            'password': '',
            'check': '0'
        }
        
        self._config['AutoUpdate'] = {
            'enabled': '1'
        }
        
        self._config['KeepAlive'] = {
            'enabled': '1'
        }
        
        self._config['Other'] = {
            'debug': '0',
            'watermark': '🤖'
        }
        
        self.save()
        
    def save(self):
        """Сохранить конфигурацию"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self._config.write(f)
            
    def _parse_value(self, value: str) -> Union[str, int, bool, list]:
        """Парсинг значения из строки"""
        # Пытаемся преобразовать в bool
        if value.lower() in ('1', 'true', 'yes', 'on'):
            return True
        if value.lower() in ('0', 'false', 'no', 'off'):
            return False
            
        # Пытаемся преобразовать в int
        try:
            return int(value)
        except ValueError:
            pass
            
        # Пытаемся преобразовать в list
        if value.startswith('[') and value.endswith(']'):
            try:
                return ast.literal_eval(value)
            except:
                pass
                
        # Возвращаем как строку
        return value
            
    def get(self, section: str, key: str, default=None):
        """Получить значение (например: 'Telegram', 'token')"""
        try:
            value = self._config.get(section, key)
            return self._parse_value(value)
        except:
            return default
        
    def set(self, section: str, key: str, value):
        """Установить значение"""
        if not self._config.has_section(section):
            self._config.add_section(section)
            
        # Преобразуем значение в строку
        if isinstance(value, bool):
            str_value = '1' if value else '0'
        elif isinstance(value, list):
            str_value = str(value)
        else:
            str_value = str(value)
            
        self._config.set(section, key, str_value)
        self.save()
        
    def get_all(self) -> Dict[str, Any]:
        """Получить всю конфигурацию"""
        result = {}
        for section in self._config.sections():
            result[section] = {}
            for key, value in self._config.items(section):
                result[section][key] = self._parse_value(value)
        return result


# Глобальный экземпляр конфигурации
_config_manager = ConfigManager()


class BotConfig:
    """Конфигурация бота"""
    
    @classmethod
    def reload(cls):
        """Перезагрузить конфигурацию"""
        global _config_manager
        _config_manager._load_or_create()
    
    # === Telegram ===
    @staticmethod
    def BOT_TOKEN() -> str:
        return _config_manager.get('Telegram', 'token', '')
    
    @staticmethod
    def PASSWORD_HASH() -> str:
        return _config_manager.get('Telegram', 'secretKeyHash', '')
    
    @staticmethod
    def ADMIN_IDS() -> list:
        return _config_manager.get('Telegram', 'adminIds', [])
    
    @staticmethod
    def set_admin_ids(admin_ids: list):
        """Установить список админов"""
        _config_manager.set('Telegram', 'adminIds', admin_ids)
    
    # === Starvell ===
    @staticmethod
    def STARVELL_SESSION() -> str:
        return _config_manager.get('Starvell', 'session_cookie', '')
    
    @staticmethod
    def USER_AGENT() -> str:
        default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        return _config_manager.get('Starvell', 'user_agent', default_ua)
    
    # === Прокси ===
    @staticmethod
    def PROXY_ENABLED() -> bool:
        return _config_manager.get('Proxy', 'enabled', False)
    
    @staticmethod
    def PROXY_IP() -> str:
        return _config_manager.get('Proxy', 'ip', '')
    
    @staticmethod
    def PROXY_PORT() -> str:
        return _config_manager.get('Proxy', 'port', '')
    
    @staticmethod
    def PROXY_LOGIN() -> str:
        return _config_manager.get('Proxy', 'login', '')
    
    @staticmethod
    def PROXY_PASSWORD() -> str:
        return _config_manager.get('Proxy', 'password', '')
    
    @staticmethod
    def PROXY_CHECK() -> bool:
        """Проверять ли прокси перед использованием"""
        return _config_manager.get('Proxy', 'check', False)
    
    @staticmethod
    def PROXY() -> str:
        """
        Получить прокси строку (если включен)
        Формат: [login:password@]ip:port
        """
        if not BotConfig.PROXY_ENABLED():
            return ''
        
        ip = BotConfig.PROXY_IP()
        port = BotConfig.PROXY_PORT()
        login = BotConfig.PROXY_LOGIN()
        password = BotConfig.PROXY_PASSWORD()
        
        if not ip or not port:
            return ''
        
        # Формируем строку прокси
        if login and password:
            return f"{login}:{password}@{ip}:{port}"
        else:
            return f"{ip}:{port}"
    
    @staticmethod
    def set_proxy(ip: str, port: str, login: str = '', password: str = '', enabled: bool = True, check: bool = False):
        """Установить прокси"""
        _config_manager.set('Proxy', 'ip', ip)
        _config_manager.set('Proxy', 'port', port)
        _config_manager.set('Proxy', 'login', login)
        _config_manager.set('Proxy', 'password', password)
        _config_manager.set('Proxy', 'enabled', enabled)
        _config_manager.set('Proxy', 'check', check)
    
    # === Хранилище ===
    @staticmethod
    def STORAGE_DIR() -> str:
        return _config_manager.get('Storage', 'dir', 'storage')
    
    # === Уведомления ===
    @staticmethod
    def CHECK_INTERVAL() -> int:
        return _config_manager.get('Notifications', 'checkInterval', 30)
    
    @staticmethod
    def NOTIFY_NEW_MESSAGES() -> bool:
        return _config_manager.get('Notifications', 'newMessages', True)
    
    @staticmethod
    def NOTIFY_NEW_ORDERS() -> bool:
        return _config_manager.get('Notifications', 'newOrders', True)
    
    @staticmethod
    def NOTIFY_LOT_RESTORE() -> bool:
        return _config_manager.get('Notifications', 'lotRestore', True)
    
    @staticmethod
    def NOTIFY_BOT_START() -> bool:
        return _config_manager.get('Notifications', 'botStart', True)
    
    @staticmethod
    def NOTIFY_LOT_DEACTIVATE() -> bool:
        return _config_manager.get('Notifications', 'lotDeactivate', True)
    
    @staticmethod
    def NOTIFY_LOT_BUMP() -> bool:
        return _config_manager.get('Notifications', 'lotBump', True)
    
    # === Авто-bump ===
    @staticmethod
    def AUTO_BUMP_ENABLED() -> bool:
        return _config_manager.get('Starvell', 'autoRaise', False)
    
    @staticmethod
    def AUTO_BUMP_INTERVAL() -> int:
        return _config_manager.get('AutoRaise', 'interval', 3600)
    
    @staticmethod
    def AUTO_BUMP_GAME_ID() -> int:
        return _config_manager.get('AutoRaise', 'gameId', 1)
    
    @staticmethod
    def AUTO_BUMP_CATEGORIES() -> List[int]:
        return _config_manager.get('AutoRaise', 'categories', [10, 11, 12])
    
    # === Авто-выдача ===
    @staticmethod
    def AUTO_DELIVERY_ENABLED() -> bool:
        return _config_manager.get('Starvell', 'autoDelivery', False)
    
    # === Авто-восстановление ===
    @staticmethod
    def AUTO_RESTORE_ENABLED() -> bool:
        return _config_manager.get('Starvell', 'autoRestore', False)
    
    # === Автообновление ===
    @staticmethod
    def AUTO_UPDATE_ENABLED() -> bool:
        """Автоматически проверять обновления"""
        return _config_manager.get('AutoUpdate', 'enabled', True)
    
    @staticmethod
    def AUTO_UPDATE_INSTALL() -> bool:
        """Автоматически устанавливать обновления и перезапускать бот"""
        return _config_manager.get('AutoUpdate', 'auto_install', False)
    
    # === Вечный онлайн ===
    @staticmethod
    def KEEP_ALIVE_ENABLED() -> bool:
        """Поддерживать онлайн статус"""
        return _config_manager.get('KeepAlive', 'enabled', True)
    
    # === Чёрный список ===
    @staticmethod
    def BL_BLOCK_DELIVERY() -> bool:
        """Не выдавать товар пользователям из ЧС"""
        return _config_manager.get('Blacklist', 'block_delivery', True)
    
    @staticmethod
    def BL_BLOCK_RESPONSE() -> bool:
        """Не отвечать на команды пользователям из ЧС"""
        return _config_manager.get('Blacklist', 'block_response', True)
    
    @staticmethod
    def BL_BLOCK_MSG_NOTIF() -> bool:
        """Не уведомлять о сообщениях от пользователей из ЧС"""
        return _config_manager.get('Blacklist', 'block_msg_notifications', True)
    
    @staticmethod
    def BL_BLOCK_ORDER_NOTIF() -> bool:
        """Не уведомлять о заказах от пользователей из ЧС"""
        return _config_manager.get('Blacklist', 'block_order_notifications', True)
    
    @staticmethod
    def toggle_bl_setting(setting_key: str):
        """Переключить настройку чёрного списка"""
        current = _config_manager.get('Blacklist', setting_key, True)
        _config_manager.set('Blacklist', setting_key, not current)
    
    # === Debug ===
    @staticmethod
    def DEBUG() -> bool:
        return _config_manager.get('Other', 'debug', False)
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка конфигурации"""
        if not cls.BOT_TOKEN():
            raise ValueError("Telegram.token не установлен в _main.cfg")
        if not cls.PASSWORD_HASH():
            raise ValueError("Telegram.secretKeyHash не установлен в _main.cfg")
        if not cls.STARVELL_SESSION():
            raise ValueError("Starvell.session_cookie не установлен в _main.cfg")
        return True
    
    @classmethod
    def ensure_dirs(cls):
        """Создать необходимые директории"""
        storage_dir = Path(cls.STORAGE_DIR())
        storage_dir.mkdir(parents=True, exist_ok=True)
        (storage_dir / "cache").mkdir(exist_ok=True)
        (storage_dir / "settings").mkdir(exist_ok=True)
        (storage_dir / "stats").mkdir(exist_ok=True)
        (storage_dir / "products").mkdir(exist_ok=True)
    
    @classmethod
    def update(cls, **kwargs):
        """Обновить конфигурацию
        
        Пример: update(**{'auto_bump.enabled': True})
        Или: update(**{'Starvell.autoRaise': True})
        """
        for key, value in kwargs.items():
            if '.' in key:
                parts = key.split('.', 1)
                section_key = parts[0]
                cfg_key = parts[1]
                
                # Маппинг ключей на секции и параметры конфига
                if section_key == 'auto_bump' and cfg_key == 'enabled':
                    _config_manager.set('Starvell', 'autoRaise', value)
                elif section_key == 'auto_delivery' and cfg_key == 'enabled':
                    _config_manager.set('Starvell', 'autoDelivery', value)
                elif section_key == 'auto_restore' and cfg_key == 'enabled':
                    _config_manager.set('Starvell', 'autoRestore', value)
                elif section_key == 'notifications':
                    # Преобразуем snake_case в camelCase
                    if cfg_key == 'new_messages':
                        _config_manager.set('Notifications', 'newMessages', value)
                    elif cfg_key == 'new_orders':
                        _config_manager.set('Notifications', 'newOrders', value)
                    elif cfg_key == 'lot_restore':
                        _config_manager.set('Notifications', 'lotRestore', value)
                    elif cfg_key == 'bot_start':
                        _config_manager.set('Notifications', 'botStart', value)
                    elif cfg_key == 'lot_deactivate':
                        _config_manager.set('Notifications', 'lotDeactivate', value)
                    elif cfg_key == 'lot_bump':
                        _config_manager.set('Notifications', 'lotBump', value)
                    else:
                        # Прямая установка для других ключей
                        _config_manager.set('Notifications', cfg_key, value)
                else:
                    # Прямая установка секция.ключ
                    _config_manager.set(section_key, cfg_key, value)


# Получить менеджер конфигурации
def get_config_manager() -> ConfigManager:
    """Получить менеджер конфигурации"""
    return _config_manager
