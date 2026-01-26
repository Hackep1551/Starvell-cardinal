from pathlib import Path
from datetime import datetime
from typing import Optional
import platform
import sys

USAGE_FILE = Path('logs') / 'usage_stats.txt'


def _ensure_dir():
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _env_info() -> str:
    """Вернуть краткую строку окружения с ОС и версией Python."""
    try:
        os_info = f"{platform.system()} {platform.release()}"
    except Exception:
        os_info = platform.system()
    py = platform.python_version()
    return f"os={os_info} python={py}"


def log_event(event: str, details: Optional[str] = None) -> None:
    """Добавить событие в файл статистики использования с меткой времени.

    Каждая запись содержит метку времени, имя события и детали. В деталях
    всегда присутствует информация об ОС и версии Python для упрощения
    обратной связи и телеметрии.

    Формат: [ISO_TIMESTAMP] EVENT - details | os=... python=...
    """
    try:
        _ensure_dir()
        ts = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
        line = f"[{ts}] {event}"

        env = _env_info()

        if details:
            # заменяем переводы строк, чтобы запись была в одну строку
            safe = str(details).replace('\n', ' | ')
            line = f"{line} - {safe} | {env}"
        else:
            line = f"{line} - {env}"

        with open(USAGE_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except Exception:
        # Никогда не бросаем исключение из логирования
        pass


def read_events(limit: int = 100) -> list:
    """Вернуть последние `limit` строк из файла статистики (от старых к новым).
    Если файл не существует — вернуть пустой список.
    """
    try:
        if not USAGE_FILE.exists():
            return []
        with open(USAGE_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            return lines[-limit:]
    except Exception:
        return []
