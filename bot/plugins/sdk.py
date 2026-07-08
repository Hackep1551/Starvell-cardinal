from dataclasses import dataclass
from typing import Any, Optional

from bot.core.config import ConfigManager
from bot.plugins.events import EventBus


@dataclass
class PluginContext:
    bot: Any
    api: Any
    starvell: Any
    db: Any
    notify: Any
    config: ConfigManager
    events: EventBus
    plugin_manager: Any
    plugin: Optional[Any] = None

    async def emit(self, event_name: str, data: dict | None = None, source: str = "plugin"):
        await self.events.emit(event_name, data or {}, source=source)

    def on(self, event_name: str, handler):
        plugin_uuid = self.plugin.uuid if self.plugin else None
        return self.events.on(event_name, handler, plugin_uuid=plugin_uuid)
