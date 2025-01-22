from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from app.models.device import Device

# from app.services.s3_async import s3


router = APIRouter()


@router.get('/device-states/{key:path}')
async def download_file(key: int) -> Device:
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
