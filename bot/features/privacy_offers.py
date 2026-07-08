import asyncio
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bot.core.config import BotConfig, get_config_manager


logger = logging.getLogger(__name__)


TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def parse_hhmm(value: str) -> int:
    value = str(value or "").strip()
    if not TIME_RE.match(value):
        raise ValueError("Время должно быть в формате HH:MM")

    hour, minute = map(int, value.split(":"))
    if hour > 23 or minute > 59:
        raise ValueError("Время должно быть в формате HH:MM")
    return hour * 60 + minute


def normalize_time(value: str) -> str:
    minutes = parse_hhmm(value)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _expand_window(start: int, end: int):
    if start == end:
        raise ValueError("Начало и конец окна не должны совпадать")
    if start < end:
        return [(start, end)]
    return [(start, 1440), (0, end)]


def _window_intervals(windows: list) -> list:
    intervals = []
    for index, window in enumerate(windows):
        start = parse_hhmm(window.get("start"))
        end = parse_hhmm(window.get("end"))
        for interval_start, interval_end in _expand_window(start, end):
            intervals.append((interval_start, interval_end, index))
    return sorted(intervals)


def validate_windows(windows: list) -> None:
    intervals = _window_intervals(windows)
    for i, (start, end, source) in enumerate(intervals):
        for other_start, other_end, other_source in intervals[i + 1:]:
            if other_start >= end:
                break
            if source != other_source and start < other_end and other_start < end:
                raise ValueError("Окна не должны пересекаться")


def add_window(windows: list, start: str, end: str) -> list:
    next_windows = [
        {"start": normalize_time(window.get("start")), "end": normalize_time(window.get("end"))}
        for window in windows
    ]
    next_windows.append({"start": normalize_time(start), "end": normalize_time(end)})
    validate_windows(next_windows)
    return sorted(next_windows, key=lambda item: parse_hhmm(item["start"]))


def remove_window(windows: list, index: int) -> list:
    return [window for i, window in enumerate(windows) if i != index]


def is_in_window(now: datetime, windows: list) -> bool:
    current = now.hour * 60 + now.minute
    for window in windows:
        start = parse_hhmm(window.get("start"))
        end = parse_hhmm(window.get("end"))
        if start < end and start <= current < end:
            return True
        if start > end and (current >= start or current < end):
            return True
    return False


def desired_visibility(now: datetime, mode: str, windows: list) -> str | None:
    if not windows:
        return None

    in_window = is_in_window(now, windows)
    if mode == "online":
        return "PUBLIC" if in_window else "HIDDEN"
    return "HIDDEN" if in_window else "PUBLIC"


class PrivacyOffersService:
    def __init__(self, starvell):
        self.starvell = starvell
        self._task = None
        self._stopping = asyncio.Event()

    async def start(self):
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def trigger_immediate_check(self):
        await self._apply()

    async def _run(self):
        while not self._stopping.is_set():
            try:
                await self._apply()
            except Exception as e:
                logger.warning(f"Не удалось обновить приватность предложений: {e}")

            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=60)
            except asyncio.TimeoutError:
                pass

    async def _apply(self):
        if not BotConfig.PRIVACY_OFFERS_ENABLED():
            return

        windows = BotConfig.PRIVACY_OFFERS_WINDOWS()
        if not windows:
            return

        validate_windows(windows)
        timezone = BotConfig.PRIVACY_OFFERS_TIMEZONE()
        try:
            now = datetime.now(ZoneInfo(timezone))
        except ZoneInfoNotFoundError:
            now = datetime.now(ZoneInfo("Europe/Moscow"))

        visibility = desired_visibility(now, BotConfig.PRIVACY_OFFERS_MODE(), windows)
        if not visibility:
            return

        if BotConfig.PRIVACY_OFFERS_LAST_APPLIED() == visibility:
            return

        current_visibility = await self.starvell.get_offers_visibility()
        if current_visibility != visibility:
            await self.starvell.update_offers_visibility(visibility)

        get_config_manager().set("PrivacyOffers", "lastApplied", visibility)
