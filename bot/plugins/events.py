import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional


logger = logging.getLogger("PluginEvents")


@dataclass
class PluginEvent:
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "core"
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, list[tuple[Callable, Optional[str]]]] = {}
        self._enabled_checker: Optional[Callable[[Optional[str]], bool]] = None

    def set_enabled_checker(self, checker: Callable[[Optional[str]], bool]):
        self._enabled_checker = checker

    def on(self, event_name: str, handler: Callable, plugin_uuid: Optional[str] = None):
        self._handlers.setdefault(event_name, []).append((handler, plugin_uuid))
        return handler

    def off(self, event_name: str, handler: Callable):
        handlers = self._handlers.get(event_name, [])
        self._handlers[event_name] = [item for item in handlers if item[0] is not handler]

    async def emit(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "core",
    ):
        event = PluginEvent(event_name, data or {}, source)
        handlers = list(self._handlers.get(event_name, [])) + list(self._handlers.get("*", []))

        for handler, plugin_uuid in handlers:
            try:
                if self._enabled_checker and not self._enabled_checker(plugin_uuid):
                    continue

                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                name = getattr(handler, "__name__", repr(handler))
                logger.error(f"Ошибка обработчика события {event_name} ({name}): {e}", exc_info=True)
