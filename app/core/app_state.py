import asyncio
from app.models import GTIN, GTINPublic, DataMatrixCodeCreate, DataMatrixCode
from app.core.config import settings
from app.core.logging import logger
from collections import deque
from app import crud
from app.api.deps import get_db

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
    def set_working(self, is_working: bool) -> None:
        self._is_working = is_working

    def get_working(self) -> bool:
        return self._is_working

    def set_current_gtin(self, gtin: GTIN | None) -> None:
        self._current_gtin = gtin

    def get_current_gtin(self) -> GTINPublic | None:
        return self._current_gtin.to_gtin_public() if self._current_gtin else None
    #---------------DMCode processing---------------
    async def initialize_buffer(self):
        await self._replenish_buffer()
        self._buffer_replenish_task = asyncio.create_task(self._buffer_monitor())

    async def _replenish_buffer(self):
        async with self._buffer_lock:
            needed_codes = settings.DMCODE_BUFFER_SIZE - len(self._dmcode_buffer)
            if needed_codes > 0:
                async for db in get_db():
                    new_codes = await crud.dmcode.get_remaind_codes_by_gtin(db=db, gtin=self._current_gtin)
                self._dmcode_buffer.extend(new_codes)

    async def _buffer_monitor(self):
        while True:
            if len(self._dmcode_buffer) < settings.DMCODE_BUFFER_THRESHOLD:
                await self._replenish_buffer()
            await asyncio.sleep(settings.BUFFER_CHECK_INTERVAL)

    async def get_next_dmcode(self) -> DataMatrixCode | None:
        async with self._buffer_lock:
            return self._dmcode_buffer.popleft() if self._dmcode_buffer else None

    async def handle_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        async with self._lock:
            dm_code = await self.get_next_dmcode()
            if dm_code is None:
                logger.warning('No available DataMatrixCode in buffer')
                return
            self._dmcode = dm_code
            self._event_1.set()
        await self._start_processing()

    #----------------------------
    def set_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        dm_code = DataMatrixCode.from_data_matrix_code_create(dmcode_create)
        if dm_code is None:
            # TODO Create error message on ws
            pass
        self._dmcode = DataMatrixCode.from_data_matrix_code_create(dmcode_create)

    async def handle_dmcode(self, dmcode_create: DataMatrixCodeCreate) -> None:
        async with self._lock:
            dm_code = DataMatrixCode.from_data_matrix_code_create(dmcode_create)
            if dm_code is None:
                logger.warning(f'Invalid DataMatrixCode: {dmcode_create}')
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
                    await ws_broadcast_dmcode(self._dmcode)
                else:
                    logger.warning('DMCode is None after successful event processing')

        except asyncio.TimeoutError:
            logger.warning('DMCode receive timeout failed')

        finally:
            async with self._lock:
                self._event_1.clear()
                self._event_2.clear()
                self._dmcode = None

app_state = AppState()