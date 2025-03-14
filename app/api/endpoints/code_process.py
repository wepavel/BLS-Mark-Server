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
import asyncio

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

    dmcode = models.DataMatrixCodeCreate(dm_code=data)
    task_1 = asyncio.create_task(app_state.handle_dmcode(dmcode_create=dmcode))
    task_2 = asyncio.create_task(app_state.handle_dmcode_confirmation())

@router.post("/set-system-working/{gtin:path}")
async def set_system_working(gtin: str, db: AsyncSession = Depends(deps.get_db)) -> None:
    if app_state.get_working():
        app_state.set_working(False)
        app_state.set_current_gtin(gtin=None)
        return

    try:
        gtin_create = models.GTINCreate(code=gtin)
    except ValidationError as e:
        raise EXC(ErrorCode.GTINValidationError, details={'reason': str(e)})

    if not models.GTIN.from_gtin_create(gtin_create):
        raise EXC(ErrorCode.GTINValidationError)

    gtin_db = await crud.gtin.get_by_code(gtin=gtin, db=db)
    if not gtin_db:
        raise EXC(ErrorCode.GTINNotExists)

    app_state.set_current_gtin(gtin=gtin_db)


    app_state.set_working(True)
