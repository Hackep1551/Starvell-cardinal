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
                # После загрузки проверим целостность/схему конфигурации 
                try:
                    self._sanitize_config()
                except Exception:
                    # Не ломаем загрузку конфигурации при ошибках очистки
                    pass
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
            'autoRaise': 'false',
            'autoDelivery': 'false',
            'autoRestore': 'false',
            'locale': 'ru'
        }
        
        self._config['Telegram'] = {
            'enabled': 'true',
            'token': '',
            'secretKeyHash': '',
            'adminIds': '[]'
        }
        
        self._config['Notifications'] = {
            'checkInterval': '30',
            'newMessages': 'true',
            'newOrders': 'true',
            'lotRestore': 'false',
            'botStart': 'false',
            'botStop': 'false',
            'lotDeactivate': 'false',
            'lotBump': 'false'
        }
        
        self._config['AutoResponse'] = {
            'orderConfirm': 'false',
            'orderConfirmText': 'Спасибо за покупку! Если возникнут вопросы - обращайтесь.',
            'reviewResponse': 'false',
            'reviewResponseText': 'Благодарю за отзыв! Рад был помочь.'
        }
        
        self._config['Monitor'] = { # Устарело, оставить для совместимости
            'chatPollInterval': '5',
            'ordersPollInterval': '10',
            'remoteInfoInterval': '120'
        }
        
        self._config['AutoRaise'] = {
            'enabled': 'false',
            'interval': '3600'
        }
        
        self._config['Storage'] = {
            'dir': 'storage'
        }
        
        # Прокси больше не поддерживается — параметр удалён
        
        self._config['AutoUpdate'] = {
            'enabled': 'true'
        }
        
        self._config['KeepAlive'] = {
            'enabled': 'true'
        }
        
        self._config['Other'] = {
            'debug': 'false',
            'watermark': '🤖',
            'useWatermark': 'true'
        }
        
        self.save()

    def _get_default_template(self) -> Dict[str, Dict[str, str]]:
        """Вернуть шаблон секций и ключей по умолчанию (как словарь).

        Используется для валидации/синхронизации существующего файла конфига.
        """
        return {
            'Starvell': {
                'session_cookie': '',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'autoRaise': 'false',
                'autoDelivery': 'false',
                'autoRestore': 'false',
                'locale': 'ru'
            },
            'Telegram': {
                'enabled': 'true',
                'token': '',
                'secretKeyHash': '',
                'adminIds': '[]'
            },
            'Notifications': {
                'checkInterval': '30',
                'newMessages': 'true',
                'newOrders': 'true',
                'lotRestore': 'false',
                'botStart': 'false',
                'botStop': 'false',
                'lotDeactivate': 'false',
                'lotBump': 'false'
            },
            'AutoResponse': {
                'orderConfirm': 'false',
                'orderConfirmText': 'Спасибо за покупку! Если возникнут вопросы - обращайтесь.',
                'reviewResponse': 'false',
                'reviewResponseText': 'Благодарю за отзыв! Рад был помочь.'
            },
            'Monitor': {
                'chatPollInterval': '5',
                'ordersPollInterval': '10',
                'remoteInfoInterval': '120'
            },
            'AutoRaise': {
                'enabled': 'false',
                'interval': '3600'
            },
            'Storage': {
                'dir': 'storage'
            },
            # Proxy section removed
            'AutoUpdate': {
                'enabled': 'true'
            },
            'KeepAlive': {
                'enabled': 'true'
            },
            'Other': {
                'debug': 'false',
                'watermark': '🤖',
                'useWatermark': 'true'
            }
        }

    def _sanitize_config(self):
        """Синхронизировать текущий конфиг со схемой по умолчанию.

        Удаляет лишние секции/ключи и добавляет отсутствующие ключи с
        дефолтными значениями.
        """
        default = self._get_default_template()

        # Удаляем лишние секции (те, которые не описаны в шаблоне)
        for section in list(self._config.sections()):
            if section not in default:
                del self._config[section]

        for section, keys in default.items():
            if not self._config.has_section(section):
                # Если секции нет - создаём и добавляем все ключи с дефолтами
                self._config.add_section(section)
                for key, val in keys.items():
                    self._config.set(section, key, val)
                continue

            # Если секция есть - удаляем ключи, не описанные в шаблоне
            # Сравниваем имена ключей в нижнем регистре, чтобы быть
            # нечувствительными к изменению регистра optionxform
            allowed = set(k.lower() for k in keys.keys())
            for key in list(self._config[section].keys()):
                if key.lower() not in allowed:
                    self._config.remove_option(section, key)
   
            # Добавляем отсутствующие ключи (не перезаписываем существующие)
            for key, val in keys.items():
                if not self._config.has_option(section, key):
                    self._config.set(section, key, val)

        # Сохраняем изменения
        self.save()
        
    def save(self):
        """Сохранить конфигурацию"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self._config.write(f)
            
    def _parse_value(self, value: str) -> Union[str, int, bool, list]:
        """Парсинг значения из строки"""
        # Сначала пытаемся преобразовать в list
        if value.startswith('[') and value.endswith(']'):
            try:
                return ast.literal_eval(value)
            except:
                pass
        
        # Пытаемся преобразовать в int (до bool, чтобы '1' не стало True)
        try:
            return int(value)
        except ValueError:
            pass
        
        # Пытаемся преобразовать в bool
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False
                
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
            str_value = 'true' if value else 'false'
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
        # Proxy support removed — всегда отключено
        return False
    
    @staticmethod
    def PROXY_IP() -> str:
        return ''
    
    @staticmethod
    def PROXY_PORT() -> str:
        return ''
    
    @staticmethod
    def PROXY_LOGIN() -> str:
        return ''
    
    @staticmethod
    def PROXY_PASSWORD() -> str:
        return ''
    
    @staticmethod
    def PROXY_CHECK() -> bool:
        """Проверять ли прокси перед использованием"""
        return False
    
    @staticmethod
    def PROXY() -> str:
        """
        Получить прокси строку (если включен)
        Формат: [login:password@]ip:port
        """
        # Proxy support removed — возвращаем пустую строку
        return ''
    
    @staticmethod
    def set_proxy(ip: str, port: str, login: str = '', password: str = '', enabled: bool = True, check: bool = False):
        """Установить прокси"""
        # Proxy support was removed; this function is a no-op to preserve compatibility
        return
    
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
    def NOTIFY_BOT_STOP() -> bool:
        return _config_manager.get('Notifications', 'botStop', False)
    
    @staticmethod
    def NOTIFY_LOT_DEACTIVATE() -> bool:
        return _config_manager.get('Notifications', 'lotDeactivate', True)
    
    @staticmethod
    def NOTIFY_LOT_BUMP() -> bool:
        return _config_manager.get('Notifications', 'lotBump', False)

    @staticmethod
    def NOTIFY_AUTO_TICKET() -> bool:
        """Уведомлять об отправке авто-тикета"""
        return _config_manager.get('Notifications', 'autoTicket', True)

    @staticmethod
    def NOTIFY_ORDER_CONFIRMED() -> bool:
        """Уведомлять о подтверждении заказа"""
        return _config_manager.get('Notifications', 'orderConfirmed', False)

    @staticmethod
    def NOTIFY_REVIEW() -> bool:
        """Уведомлять о новых отзывах"""
        return _config_manager.get('Notifications', 'review', False)

    @staticmethod
    def NOTIFY_AUTO_RESPONSES() -> bool:
        """Уведомлять при выполнении автоответов/команд"""
        return _config_manager.get('Notifications', 'autoResponses', False)
    
    # === Авто-поднятие ===
    @staticmethod
    def AUTO_BUMP_ENABLED() -> bool:
        return _config_manager.get('Starvell', 'autoRaise', False)
    
    @staticmethod
    def AUTO_BUMP_INTERVAL() -> int:
        return _config_manager.get('AutoRaise', 'interval', 3600)
    
    # === Авто-выдача ===
    @staticmethod
    def AUTO_DELIVERY_ENABLED() -> bool:
        return _config_manager.get('Starvell', 'autoDelivery', False)
    
    # === Авто-восстановление ===
    @staticmethod
    def AUTO_RESTORE_ENABLED() -> bool:
        return _config_manager.get('Starvell', 'autoRestore', False)
    
    # === Авто-прочтение ===
    @staticmethod
    def AUTO_READ_ENABLED() -> bool:
        """Автоматически помечать чаты как прочитанные"""
        return _config_manager.get('Starvell', 'autoRead', True)
    
    # === Авто-тикет ===
    @staticmethod
    def AUTO_TICKET_ENABLED() -> bool:
        """Автоматически отправлять тикеты для неподтверждённых заказов"""
        return _config_manager.get('Starvell', 'autoTicket', False)
    
    @staticmethod
    def AUTO_TICKET_INTERVAL() -> int:
        """Интервал проверки авто-тикета (секунды)"""
        return _config_manager.get('Starvell', 'autoTicketInterval', 3600)

    @staticmethod
    def AUTO_TICKET_MAX_ORDERS() -> int:
        """Максимум заказов в одном тикете"""
        return _config_manager.get('Starvell', 'autoTicketMaxOrders', 5)

    @staticmethod
    def AUTO_TICKET_ORDER_AGE() -> int:
        """Минимальный возраст заказа для авто-тикета (часы)"""
        return _config_manager.get('Starvell', 'autoTicketOrderAge', 48)
    
    # === Автоответы ===
    @staticmethod
    def ORDER_CONFIRM_RESPONSE_ENABLED() -> bool:
        """Автоответ на подтверждение заказа"""
        return _config_manager.get('AutoResponse', 'orderConfirm', False)
    
    @staticmethod
    def ORDER_CONFIRM_RESPONSE_TEXT() -> str:
        """Текст автоответа на подтверждение заказа"""
        return _config_manager.get('AutoResponse', 'orderConfirmText', 'Спасибо за покупку! Если возникнут вопросы - обращайтесь.')
    
    @staticmethod
    def REVIEW_RESPONSE_ENABLED() -> bool:
        """Автоответ на отзыв"""
        return _config_manager.get('AutoResponse', 'reviewResponse', False)
    
    @staticmethod
    def REVIEW_RESPONSE_TEXT() -> str:
        """Текст автоответа на отзыв"""
        return _config_manager.get('AutoResponse', 'reviewResponseText', 'Благодарю за отзыв! Рад был помочь.')
    
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

    @staticmethod
    def WATERMARK() -> str:
        return _config_manager.get('Other', 'watermark', '🤖')

    @staticmethod
    def USE_WATERMARK() -> bool:
        return _config_manager.get('Other', 'useWatermark', True)
    
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
                elif section_key == 'auto_read' and cfg_key == 'enabled':
                    _config_manager.set('Starvell', 'autoRead', value)
                elif section_key == 'auto_ticket':
                    if cfg_key == 'enabled':
                        _config_manager.set('Starvell', 'autoTicket', value)
                    elif cfg_key == 'interval':
                        _config_manager.set('Starvell', 'autoTicketInterval', value)
                    elif cfg_key == 'max_orders':
                        _config_manager.set('Starvell', 'autoTicketMaxOrders', value)
                    elif cfg_key == 'order_age':
                        _config_manager.set('Starvell', 'autoTicketOrderAge', value)
                elif section_key == 'notifications':
                    if cfg_key == 'new_messages':
                        _config_manager.set('Notifications', 'newMessages', value)
                    elif cfg_key == 'auto_ticket':
                        _config_manager.set('Notifications', 'autoTicket', value)
                    elif cfg_key == 'new_orders':
                        _config_manager.set('Notifications', 'newOrders', value)
                    elif cfg_key == 'lot_restore':
                        _config_manager.set('Notifications', 'lotRestore', value)
                    elif cfg_key == 'bot_start':
                        _config_manager.set('Notifications', 'botStart', value)
                    elif cfg_key == 'bot_stop':
                        _config_manager.set('Notifications', 'botStop', value)
                    elif cfg_key == 'order_confirmed':
                        _config_manager.set('Notifications', 'orderConfirmed', value)
                    elif cfg_key == 'review':
                        _config_manager.set('Notifications', 'review', value)
                    elif cfg_key == 'auto_responses':
                        _config_manager.set('Notifications', 'autoResponses', value)
                    elif cfg_key == 'lot_deactivate':
                        _config_manager.set('Notifications', 'lotDeactivate', value)
                    elif cfg_key == 'lot_bump':
                        _config_manager.set('Notifications', 'lotBump', value)
                    else:
                        # Прямая установка для других ключей
                        _config_manager.set('Notifications', cfg_key, value)
                elif section_key == 'other':
                    if cfg_key == 'use_watermark':
                        _config_manager.set('Other', 'useWatermark', value)
                    elif cfg_key == 'watermark':
                        _config_manager.set('Other', 'watermark', value)
                    else:
                        _config_manager.set('Other', cfg_key, value)
                else:
                    # Прямая установка секция.ключ
                    _config_manager.set(section_key, cfg_key, value)


# Получить менеджер конфигурации
def get_config_manager() -> ConfigManager:
    """Получить менеджер конфигурации"""
    return _config_manager
