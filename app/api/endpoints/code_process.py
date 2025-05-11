from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from fastapi import Depends, Request

from app.core.exceptions import EXC
from app.api import deps

from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import ValidationError
from app import crud, models
from fastapi import APIRouter
from app.core.app_state import app_state
from ..tcp_client import tcp_connection_manager, TCPDevice
import asyncio
import random

router = APIRouter()


@router.post('/set-entry-time')
async def set_entry_time(*, dm_code: models.DataMatrixCodeCreate,
                         db: AsyncSession = Depends(deps.get_db)) -> models.DataMatrixCodePublic:
    """
    Set current entry time
    """
    db_obj = await crud.dmcode._get_by_code(db=db, dm_code=dm_code.dm_code)
    if not db_obj:
        raise EXC(ErrorCode.DMCodeNotExists)

    result = crud.dmcode.update(db=db, db_obj=db_obj, obj_in=dm_code)

    return result

@router.post('/set-export-time')
async def set_export_time(*, dm_code: models.DataMatrixCodeUpdate,
                         db: AsyncSession = Depends(deps.get_db)) -> models.DataMatrixCodePublic:
    """
    Set current export time
    """
    db_obj = await crud.dmcode._get_by_code(db=db, dm_code=dm_code.dm_code)
    if not db_obj:
        raise EXC(ErrorCode.DMCodeNotExists)

    result = crud.dmcode.update(db=db, db_obj=db_obj, obj_in=dm_code)

    return result

@router.post('/set-custom-entry-time')
async def set_custom_time(*, dm_code: models.DataMatrixCodeUpdate, db: AsyncSession = Depends(deps.get_db)) -> models.DataMatrixCodePublic:
    """
    Set custom entry time
    """
    db_obj = await crud.dmcode._get_by_code(db=db, dm_code=dm_code.dm_code)
    if not db_obj:
        raise EXC(ErrorCode.DMCodeNotExists)

    result = crud.dmcode.update(db=db, db_obj=db_obj, obj_in=dm_code)

    return result

@router.post("/recieve-dmcode")
async def receive_dmcode(request: Request) -> None:

    body = await request.body()
    data = body.decode().strip()
    logger.info(f'Received DMCode request: {data}')

    dmcode = models.DataMatrixCodeCreate(dm_code=data)
    asyncio.create_task(app_state.handle_dmcode(dmcode_create=dmcode))
    # task_2 = asyncio.create_task(app_state.handle_dmcode_confirmation())

@router.post("/send-tcp-message/{message:path}")
async def send_tcp_message(message: str):
    client = await tcp_connection_manager.get_connection(TCPDevice.PRINTER)
    success = await client.send_message(message)
    if success:
        return {"status": "success", "message": f"Сообщение успешно отправлено на устройство"}
    else:
        raise EXC(ErrorCode.DMCodeAddingError)

@router.post("/rotate_dmcode")
async def rotate_dmcode():
    await app_state.rotate_dmcode()

@router.post("/set-system-working/{gtin:path}")
async def set_system_working(gtin: str, db: AsyncSession = Depends(deps.get_db)) -> None:
    if app_state.get_working():
        return

    if not app_state.is_scanner or not app_state.is_printer \
        or not app_state.is_plc or not app_state.is_plc:
        raise EXC(ErrorCode.DeviceDisconnect)

    try:
        gtin_create = models.GTINCreate(code=gtin)
    except ValidationError as e:
        raise EXC(ErrorCode.GTINValidationError, details={'reason': str(e)})

    if not models.GTIN.from_gtin_create(gtin_create):
        raise EXC(ErrorCode.GTINValidationError)

    gtin_db = await crud.gtin.get_by_code(gtin=gtin, db=db)
    if not gtin_db:
        raise EXC(ErrorCode.GTINNotExists)

    # app_state.set_current_gtin(gtin=gtin_db)

    await app_state.set_working(gtin=gtin_db)

@router.post("/group-codes")
async def group_codes() -> None:
    """
    Test delays for BLS Mark Group
    """
    sleep_time = round(random.uniform(0, 3), 2)
    await asyncio.sleep(sleep_time)

@router.post("/set-system-stop")
async def set_system_stop() -> None:
    if app_state.get_working():
        await app_state.set_stop()
    return