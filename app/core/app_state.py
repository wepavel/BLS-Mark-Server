import asyncio
from app.models import GTIN, GTINPublic, DataMatrixCodeCreate, DataMatrixCode
from app.models.dmcode import export_normalize_gs
from app.core.config import settings
from app.core.logging import logger
from collections import deque
from app import crud
from app.api.deps import get_db
from app.api.tcp_client import tcp_connection_manager, TCPDevice
from datetime import datetime
from app import models
from datetime import timezone
import time
from .utils import ping_device


class AppState:
    def __init__(self):
        self._is_working = False
        self._current_gtin: GTIN | None = None
        self._timeout = settings.DMCODE_HANDLE_TIMEOUT
        self._event_1 = asyncio.Event()
        self._event_2 = asyncio.Event()
        self._dmcode: DataMatrixCode | None = None
        self._lock = asyncio.Lock()
        self._handle_lock = asyncio.Lock()
        self._processing_task: asyncio.Task | None = None
        #-----------DMCode Queue
        self._dmcode_buffer = deque(maxlen=settings.DMCODE_BUFFER_SIZE)
        self._consumed_codes = deque(maxlen=settings.DMCODE_CONSUMED_BUFFER_SIZE)

        self._buffer_lock = asyncio.Lock()
        self._buffer_replenish_task: asyncio.Task | None = None

        self._last_confirmation_time = 0
        self._confirmation_cooldown = 1  # 100 мс между подтверждениями
        self._confirmation_queue = asyncio.Queue(maxsize=100)  # Ограничиваем размер очереди подтверждений

        self.dmcode_confirmation = False


        self.is_scanner = False
        self.is_printer = False
        self.is_plc = False
        self.is_database = False

        # loop = asyncio.get_event_loop()  # Получаем текущий event loop
        # loop.create_task(self._device_heartbeat())
        # asyncio.run(self._device_heartbeat())
        # self._device_heartbeat_task: asyncio.Task = asyncio.create_task(self._device_heartbeat())
    #------------------Base funcs------------------
    async def device_heartbeat(self):
        while True:
            self.is_scanner = await ping_device(settings.SCANNER_ADRESS)
            self.is_printer = await ping_device(settings.PRINTER_ADRESS)
            self.is_plc = await ping_device(settings.PLC_ADRESS)
            async for db in get_db():
                self.is_database = await crud.gtin.check_database_connection(db)
            await asyncio.sleep(settings.DEVICES_HEARTBEAT_INTERVAL)

    async def set_working(self, gtin: GTIN | None) -> None:
        self._current_gtin = gtin
        self._is_working = True

        if not await self._replenish_buffer():
            logger.warning("Unable to start the process due to empty buffer.")
            await self.set_stop()
            return

        if self._buffer_replenish_task is None or self._buffer_replenish_task.done():
            self._buffer_replenish_task = asyncio.create_task(self._buffer_monitor())
        client = await tcp_connection_manager.get_connection(TCPDevice.PRINTER)
        dmcode = await self.get_next_dmcode()
        if dmcode:
            success = await client.send_message(export_normalize_gs(dmcode.dm_code))
            if not success:
                logger.error("Failed to send the first code to the printer")
        else:
            logger.error("Unexpected error: buffer is empty after successful replenishment")
            await self.set_stop()

    async def set_stop(self):
        self._is_working = None
        self._current_gtin = None
        await self._clear_buffer()
        if self._buffer_replenish_task:
            self._buffer_replenish_task.cancel()
        self._buffer_replenish_task = None
        client = await tcp_connection_manager.get_connection(TCPDevice.PRINTER)
        success = await client.send_message(' ')

    def get_working(self) -> bool:
        return self._is_working

    # def set_current_gtin(self, gtin: GTIN | None) -> None:
    #     self._current_gtin = gtin

    def get_current_gtin(self) -> GTINPublic | None:
        return self._current_gtin.to_gtin_public() if self._current_gtin else None

    #---------------DMCode processing---------------
    # async def initialize_buffer(self) -> None:
    #     # await self._replenish_buffer()
    #     self._buffer_replenish_task = asyncio.create_task(self._buffer_monitor())

    # async def _replenish_buffer(self) -> bool:
    #     async with self._buffer_lock:
    #         needed_codes = settings.DMCODE_BUFFER_SIZE - len(self._dmcode_buffer)
    #         if needed_codes > 0 and self._current_gtin:
    #             # Получаем список кодов, которые уже есть в буфере
    #             existing_codes = [code.code for code in self._dmcode_buffer]
    #
    #             async for db in get_db():
    #                 new_codes = await crud.dmcode.get_remaind_codes_by_gtin(
    #                     db=db,
    #                     gtin=self._current_gtin.code,
    #                     exclude_codes=existing_codes,
    #                     limit=needed_codes,
    #                 )
    #                 if not new_codes:
    #                     break  # Если больше нет новых кодов, выходим из цикла
    #
    #                 logger.info(f"Получено {len(new_codes)} новых уникальных кодов для пополнения буфера")
    #                 self._dmcode_buffer.extend(new_codes)
    #                 needed_codes -= len(new_codes)
    #
    #         if len(self._dmcode_buffer) == 0:
    #             logger.warning("Буфер пуст после попытки пополнения. Возможно, нет доступных уникальных кодов.")
    #             return False
    #         return True

    # DMCode buffer management
    async def _replenish_buffer(self) -> bool:
        """Replenish the buffer with new codes from the database."""
        async with self._buffer_lock:
            needed_codes = settings.DMCODE_BUFFER_SIZE - len(self._dmcode_buffer)
            if needed_codes <= 0 or not self._current_gtin:
                return len(self._dmcode_buffer) > 0

            # Get list of codes to exclude (current buffer + consumed codes)
            existing_codes = [code.code for code in self._dmcode_buffer]
            consumed_codes = [code.code for code in self._consumed_codes]
            exclude_codes = existing_codes + consumed_codes

            try:
                async for db in get_db():
                    new_codes = await crud.dmcode.get_remaind_codes_by_gtin(
                        db=db,
                        gtin=self._current_gtin.code,
                        exclude_codes=exclude_codes,
                        limit=needed_codes,
                    )

                    if not new_codes:
                        break  # No more codes available

                    logger.info(f"Retrieved {len(new_codes)} new unique codes for buffer")
                    self._dmcode_buffer.extend(new_codes)
                    needed_codes -= len(new_codes)

                    if needed_codes <= 0:
                        break
            except Exception as e:
                logger.error(f"Error replenishing buffer: {str(e)}")

            is_buffer_empty = len(self._dmcode_buffer) == 0
            if is_buffer_empty:
                logger.warning("Buffer is empty after replenishment attempt. No available unique codes.")

            return not is_buffer_empty

    # async def _clear_buffer(self) -> None:
    #     async with self._buffer_lock:
    #         self._dmcode_buffer.clear()
    #     logger.info("Buffer cleared")

    async def _clear_buffer(self) -> None:
        """Clear the buffer and consumed codes."""
        async with self._buffer_lock:
            self._dmcode_buffer.clear()
            self._consumed_codes.clear()
        logger.info("Buffer and consumed codes cleared")

    # async def _buffer_monitor(self):
    #     while True:
    #         if self._is_working and len(self._dmcode_buffer) < settings.DMCODE_BUFFER_THRESHOLD:
    #             await self._replenish_buffer()
    #         await asyncio.sleep(settings.BUFFER_CHECK_INTERVAL)

    async def _buffer_monitor(self) -> None:
        """Monitor buffer level and replenish when needed."""
        try:
            while True:
                if self._is_working and len(self._dmcode_buffer) < settings.DMCODE_BUFFER_THRESHOLD:
                    await self._replenish_buffer()
                await asyncio.sleep(settings.BUFFER_CHECK_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Buffer monitor task cancelled")
        except Exception as e:
            logger.error(f"Error in buffer monitor: {str(e)}")

    # async def get_next_dmcode(self) -> DataMatrixCode | None:
    #     async with self._buffer_lock:
    #         return self._dmcode_buffer.popleft() if self._dmcode_buffer else None
    async def get_next_dmcode(self) -> DataMatrixCode | None:
        """Get the next code from the buffer and add it to consumed codes."""
        async with self._buffer_lock:
            if not self._dmcode_buffer:
                return None

            code = self._dmcode_buffer.popleft()
            # Add the code to consumed codes list
            self._consumed_codes.append(code)
            return code

    async def _send_code_to_printer(self, dmcode: DataMatrixCode) -> bool:
        """Send the next code to the printer device."""
        client = await tcp_connection_manager.get_connection(TCPDevice.PRINTER)

        success = await client.send_message(export_normalize_gs(dmcode.dm_code))
        if not success:
            logger.error("Failed to send code to printer")
            return False

        return True
    #----------------------------
    def set_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        """Set the current DataMatrix code."""
        dm_code = DataMatrixCode.from_data_matrix_code_create(dmcode_create)
        if dm_code is None:
            logger.warning(f"Invalid DataMatrix code: {dmcode_create}")
            return
        self._dmcode = dm_code

    async def handle_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        """Handle incoming DataMatrix code."""
        from app.api.ws_eventbus import broadcast_dmcode as ws_broadcast_dmcode

        # Validate the code
        async with self._lock:
            dm_code = DataMatrixCode.from_data_matrix_code_create(dmcode_create)

        # Check for invalid conditions
        if dm_code is None or not self._is_working or (
                self._current_gtin and dm_code.gtin != self._current_gtin.code):
            reason = (
                'Invalid DataMatrixCode' if dm_code is None else
                'System is not working' if not self._is_working else
                'GTIN mismatch'
            )
            logger.warning(f'{reason}: {dmcode_create}')

            # Send empty code response
            empty_code = DataMatrixCode().empty_code()
            empty_code.dm_code = DataMatrixCode.normalize_gs(dmcode_create.dm_code)
            await ws_broadcast_dmcode(empty_code)
            return

        # Process valid code
        self._dmcode = dm_code
        self._event_1.set()
        await self._start_processing()

    # async def handle_dmcode_confirmation(self) -> bool:
    #     async with self._lock:
    #         self._event_2.set()
    #     return await self._start_processing()
    async def handle_dmcode_confirmation(self) -> bool:
        """Handle confirmation of DataMatrix code processing."""
        async with self._lock:
            self._event_2.set()

        await self._start_processing()

        try:
            await asyncio.wait_for(
                self._wait_for_event_clear(),
                timeout=self._timeout + 2
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for event clear")
            return False

        return self.dmcode_confirmation

    async def _wait_for_event_clear(self):
        while self._event_2.is_set():
            # logger.info('Waiting for event clear')
            await asyncio.sleep(0.01)

    async def _start_processing(self) -> None:
        """Start the code processing task if not already running."""
        async with self._lock:
            if self._processing_task is None or self._processing_task.done():
                self._processing_task = asyncio.create_task(self._process_events())

    async def rotate_dmcode(self) -> None:
        # client = await tcp_connection_manager.get_connection(TCPDevice.PRINTER)
        dmcode = await self.get_next_dmcode()
        print(dmcode.dm_code)
        if dmcode:
            # success = await client.send_message(export_normalize_gs(dmcode.dm_code))
            success = await self._send_code_to_printer(dmcode)
            if not success:
                logger.error("Failed to send the first code to the printer")
        else:
            logger.error("Unexpected error: buffer is empty after successful replenishment")
            await self.set_stop()

    async def _process_events(self):
        try:
            logger.info('Processing events')
            await asyncio.wait_for(
                asyncio.gather(self._event_1.wait(), self._event_2.wait()),
                timeout=self._timeout
            )

            async with self._lock:
                if not self._dmcode:
                    logger.warning('DMCode is None after successful event processing')
                    self.dmcode_confirmation = False
                    return

                logger.info('DMCode successfully received')
                from app.api.ws_eventbus import broadcast_dmcode as ws_broadcast_dmcode

                # async for db in get_db():
                #     db_dm_code = await crud.dmcode._get_by_code(db=db, dm_code=self._dmcode.dm_code)
                #     # is_printed = await crud.dmcode.is_code_printed_exported(db=db, dm_code=self._dmcode.dm_code)
                # if not db_dm_code:
                #     logger.warning(f'DMCode does not exists in database')
                #     empty_code = DataMatrixCode().empty_code()
                #     empty_code.dm_code = self._dmcode.dm_code
                #     await ws_broadcast_dmcode(empty_code)
                #     self.dmcode_confirmation = False
                # if db_dm_code.entry_time or db_dm_code.export_time:
                #     logger.warning(f'DMCode already printed or exported: {self._dmcode.dm_code}')
                #     empty_code = DataMatrixCode().empty_code()
                #     empty_code.dm_code = self._dmcode.dm_code
                #     await ws_broadcast_dmcode(empty_code)
                #     self.dmcode_confirmation = False

                # dm_code_update = models.DataMatrixCodeUpdate(
                #     dm_code=db_dm_code.dm_code,
                #     entry_time=datetime.now(timezone.utc)
                # )
                # await crud.dmcode.update(db=db, db_obj=db_dm_code, obj_in=dm_code_update)

                self._dmcode.entry_time = datetime.now()
                await ws_broadcast_dmcode(self._dmcode)

                dmcode = await self.get_next_dmcode()
                if dmcode:
                    success = await self._send_code_to_printer(dmcode)
                    if not success:
                        logger.error("Failed to send the first code to the printer")
                        self.dmcode_confirmation = False
                else:
                    logger.error("Unexpected error: buffer is empty after successful replenishment")
                    await self.set_stop()
                    self.dmcode_confirmation = False

                self.dmcode_confirmation = True

        except asyncio.TimeoutError:
            logger.warning('DMCode receive timeout failed')
            self.dmcode_confirmation = False
        except asyncio.exceptions.CancelledError:
            logger.info("Process events operation was cancelled")
            self.dmcode_confirmation = False
        except Exception as e:
            logger.error(f"Unexpected error in _process_events: {str(e)}")
            self.dmcode_confirmation = False

        finally:
            async with self._lock:
                logger.info("Process events operation was finished")
                self._event_1.clear()
                self._event_2.clear()
                self._dmcode = None


app_state = AppState()