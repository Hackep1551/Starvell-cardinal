"""
Система плагинов.
"""

from .manager import PluginManager, PluginData
from .cp import init_plugins_cp, BIND_TO_PRE_INIT
from .events import EventBus, PluginEvent
from .sdk import PluginContext

__all__ = [
    'PluginManager',
    'PluginData',
    'init_plugins_cp',
    'BIND_TO_PRE_INIT',
    'EventBus',
    'PluginEvent',
    'PluginContext',
]
