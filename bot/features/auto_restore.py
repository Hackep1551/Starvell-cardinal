"""
Модуль авто-восстановления лотов (по наличию товара)
"""

import asyncio
import logging
from typing import Dict
from pathlib import Path

from bot.core.config import BotConfig


logger = logging.getLogger("REST")


class AutoRestoreService:
    """Сервис автоматического восстановления лотов при наличии товара"""
    
    def __init__(self, starvell_service, auto_delivery_service):
        self.starvell = starvell_service
        self.auto_delivery = auto_delivery_service
        self.check_interval = 60  # Проверять каждую минуту
        self._task: asyncio.Task = None
        self.lot_states: Dict[str, dict] = {}  # lot_id -> {amount: int, active: bool}
        
    async def start(self):
        """Запустить сервис"""
        if BotConfig.AUTO_RESTORE_ENABLED():
            self._task = asyncio.create_task(self._restore_loop())
            logger.info("✅ Сервис авто-восстановления запущен")
        else:
            logger.info("Сервис авто-восстановления отключен")
    
    async def stop(self):
        """Остановить сервис"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Сервис авто-восстановления остановлен")
    
    async def _restore_loop(self):
        """Цикл проверки и восстановления лотов"""
        while True:
            try:
                if BotConfig.AUTO_RESTORE_ENABLED():
                    await self._check_and_restore()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле восстановления: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_restore(self):
        """Проверить и восстановить лоты при наличии товара"""
        try:
            # Получаем список всех лотов
            lots = await self.starvell.get_lots()
            
            if not lots:
                return
            
            for lot in lots:
                lot_id = str(lot.get('id'))
                lot_title = lot.get('title', lot_id)
                is_active = lot.get('active', False)
                current_amount = lot.get('amount', 0)
                
                # Сохраняем предыдущее состояние
                prev_state = self.lot_states.get(lot_id, {})
                prev_amount = prev_state.get('amount', current_amount)
                prev_active = prev_state.get('active', is_active)
                
                # Обновляем текущее состояние
                self.lot_states[lot_id] = {
                    'amount': current_amount,
                    'active': is_active,
                    'title': lot_title
                }
                
                # Логика автовосстановления:
                # Если лот деактивирован И количество товара упало до 0 (товары закончились)
                # И теперь появились товары - восстанавливаем лот
                
                # Проверяем, закончились ли товары
                if prev_amount > 0 and current_amount == 0:
                    logger.info(f"📦 Товары в лоте '{lot_title}' (ID: {lot_id}) закончились (было: {prev_amount}, стало: 0)")
                
                # Проверяем, появились ли товары у неактивного лота
                if not is_active and current_amount > 0:
                    # Лот неактивен, но есть товары
                    
                    # Проверяем товары в файле (если используется авто-выдача)
                    products_count = await self._get_products_count(lot_id)
                    
                    if products_count > 0:
                        logger.info(f"🔄 Восстанавливаю лот '{lot_title}' (ID: {lot_id}): есть товары ({products_count} шт.)")
                        await self._restore_lot(lot_id, lot_title, products_count)
                    else:
                        # Товары есть в БД, но нет в файле
                        if current_amount > 0:
                            logger.debug(f"Лот '{lot_title}' (ID: {lot_id}): amount={current_amount}, но файл товаров пуст")
                
                # Логируем деактивацию
                if prev_active and not is_active:
                    logger.info(f"🔴 Лот '{lot_title}' (ID: {lot_id}) деактивирован")
                    # TODO: отправить уведомление
                
                # Логируем активацию
                if not prev_active and is_active:
                    logger.info(f"🟢 Лот '{lot_title}' (ID: {lot_id}) активирован")
                    # TODO: отправить уведомление
                
        except Exception as e:
            logger.error(f"Ошибка проверки лотов: {e}", exc_info=True)
    
    async def _get_products_count(self, lot_id: str) -> int:
        """
        Получить количество товаров из файла авто-выдачи
        
        Args:
            lot_id: ID лота
            
        Returns:
            Количество доступных товаров
        """
        try:
            # Получаем товары через сервис авто-выдачи
            products = await self.auto_delivery.get_product(lot_id, peek=True)
            
            if products:
                # products - это список строк (товаров)
                return len(products) if isinstance(products, list) else 1
            
            return 0
            
        except:
            return 0
    
    async def _restore_lot(self, lot_id: str, lot_title: str, products_count: int):
        """
        Восстановить лот до указанного количества
        
        Args:
            lot_id: ID лота
            lot_title: Название лота
            products_count: Количество доступных товаров
        """
        try:
            # Активируем лот с указанием количества
            result = await self.starvell.activate_lot(lot_id, amount=products_count)
            
            if result:
                logger.info(f"✅ Лот '{lot_title}' (ID: {lot_id}) успешно восстановлен (количество: {products_count})")
                
                # Обновляем состояние
                self.lot_states[lot_id]['active'] = True
                self.lot_states[lot_id]['amount'] = products_count
                
                # TODO: отправить уведомление в Telegram
            else:
                logger.warning(f"⚠️ Не удалось восстановить лот '{lot_title}' (ID: {lot_id})")
                
        except Exception as e:
            logger.error(f"Ошибка восстановления лота '{lot_title}' (ID: {lot_id}): {e}", exc_info=True)
    
    async def on_order_completed(self, lot_id: str):
        """
        Обработка события завершения заказа
        
        Args:
            lot_id: ID лота
        """
        # Принудительная проверка этого лота
        if BotConfig.AUTO_RESTORE_ENABLED():
            await self._check_specific_lot(lot_id)
    
    async def _check_specific_lot(self, lot_id: str):
        """
        Проверить конкретный лот и восстановить при необходимости
        
        Args:
            lot_id: ID лота
        """
        try:
            lots = await self.starvell.get_lots()
            
            for lot in lots:
                if str(lot.get('id')) == lot_id:
                    is_active = lot.get('active', False)
                    current_amount = lot.get('amount', 0)
                    lot_title = lot.get('title', lot_id)
                    
                    if current_amount == 0 and not is_active:
                        # Проверяем файл товаров
                        products_count = await self._get_products_count(lot_id)
                        
                        if products_count > 0:
                            logger.info(f"🔄 Восстанавливаю лот '{lot_title}' после продажи")
                            await self._restore_lot(lot_id, lot_title, products_count)
                    
                    break
                    
        except Exception as e:
            logger.error(f"Ошибка проверки лота {lot_id}: {e}", exc_info=True)
