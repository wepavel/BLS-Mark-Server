from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.api.ws_eventbus import send_broadcast_heartbeat_message, ws_eventbus, broadcast_msg
from app.core.config import settings
from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from app.models.device import Device

router = APIRouter()


@router.get('/device-states/{key}')
async def get_device_states(key: int) -> Device:
    if key == 0:
        raise EXC(ErrorCode.CoreFileUploadingError, details={'reason': 'Test'})

    logger.info('Hello world from endpoint')
    device = Device()
    # device.name = 'Test'
    # device.heartbeat = True
    # device.ping = True

    return device


@router.get('/service-heartbeat/{ping}')
async def ping(ping: str) -> PlainTextResponse:
    if ping == 'ping':
        return PlainTextResponse('pong')

    raise EXC(ErrorCode.InternalError)



