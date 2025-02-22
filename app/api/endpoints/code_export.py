from app import crud, models
from fastapi import APIRouter, Path
from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from fastapi import Depends

# from app.models import DataMatrixCodeCreate, DataMatrixCode, DataMatrixCodePublic, DataMatrixCodeProblem
from app.models import Country
# from app.models import GTIN, GTINPublic
from app.core.exceptions import EXC
from app.api import deps
from urllib.parse import unquote  # Импортируем unquote
# from app.models.dmcode import validate_data_matrix
from datetime import datetime

from fastapi import APIRouter

from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()

@router.get('/get-all-gtins')
async def get_all_gtins(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.GTINPublic]:
    """
    Get all existing gtins from DB
    """
    gtin_list = await crud.gtin.get_multi(db=db)
    return gtin_list

@router.get('/get-product-export-dates/{gtin}/{date}')
async def get_product_export_dates(*, gtin: str, month: str, db: AsyncSession = Depends(deps.get_db)) -> list[str]:
    """
    Get unique export dates for a specific GTIN in a given month
    """
    try:
        month_date = datetime.strptime(month, "%Y_%m")
    except ValueError:
        raise EXC(ErrorCode.ValidationError, details = {'detail': 'Invalid month format. Use YYYY_MM'})

    export_dates = await crud.dmcode.get_unique_export_dates(db, gtin, month_date)

    return [date.strftime("%Y_%m_%d") for date in export_dates]


@router.get('/get-all-dmcodes')
async def get_all_dmcodes(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.DataMatrixCodePublic]:
    """
    Get last 100 dmcodes from database
    """
    dmcode_list = await crud.dmcode.get_multi(db=db)

    return dmcode_list
