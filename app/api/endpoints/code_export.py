from app import crud, models
from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from fastapi import Depends

# from app.models import DataMatrixCodeCreate, DataMatrixCode, DataMatrixCodePublic, DataMatrixCodeProblem
from app.models import Country
# from app.models import GTIN, GTINPublic

from app.api import deps
from urllib.parse import unquote  # Импортируем unquote
# from app.models.dmcode import validate_data_matrix
from datetime import datetime
from app.core.utils import timezone_to_utc, current_timezone
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

@router.get('/get-gtin-entry-dates/{is_exported}/{gtin}/{date}')
async def get_gtin_entry_dates(*, is_exported: bool, gtin: str, date: str, db: AsyncSession = Depends(deps.get_db)) -> list[str]:
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

    if is_exported:
        export_dates = await crud.dmcode.get_unique_entry_dates_with_export(db, gtin.code, month_date)
    else:
        export_dates = await crud.dmcode.get_unique_entry_dates(db, gtin.code, month_date)

    return [date.strftime("%Y_%m_%d") for date in export_dates]


@router.get('/get-gtin-dmcodes-by-date/{is_exported}/{gtin}/{date}')
async def get_gtin_dmcodes_by_date(*, is_exported: bool, gtin: str, date: str, db: AsyncSession = Depends(deps.get_db)
                                   ) -> list[models.DataMatrixCodePublic]:
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

    if is_exported:
        dm_codes = await crud.dmcode.get_codes_by_day_with_export(db, gtin.code, date_obj)
    else:
        dm_codes = await crud.dmcode.get_codes_by_day(db, gtin.code, date_obj)

    return dm_codes

@router.post('/export_dmcodes')
async def export_dmcodes(
        *,
        dm_codes: list[models.DataMatrixCodeCreate],
        db: AsyncSession = Depends(deps.get_db)
) -> list[models.DataMatrixCodeProblem]:
    problem_dm_codes: list[models.DataMatrixCodeProblem] = []
    valid_codes: list[models.DataMatrixCode] = []

    # Получаем все уникальные DataMatrix коды из запроса
    dm_code_values: set[str] = set(dm_code.dm_code for dm_code in dm_codes)

    # Получаем все уникальные DataMatrix коды
    unique_dm_code_values = [models.DataMatrixCodeCreate(dm_code=dm_code) for dm_code in dm_code_values]

    # Проверяем существование DataMatrix кодов в базе
    existing_dm_codes = await crud.dmcode.get_existing_multi(db=db, dm_codes=list(dm_code_values))
    existing_dm_code_values = [dm_code.dm_code for dm_code in existing_dm_codes]

    for dm_code in unique_dm_code_values:
        if dm_code.dm_code in existing_dm_code_values:
            # Игнорируем уже существующие коды
            continue

            parsed_code = models.DataMatrixCode.from_data_matrix_code_create(dm_code)

            if parsed_code is None:
                problem_dm_codes.append(
                    models.DataMatrixCodeProblem(dm_code=dm_code.dm_code, problem='Error validating dm code'))
            else:
                # Проверяем существование GTIN
                gtin = await crud.gtin.get_by_code(db=db, gtin=parsed_code.gtin)
                if not gtin:
                    problem_dm_codes.append(
                        models.DataMatrixCodeProblem(dm_code=dm_code.dm_code, problem='GTIN does not exist'))
                else:
                    valid_codes.append(parsed_code)

        if valid_codes:
            for valid_code in valid_codes:
                try:
                    dm_code_update = models.DataMatrixCodeUpdate(dm_code=valid_code.dm_code,
                                                                 entry_time=valid_code.entry_time,
                                                                 export_time=timezone_to_utc(dm_code_update.upload_time))
                    await crud.dmcode.update(db=db, db_obj=valid_code, obj_in=dm_code_update)

                # await crud.dmcode.create_multi(db=db, obj_in=valid_codes)
                except Exception as e:

                    problem_dm_codes.append(
                        models.DataMatrixCodeProblem(dm_code=valid_code.dm_code, problem='Error updating dm code')
                    )
                    raise EXC(ErrorCode.DMCodeAddingError, details={'reason': str(e)})

    return problem_dm_codes

@router.get('/get-all-dmcodes')
async def get_all_dmcodes(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.DataMatrixCodePublic]:
    """
    Get last 100 dmcodes from database
    """
    dmcode_list = await crud.dmcode.get_multi(db=db)

    return dmcode_list

@router.get('/get-all-gtins-with-remainds')
async def get_all_dmcodes_with_remainds(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.GTINRemainder]:
    """
    Get last 100 dmcodes from database
    """
    dmcode_list = await crud.gtin.get_all_gtins_with_remainder(db=db)

    return dmcode_list
