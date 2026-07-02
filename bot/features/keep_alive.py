"""
Сервис вечного онлайна
"""

import asyncio
import logging
from typing import Optional

import aiohttp

from bot.core.config import BotConfig


logger = logging.getLogger("KeepAlive")


class KeepAliveService:
    """
    Сервис для поддержания онлайн статуса на Starvell

    Основной канал — Socket.IO websocket с namespace /online
    (так держит онлайн браузер, за QRATOR — через порт 8443).
    Если Socket.IO недоступен, работает HTTP heartbeat.
    """

    # Namespace, которые открывает фронтенд Starvell
    SOCKET_NAMESPACES = (
        "/chats",
        "/user-notifications",
        "/user-presence",
        "/viewed-offers",
        "/online",
    )

    def __init__(self, starvell):
        """
        Args:
            starvell: StarvellService instance
        """
        self.starvell = starvell
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._socket_task: Optional[asyncio.Task] = None
        self._interval = 60  # Интервал HTTP heartbeat в секундах
        self._last_success = None
        self._last_socket_success = None
        self._socket_enabled = True
        self._socket_fail_count = 0
        self._socket_stale_after = 45  # Секунд без пакетов = сокет мёртв

    async def start(self):
        """Запустить сервис"""
        if self._running:
            logger.warning("Сервис вечного онлайна уже запущен")
            return

        # Проверяем включено ли в конфиге
        if not BotConfig.KEEP_ALIVE_ENABLED():
            logger.info("⏸️ Вечный онлайн отключен в настройках")
            self._running = False
            return

        # Устанавливаем флаг и запускаем фоновые задачи
        self._running = True
        try:
            self._task = asyncio.create_task(self._keep_alive_loop())
            self._socket_task = asyncio.create_task(self._socket_mode_init())
            logger.info(f"Сервис вечного онлайна запущен (интервал: {self._interval}s)")
        except Exception as e:
            self._running = False
            logger.error(f"Не удалось запустить KeepAliveTask: {e}")

    async def stop(self):
        """Остановить сервис"""
        self._running = False

        for task_attr in ('_task', '_socket_task'):
            task = getattr(self, task_attr)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                setattr(self, task_attr, None)

        logger.info("⏹️ Сервис вечного онлайна остановлен")

    # ==================== Socket.IO ====================

    async def _socket_mode_init(self):
        """Проверить Socket.IO в фоне и запустить websocket-цикл"""
        try:
            self._socket_enabled = await self.starvell.is_socket_io_available()
            if self._socket_enabled:
                await self._online_socket_loop()
            else:
                logger.info("🟢 Вечный онлайн: режим HTTP heartbeat")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._socket_enabled = False
            logger.debug(f"Socket.IO init пропущен: {e}")

    async def _online_socket_loop(self):
        """Держать открытым websocket /online, как это делает браузер"""
        while self._running and self._socket_enabled:
            ws = None
            try:
                ws = await asyncio.wait_for(
                    self.starvell.connect_online_socket(),
                    timeout=25,
                )
                online_confirmed = False
                logger.info("🟢 Online websocket подключён")

                async for message in ws:
                    if not self._running:
                        break
                    if message.type != aiohttp.WSMsgType.TEXT:
                        if message.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
                        continue

                    payload = message.data

                    # Engine.IO handshake — подключаем namespace'ы
                    if payload.startswith("0"):
                        for namespace in self.SOCKET_NAMESPACES:
                            await ws.send_str(f"40{namespace},")
                    # ping -> pong
                    elif payload == "2":
                        await ws.send_str("3")
                        if online_confirmed:
                            self._mark_socket_alive()
                    # Подтверждение подключения namespace
                    elif payload.startswith("40/"):
                        namespace = self._parse_namespace(payload)
                        if namespace == "/online":
                            online_confirmed = True
                            logger.info("🟢 Namespace /online подтверждён — онлайн активен")
                        self._mark_socket_alive()
                    # Сервер закрыл namespace или соединение
                    elif payload.startswith(("41/", "44/")):
                        namespace = self._parse_namespace(payload)
                        self._socket_fail_count += 1
                        logger.warning(f"⚠️ Starvell закрыл namespace {namespace}: {payload[:120]}")
                        if namespace == "/online":
                            break
                    elif payload.startswith(("41", "1")):
                        break
                    else:
                        if online_confirmed:
                            self._mark_socket_alive()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._socket_fail_count += 1
                error_text = str(e).lower()
                # Socket.IO выключили на сервере — переходим на HTTP навсегда
                if "404" in error_text or "socket.io" in error_text:
                    self._socket_enabled = False
                    logger.info("ℹ️ Socket.IO недоступен — переключаюсь на HTTP heartbeat")
                    break
                if self._socket_fail_count <= 3 or self._socket_fail_count % 10 == 0:
                    logger.warning(
                        f"⚠️ Online websocket отвалился: {e} (ошибок подряд: {self._socket_fail_count})"
                    )
            finally:
                if ws and not ws.closed:
                    await ws.close()

            if self._running and self._socket_enabled:
                # Реконнект с нарастающей задержкой, максимум 2 минуты
                await asyncio.sleep(min(120, 10 * max(1, self._socket_fail_count)))

    def _mark_socket_alive(self):
        """Отметить живой пакет от сокета"""
        self._last_socket_success = asyncio.get_event_loop().time()
        self._socket_fail_count = 0

    @staticmethod
    def _parse_namespace(payload: str) -> Optional[str]:
        """Достать namespace из Socket.IO пакета вида '40/online,...'"""
        namespace = payload[2:]
        for sep in (",", "{", "["):
            idx = namespace.find(sep)
            if idx >= 0:
                namespace = namespace[:idx]
                break
        return namespace or None

    # ==================== HTTP heartbeat ====================

    async def _keep_alive_loop(self):
        """Основной цикл поддержания онлайна"""
        logger.debug("KeepAlive loop started")

        while self._running:
            try:
                await asyncio.sleep(self._interval)

                if not BotConfig.KEEP_ALIVE_ENABLED():
                    logger.debug("Вечный онлайн отключен, пропускаем heartbeat")
                    continue

                # Пока websocket живой, HTTP heartbeat не нужен
                now = asyncio.get_event_loop().time()
                socket_fresh = (
                    self._socket_enabled
                    and self._last_socket_success
                    and now - self._last_socket_success < self._socket_stale_after
                )

                if not socket_fresh:
                    await self._send_heartbeat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле вечного онлайна: {e}", exc_info=True)
                await asyncio.sleep(5)  # Короткая пауза перед повтором

    async def _send_heartbeat(self):
        """Отправить heartbeat запрос"""
        try:
            success = await asyncio.wait_for(self.starvell.keep_alive(), timeout=25)

            if success:
                self._last_success = asyncio.get_event_loop().time()
                logger.debug("💚 Heartbeat отправлен успешно")
            else:
                logger.warning("⚠️ Heartbeat не удался")

        except asyncio.TimeoutError:
            logger.warning("⚠️ Heartbeat завис по таймауту")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки heartbeat: {e}")

    def get_status(self) -> dict:
        """
        Получить статус сервиса

        Returns:
            dict с информацией о статусе
        """
        return {
            "running": self._running,
            "enabled": BotConfig.KEEP_ALIVE_ENABLED(),
            "interval": self._interval,
            "socket_enabled": self._socket_enabled,
            "last_success": self._last_success,
            "last_socket_success": self._last_socket_success,
            "socket_fail_count": self._socket_fail_count,
        }
