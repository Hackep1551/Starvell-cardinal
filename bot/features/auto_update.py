"""
Сервис автообновления Starvell Cardinal
"""

import logging
import asyncio
import aiohttp
import re
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta

from version import VERSION, VERSION_URL
from bot.core.config import BotConfig

logger = logging.getLogger("AutoUpdate")


class AutoUpdateService:
    """
    Сервис автоматического обновления бота
    Проверяет версию на GitHub и уведомляет о доступных обновлениях
    """
    
    def __init__(self, notifier=None):
        self.notifier = notifier
        self.current_version = VERSION
        self.latest_version: Optional[str] = None
        self.update_available = False
        self._running = False
        self._check_interval = 3600  # Проверять каждый час
        self._last_check: Optional[datetime] = None
        
    async def start(self):
        """Запустить сервис автообновления"""
        self._running = True
        
        # Первая проверка при старте
        await self.check_for_updates()
        
        # Запускаем фоновую проверку если автообновление включено
        if BotConfig.AUTO_UPDATE_ENABLED():
            asyncio.create_task(self._update_check_loop())
            logger.info("✅ Сервис автообновления запущен")
        else:
            logger.info("⏸️ Автообновление отключено (можно включить в настройках)")
    
    async def stop(self):
        """Остановить сервис"""
        self._running = False
        logger.info("⏹️ Сервис автообновления остановлен")
    
    async def _update_check_loop(self):
        """Фоновая проверка обновлений"""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                
                if not BotConfig.AUTO_UPDATE_ENABLED():
                    continue
                
                await self.check_for_updates(notify=True)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле проверки обновлений: {e}", exc_info=True)
    
    async def check_for_updates(self, notify: bool = False) -> bool:
        """
        Проверить наличие обновлений
        
        Args:
            notify: Отправить уведомление если обновление доступно
            
        Returns:
            True если обновление доступно
        """
        try:
            logger.info(f"🔍 Проверка обновлений... Текущая версия: {self.current_version}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(VERSION_URL, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"Не удалось проверить обновления: HTTP {response.status}")
                        return False
                    
                    content = await response.text()
                    
                    # Парсим версию из файла
                    version_match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
                    
                    if not version_match:
                        logger.warning("Не удалось распарсить версию из GitHub")
                        return False
                    
                    self.latest_version = version_match.group(1)
                    self._last_check = datetime.now()
                    
                    # Сравниваем версии
                    self.update_available = self._compare_versions(
                        self.current_version,
                        self.latest_version
                    )
                    
                    if self.update_available:
                        logger.info(
                            f"✨ Доступно обновление! "
                            f"{self.current_version} → {self.latest_version}"
                        )
                        
                        if notify and self.notifier:
                            await self.notifier.notify_update_available(
                                self.current_version,
                                self.latest_version
                            )
                    else:
                        logger.info(f"✅ Установлена последняя версия: {self.current_version}")
                    
                    return self.update_available
                    
        except asyncio.TimeoutError:
            logger.warning("⏱️ Таймаут при проверке обновлений")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка проверки обновлений: {e}", exc_info=True)
            return False
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """
        Сравнить версии (формат: major.minor.patch)
        
        Returns:
            True если latest > current
        """
        try:
            def parse_version(v: str) -> Tuple[int, int, int]:
                parts = v.split('.')
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
            
            current_tuple = parse_version(current)
            latest_tuple = parse_version(latest)
            
            return latest_tuple > current_tuple
            
        except Exception as e:
            logger.error(f"Ошибка сравнения версий: {e}")
            return False
    
    async def perform_update(self) -> dict:
        """
        Выполнить обновление (pull из git)
        Защищённые папки: configs, storage, logs, plugins, docs
        
        Returns:
            dict с результатом: {"success": bool, "message": str, "output": str}
        """
        try:
            logger.info("🔄 Начинаю безопасное обновление...")
            
            # Проверяем что мы в git репозитории
            import subprocess
            
            # Проверяем наличие .git
            if not Path(".git").exists():
                return {
                    "success": False,
                    "message": "❌ Это не Git репозиторий!",
                    "output": "Директория .git не найдена"
                }
            
            # Сохраняем текущую ветку
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": "❌ Не удалось определить ветку",
                    "output": result.stderr
                }
            
            branch = result.stdout.strip()
            
            # Получаем список файлов которые будут удалены
            result = subprocess.run(
                ["git", "fetch", "origin", branch],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": "❌ Ошибка при получении обновлений",
                    "output": result.stderr
                }
            
            # Проверяем какие файлы будут удалены
            result = subprocess.run(
                ["git", "diff", "--name-status", f"HEAD..origin/{branch}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            deleted_files = []
            protected_dirs = ["configs/", "storage/", "logs/", "plugins/", "docs/"]
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('D\t'):
                        file_path = line.split('\t', 1)[1]
                        # Проверяем защищённые папки
                        if any(file_path.startswith(pdir) for pdir in protected_dirs):
                            deleted_files.append(file_path)
            
            # Если есть удаляемые файлы в защищённых папках - восстанавливаем их после merge
            restore_needed = len(deleted_files) > 0
            
            if restore_needed:
                logger.info(f"🛡️ Защищаю {len(deleted_files)} файлов от удаления")
            
            # Выполняем git merge (без удаления защищённых файлов)
            result = subprocess.run(
                ["git", "merge", f"origin/{branch}", "--no-commit", "--no-ff"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            
            # Если есть конфликты или ошибки
            if result.returncode != 0 and "Already up to date" not in output:
                # Отменяем merge
                subprocess.run(["git", "merge", "--abort"], capture_output=True)
                return {
                    "success": False,
                    "message": f"❌ Ошибка при обновлении",
                    "output": output
                }
            
            # Восстанавливаем защищённые файлы
            if restore_needed and deleted_files:
                for file_path in deleted_files:
                    # Восстанавливаем файл из HEAD
                    restore_result = subprocess.run(
                        ["git", "checkout", "HEAD", "--", file_path],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if restore_result.returncode == 0:
                        logger.info(f"🛡️ Защищён файл: {file_path}")
            
            # Завершаем merge
            if "Already up to date" not in output:
                commit_result = subprocess.run(
                    ["git", "commit", "-m", "Auto-update: merge with protected files"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if commit_result.returncode != 0:
                    # Если нечего коммитить - это нормально
                    if "nothing to commit" not in commit_result.stdout:
                        logger.warning(f"Предупреждение при коммите: {commit_result.stderr}")
            
            # Проверяем что файлы обновились
            if "Already up to date" in output or "Already up-to-date" in output:
                return {
                    "success": True,
                    "message": "✅ Уже установлена последняя версия",
                    "output": output
                }
            
            logger.info("✅ Обновление успешно выполнено!")
            
            # Формируем сообщение о защищённых файлах
            protected_msg = ""
            if restore_needed:
                protected_msg = f"\n\n🛡️ Защищено файлов: {len(deleted_files)}"
            
            # Перезагружаем version модуль
            import importlib
            import version as version_module
            importlib.reload(version_module)
            
            from version import VERSION as NEW_VERSION
            
            return {
                "success": True,
                "message": f"✅ Обновление выполнено!\n"
                          f"Версия: {self.current_version} → {NEW_VERSION}{protected_msg}\n\n"
                          f"⚠️ Для применения изменений требуется перезапуск бота!",
                "output": output
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "❌ Таймаут при выполнении git pull",
                "output": "Превышено время ожидания"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "message": "❌ Git не установлен!",
                "output": "Установите Git: https://git-scm.com/"
            }
        except Exception as e:
            logger.error(f"Ошибка обновления: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ Ошибка: {str(e)}",
                "output": str(e)
            }
    
    def get_status(self) -> dict:
        """
        Получить статус обновлений
        
        Returns:
            dict с информацией о версии и обновлениях
        """
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "auto_update_enabled": BotConfig.AUTO_UPDATE_ENABLED(),
            "last_check": self._last_check.isoformat() if self._last_check else None
        }
