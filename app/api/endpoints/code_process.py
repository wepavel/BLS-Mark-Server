from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from fastapi import Depends

# from app.models import DataMatrixCodeCreate, DataMatrixCode, DataMatrixCodePublic, DataMatrixCodeProblem
from app.models import Country, DataMatrixCodeCreate
# from app.models import GTIN, GTINPublic
from app.core.exceptions import EXC
from app.api import deps
# from app.models.dmcode import validate_data_matrix

from fastapi import APIRouter

from sqlmodel.ext.asyncio.session import AsyncSession


# from app import crud
# from app import models
from app import crud, models
from fastapi import APIRouter

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

