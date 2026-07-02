"""
Функционал бота: автовыдача, автоподнятие, ЧС и т.д.
"""

from .auto_delivery import AutoDeliveryService
from .auto_raise import AutoRaiseService
from .auto_restore import AutoRestoreService
from .auto_update import AutoUpdateService
from .keep_alive import KeepAliveService
from .tasks import BackgroundTasks

__all__ = ['AutoDeliveryService', 'AutoRaiseService', 'AutoRestoreService', 'AutoUpdateService', 'KeepAliveService', 'BackgroundTasks']
