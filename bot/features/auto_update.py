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
        self._check_interval = 900  # Проверять каждые 15 минут (900 секунд)
        self._last_check: Optional[datetime] = None
        self._notification_sent = False  # Флаг отправки уведомления
        
    async def start(self):
        """Запустить сервис автообновления"""
        self._running = True
        
        # Первая проверка при старте
        logger.info("🔍 Проверка обновлений при запуске...")
        update_available = await self.check_for_updates()
        
        if update_available:
            # Если включено автообновление - устанавливаем сразу
            if BotConfig.AUTO_UPDATE_INSTALL():
                logger.info("🔄 Обнаружено обновление! Запускаю автоматическую установку...")
                
                # Уведомляем админов перед обновлением
                if self.notifier:
                    await self.notifier.notify_all_admins(
                        "update",
                        "🔄 <b>Обнаружено обновление при запуске!</b>\n"
                        f"Версия: {self.current_version} → {self.latest_version}\n\n"
                        "⏳ Начинается автоматическое обновление...",
                        force=True
                    )
                
                # Небольшая задержка для отправки уведомлений
                await asyncio.sleep(2)
                
                # Выполняем обновление
                result = await self.perform_update()
                
                if result["success"]:
                    logger.info("✅ Автообновление при запуске выполнено успешно! Перезапуск...")
                    
                    # Перезапускаем бот
                    import os
                    import sys
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    logger.error(f"❌ Ошибка автообновления при запуске: {result['message']}")
                    
                    if self.notifier:
                        await self.notifier.notify_all_admins(
                            "update",
                            f"❌ <b>Ошибка автообновления</b>\n\n{result['message']}",
                            force=True
                        )
            else:
                # Отправляем уведомление один раз
                if self.notifier and not self._notification_sent:
                    await self.notifier.notify_update_available(
                        self.current_version,
                        self.latest_version
                    )
                    self._notification_sent = True
                    logger.info("📨 Отправлено уведомление об обновлении")
        
        # Запускаем фоновую проверку обновлений (всегда активна)
        asyncio.create_task(self._update_check_loop())
        logger.info("✅ Сервис автообновления запущен (проверка каждые 15 минут)")
    
    async def stop(self):
        """Остановить сервис"""
        self._running = False
        logger.info("⏹️ Сервис автообновления остановлен")
    
    async def _update_check_loop(self):
        """Фоновая проверка обновлений"""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                
                update_available = await self.check_for_updates(notify=False, silent=True)
                
                # Если включено автоматическое обновление
                if update_available and BotConfig.AUTO_UPDATE_INSTALL():
                    logger.info("🔄 Запускаю автоматическое обновление...")
                    
                    # Уведомляем админов перед обновлением
                    if self.notifier:
                        await self.notifier.notify_all_admins(
                            "update",
                            "🔄 <b>Начинается автоматическое обновление...</b>\n"
                            f"Версия: {self.current_version} → {self.latest_version}\n\n"
                            "⏳ Бот будет перезапущен через несколько секунд",
                            force=True
                        )
                    
                    # Выполняем обновление
                    result = await self.perform_update()
                    
                    if result["success"]:
                        logger.info("✅ Автообновление выполнено успешно! Перезапуск...")
                        
                        # Небольшая задержка для отправки уведомлений
                        await asyncio.sleep(2)
                        
                        # Перезапускаем бот
                        import os
                        import sys
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    else:
                        logger.error(f"❌ Ошибка автообновления: {result['message']}")
                        
                        if self.notifier:
                            await self.notifier.notify_all_admins(
                                "update",
                                f"❌ <b>Ошибка автообновления</b>\n\n{result['message']}",
                                force=True
                            )
                elif update_available and not self._notification_sent:
                    # Отправляем уведомление только один раз
                    if self.notifier:
                        await self.notifier.notify_update_available(
                            self.current_version,
                            self.latest_version
                        )
                        self._notification_sent = True
                        logger.info("📨 Отправлено уведомление об обновлении")
                
            except Exception as e:
                logger.error(f"Ошибка в цикле проверки обновлений: {e}", exc_info=True)
    
    async def check_for_updates(self, notify: bool = False, silent: bool = False) -> bool:
        """
        Проверить наличие обновлений
        
        Args:
            notify: Отправить уведомление если обновление доступно
            silent: Не логировать процесс проверки (для фоновых проверок)
            
        Returns:
            True если обновление доступно
        """
        try:
            if not silent:
                logger.info(f"🔍 Проверка обновлений... Текущая версия: {self.current_version}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(VERSION_URL, timeout=10) as response:
                    if response.status != 200:
                        if not silent:
                            logger.warning(f"Не удалось проверить обновления: HTTP {response.status}")
                        return False
                    
                    content = await response.text()
                    
                    # Парсим версию из файла
                    version_match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
                    
                    if not version_match:
                        if not silent:
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
                        if not silent:
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
                        if not silent:
                            logger.info(f"✅ Установлена последняя версия: {self.current_version}")
                    
                    return self.update_available
                    
        except asyncio.TimeoutError:
            if not silent:
                logger.warning("⏱️ Таймаут при проверке обновлений")
            return False
        except Exception as e:
            if not silent:
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
            
            # Проверяем наличие локальных изменений
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            has_local_changes = bool(status_result.stdout.strip())
            stash_created = False
            
            if has_local_changes:
                logger.info("💾 Обнаружены локальные изменения, сохраняю их...")
                
                # Сначала сбрасываем version.py к версии из HEAD (если он изменён)
                subprocess.run(
                    ["git", "checkout", "HEAD", "--", "version.py"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Теперь сохраняем остальные локальные изменения в stash
                stash_result = subprocess.run(
                    ["git", "stash", "push", "-m", "Auto-update: temporary stash"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if stash_result.returncode == 0:
                    stash_created = True
                    logger.info("✅ Локальные изменения сохранены")
                else:
                    logger.warning(f"⚠️ Не удалось создать stash: {stash_result.stderr}")
            
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
            modified_files = []
            added_files = []
            protected_dirs = ["configs/", "storage/", "logs/", "plugins/", "docs/"]
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    
                    parts = line.split('\t', 1)
                    if len(parts) < 2:
                        continue
                    
                    status = parts[0]
                    file_path = parts[1]
                    
                    if status.startswith('D'):
                        # Проверяем защищённые папки
                        if any(file_path.startswith(pdir) for pdir in protected_dirs):
                            deleted_files.append(file_path)
                    elif status.startswith('M'):
                        modified_files.append(file_path)
                    elif status.startswith('A'):
                        added_files.append(file_path)
            
            # Логируем изменения
            if modified_files or added_files or deleted_files:
                logger.info("📝 Изменения в обновлении:")
                if modified_files:
                    logger.info(f"  ✏️  Изменено файлов: {len(modified_files)}")
                    for f in modified_files[:5]:  # Показываем первые 5
                        logger.info(f"      - {f}")
                    if len(modified_files) > 5:
                        logger.info(f"      ... и ещё {len(modified_files) - 5}")
                
                if added_files:
                    logger.info(f"  ➕ Добавлено файлов: {len(added_files)}")
                    for f in added_files[:5]:
                        logger.info(f"      - {f}")
                    if len(added_files) > 5:
                        logger.info(f"      ... и ещё {len(added_files) - 5}")
                
                if deleted_files:
                    logger.info(f"  🛡️  Защищено от удаления: {len(deleted_files)}")
                    for f in deleted_files[:5]:
                        logger.info(f"      - {f}")
                    if len(deleted_files) > 5:
                        logger.info(f"      ... и ещё {len(deleted_files) - 5}")
            
            # Если есть удаляемые файлы в защищённых папках - восстанавливаем их после merge
            restore_needed = len(deleted_files) > 0
            
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
                
                # Восстанавливаем stash если создавали
                if stash_created:
                    subprocess.run(["git", "stash", "pop"], capture_output=True)
                    
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
                    ["git", "commit", "--no-edit", "-m", "Auto-update: merge with protected files"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if commit_result.returncode != 0:
                    # Если нечего коммитить - это нормально
                    if "nothing to commit" not in commit_result.stdout:
                        logger.warning(f"Предупреждение при коммите: {commit_result.stderr}")
            
            # Восстанавливаем локальные изменения из stash
            if stash_created:
                logger.info("♻️ Восстанавливаю локальные изменения...")
                stash_pop_result = subprocess.run(
                    ["git", "stash", "pop"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if stash_pop_result.returncode == 0:
                    logger.info("✅ Локальные изменения восстановлены")
                else:
                    logger.warning(f"⚠️ Не удалось восстановить stash: {stash_pop_result.stderr}")
            
            # Проверяем что файлы обновились
            if "Already up to date" in output or "Already up-to-date" in output:
                # Восстанавливаем stash если был создан
                if stash_created:
                    logger.info("♻️ Восстанавливаю локальные изменения...")
                    stash_pop_result = subprocess.run(
                        ["git", "stash", "pop"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if stash_pop_result.returncode == 0:
                        logger.info("✅ Локальные изменения восстановлены")
                
                return {
                    "success": True,
                    "message": "✅ Уже установлена последняя версия",
                    "output": output
                }
            
            logger.info("✅ Обновление успешно выполнено!")
            
            # Сохраняем старую версию для сообщения
            old_version = self.current_version
            
            # Логируем итоговую статистику изменений
            total_changes = len(modified_files) + len(added_files)
            if total_changes > 0:
                logger.info(f"📊 Итого изменений: {total_changes} файлов")
                if modified_files:
                    logger.info(f"   ✏️  Изменено: {len(modified_files)}")
                if added_files:
                    logger.info(f"   ➕ Добавлено: {len(added_files)}")
                if deleted_files:
                    logger.info(f"   🛡️  Защищено: {len(deleted_files)}")
            
            # Формируем сообщение о защищённых файлах
            protected_msg = ""
            if restore_needed:
                protected_msg = f"\n🛡️ Защищено файлов: {len(deleted_files)}"
            
            # Информация о восстановленных локальных изменениях
            local_changes_msg = ""
            if stash_created:
                local_changes_msg = "\n♻️ Локальные изменения сохранены"
            
            # Перезагружаем version модуль
            import importlib
            import version as version_module
            importlib.reload(version_module)
            
            from version import VERSION as NEW_VERSION
            
            # Обновляем текущую версию и сбрасываем флаги
            self.current_version = NEW_VERSION
            self.update_available = False
            self._notification_sent = False
            
            return {
                "success": True,
                "message": f"✅ Обновление выполнено!\n"
                          f"Версия: {old_version} → {NEW_VERSION}{protected_msg}{local_changes_msg}",
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
    
    def reset_notification_flag(self):
        """Сбросить флаг отправки уведомления (например, после обновления)"""
        self._notification_sent = False
        logger.info("🔔 Флаг уведомления сброшен")
