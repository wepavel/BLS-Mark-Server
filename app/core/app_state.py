import asyncio
from app.models import GTINBase, GTINPublic, DataMatrixCodeCreate, DataMatrixCode
from app.core.config import settings
from app.core.logging import logger
from app.api.ws_eventbus import broadcast_dmcode as ws_broadcast_dmcode

class AppState:
    def __init__(self):
        self._is_working = False
        self._current_gtin: GTINBase | None = None
        self._timeout = settings.DMCODE_HANDLE_TIMEOUT
        self._event_1 = asyncio.Event()
        self._event_2 = asyncio.Event()
        self._dmcode: DataMatrixCode | None = None
        self._lock = asyncio.Lock()
        self._processing_task: asyncio.Task | None = None

    def set_working(self, is_working: bool) -> None:
        self._is_working = is_working

    def get_working(self) -> bool:
        return self._is_working

    def set_current_gtin(self, current_gtin: GTINBase) -> None:
        self._current_gtin = current_gtin

    def get_current_gtin(self) -> GTINPublic | None:
        return self._current_gtin

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