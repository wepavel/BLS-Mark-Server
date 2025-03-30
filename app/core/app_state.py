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

class AppState:
    def __init__(self):
        self._is_working = False
        self._current_gtin: GTIN | None = None
        self._timeout = settings.DMCODE_HANDLE_TIMEOUT
        self._event_1 = asyncio.Event()
        self._event_2 = asyncio.Event()
        self._dmcode: DataMatrixCode | None = None
        self._lock = asyncio.Lock()
        self._processing_task: asyncio.Task | None = None
        #-----------DMCode Queue
        self._dmcode_buffer = deque(maxlen=settings.DMCODE_BUFFER_SIZE)
        self._buffer_lock = asyncio.Lock()
        self._buffer_replenish_task: asyncio.Task | None = None

    #------------------Base funcs------------------
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
        self._current_gtin = None
        self._is_working = None
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

    async def _replenish_buffer(self) -> bool:
        async with self._buffer_lock:
            needed_codes = settings.DMCODE_BUFFER_SIZE - len(self._dmcode_buffer)
            if needed_codes > 0 and self._current_gtin:
                async for db in get_db():
                    new_codes = await crud.dmcode.get_remaind_codes_by_gtin(
                        db=db,
                        gtin=self._current_gtin.code,
                        skip=len(self._dmcode_buffer),
                        limit=needed_codes,
                    )
                    self._dmcode_buffer.extend(new_codes)

            if len(self._dmcode_buffer) == 0:
                logger.warning("Buffer is empty after replenishment attempt.")
                return False
            return True

    async def _clear_buffer(self) -> None:
        async with self._buffer_lock:
            self._dmcode_buffer.clear()
        logger.info("Buffer cleared")

    async def _buffer_monitor(self):
        while True:
            logger.info('Buffer monitor started.')
            if self._is_working and len(self._dmcode_buffer) < settings.DMCODE_BUFFER_THRESHOLD:
                await self._replenish_buffer()
            await asyncio.sleep(settings.BUFFER_CHECK_INTERVAL)

    async def get_next_dmcode(self) -> DataMatrixCode | None:
        async with self._buffer_lock:
            return self._dmcode_buffer.popleft() if self._dmcode_buffer else None


    #----------------------------
    def set_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        dm_code = DataMatrixCode.from_data_matrix_code_create(dmcode_create)
        if dm_code is None:
            # TODO Create error message on ws
            pass
        self._dmcode = DataMatrixCode.from_data_matrix_code_create(dmcode_create)

    async def handle_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        from app.api.ws_eventbus import broadcast_dmcode as ws_broadcast_dmcode

        async with self._lock:
            dm_code = DataMatrixCode.from_data_matrix_code_create(dmcode_create)

        if dm_code is None or not self._is_working or dm_code.gtin != self._current_gtin.code:
            reason = (
                'Invalid DataMatrixCode' if dm_code is None else
                'System is not working' if not self._is_working else
                'GTIN mismatch'
            )
            logger.warning(f'{reason}: {dmcode_create}')
            empty_code = DataMatrixCode().empty_code()
            empty_code.dm_code = dmcode_create.dm_code
            await ws_broadcast_dmcode(empty_code)
            return

        self._dmcode = dm_code
        self._event_1.set()
        await self._start_processing()

    async def handle_dmcode_confirmation(self):
        async with self._lock:
            self._event_2.set()
        await self._start_processing()

    async def _start_processing(self):
        async with self._lock:
            if self._processing_task is None or self._processing_task.done():
                self._processing_task = asyncio.create_task(self._process_events())

    async def _process_events(self):
        try:
            await asyncio.wait_for(
                asyncio.gather(self._event_1.wait(), self._event_2.wait()),
                timeout=self._timeout
            )

            async with self._lock:
                if self._dmcode:
                    logger.info('DMCode successfully received')
                    from app.api.ws_eventbus import broadcast_dmcode as ws_broadcast_dmcode

                    self._dmcode.entry_time = datetime.now()

                    await ws_broadcast_dmcode(self._dmcode)
                else:
                    logger.warning('DMCode is None after successful event processing')
                    create_dm = DataMatrixCodeCreate(dm_code='')
                    dm_attrs = DataMatrixCode.from_data_matrix_code_create(data=create_dm)

                    if dm_attrs is None:
                        logger.warning('Error parsing DataMatrixCode')

        except asyncio.TimeoutError:
            logger.warning('DMCode receive timeout failed')

        finally:
            async with self._lock:
                self._event_1.clear()
                self._event_2.clear()
                self._dmcode = None

app_state = AppState()