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

@router.get('/get-gtin-entry-dates/{gtin}/{date}')
async def get_gtin_entry_dates(*, gtin: str, date: str, db: AsyncSession = Depends(deps.get_db)) -> list[str]:
    """
    Get unique export dates for a specific GTIN in a given month

    Args:
        gtin (str): Global Trade Item Number (GTIN), уникальный идентификатор продукта.
        date (str): Строка месяца в формате "YYYY_MM".
        db (AsyncSession): Асинхронная сессия базы данных, используемая для выполнения запросов к базе данных.

    Returns:
        list[str]: Список уникальных экспортных дат в формате "YYYY_MM_DD".
    """
    gtin = models.GTINBase(code=gtin)
    if not models.GTIN.from_gtin_create(models.GTINCreate(code=gtin.code, name='')):
        raise EXC(ErrorCode.GTINValidationError)
    if not await crud.gtin.get_by_code(gtin=gtin.code, db=db):
        raise EXC(ErrorCode.GTINNotExists)

    try:
        month_date = datetime.strptime(date, "%Y_%m")
    except ValueError:
        raise EXC(ErrorCode.ValidationError, details = {'detail': 'Invalid month format. Use YYYY_MM'})

    export_dates = await crud.dmcode.get_unique_export_dates(db, gtin.code, month_date)

    return [date.strftime("%Y_%m_%d") for date in export_dates]


@router.get('/get-gtin-dmcodes-by-date/{gtin}/{date}')
async def get_gtin_dmcodes_by_date(*, gtin: str, date: str, db: AsyncSession = Depends(deps.get_db)) -> list[models.DataMatrixCodePublic]:
    """
    Получить все DataMatrix коды для определенного дня.

    Args:
        gtin (str): Global Trade Item Number (GTIN), уникальный идентификатор продукта.
        date (str): Строка даты в формате "YYYY_MM_DD".
        db (AsyncSession): Асинхронная сессия базы данных.

    Returns:
        list[models.DataMatrixCodePublic]: Список объектов DataMatrixCodePublic.
    """
    gtin = models.GTINBase(code=gtin)
    if not models.GTIN.from_gtin_create(models.GTINCreate(code=gtin.code, name='')):
        raise EXC(ErrorCode.GTINValidationError)
    if not await crud.gtin.get_by_code(gtin=gtin.code, db=db):
        raise EXC(ErrorCode.GTINNotExists)

    try:
        date_obj = datetime.strptime(date, "%Y_%m_%d")
    except ValueError:
        raise EXC(ErrorCode.ValidationError, details={'detail': 'Invalid month format. Use YYYY_MM_DD'})

    dm_codes = await crud.dmcode.get_codes_by_day(db, gtin.code, date_obj)

    return dm_codes


@router.get('/get-all-dmcodes')
async def get_all_dmcodes(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.DataMatrixCodePublic]:
    """
    Get last 100 dmcodes from database
    """
    dmcode_list = await crud.dmcode.get_multi(db=db)

    return dmcode_list
