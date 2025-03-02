import asyncio
from app.models import GTINBase, GTINPublic, DataMatrixCodeCreate
from app.core.config import settings

class AppState:
    def __init__(self):
        self._is_working = False
        self._current_gtin: GTINBase | None = None
        self._timeout = settings.DMCODE_HANDLE_TIMEOUT
        self._event_1 = asyncio.Event()
        self._event_2 = asyncio.Event()
        self._dmcode = None

    def set_working(self, is_working: bool) -> None:
        self._is_working = is_working

    def get_working(self) -> bool:
        return self._is_working

    def set_current_gtin(self, current_gtin: GTINBase) -> None:
        self._current_gtin = current_gtin

    def get_current_gtin(self) -> GTINPublic | None:
        return self._current_gtin

    async def handle_dmcode(self, dmcode: DataMatrixCodeCreate) -> None:
        self._dmcode = dmcode
        self._event_1.set()
        await self._check_events()

    async def handle_dmcode_confirmation(self):
        self._event_2.set()
        await self._check_events()

    async def _check_events(self):
        try:
            # Ожидаем, пока оба события будут установлены или таймаут
            await asyncio.wait_for(
                asyncio.gather(self._event_1.wait(), self._event_2.wait()),
                timeout=self._timeout
            )
            # Если оба события установлены в заданный таймаут, выполняем первую функцию
            # await self.execute_success_action()
            dmcode = self._dmcode
            print('Event timeout success')
        except asyncio.TimeoutError:
            # Если таймаут произошел, выполняем вторую функцию
            print('Event timeout error')
        finally:
            # Сбрасываем события для повторного использования
            self._event_1.clear()
            self._event_2.clear()

app_state = AppState()