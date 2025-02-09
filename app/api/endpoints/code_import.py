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

from fastapi import APIRouter

from sqlmodel.ext.asyncio.session import AsyncSession


# from app import crud
# from app import models
from app import crud, models


router = APIRouter()


@router.post('/add-dmcode')
async def add_dmcode(*, dm_code: models.DataMatrixCodeCreate, db: AsyncSession = Depends(deps.get_db)) -> models.DataMatrixCodePublic:
    """
    Add new dmcode to system
    """
    dm_code = models.DataMatrixCode.from_data_matrix_code_create(dm_code)
    if dm_code is None:
        raise EXC(ErrorCode.DMCodeValidationError)

    if not await crud.gtin.get_by_code(gtin=dm_code.gtin, db=db):
        raise EXC(ErrorCode.GTINNotExists)

    existing_dmcode = await crud.dmcode.get_by_code(dm_code=dm_code.dm_code, db=db)
    if existing_dmcode:
        return existing_dmcode

    result = await crud.dmcode.create(
        obj_in=models.DataMatrixCodeCreate(dm_code=dm_code.dm_code),
        db=db
    )
    return result

@router.post('/add-dmcodes')
async def add_dmcodes(
        *,
        dm_codes: list[models.DataMatrixCodeCreate],
        db: AsyncSession = Depends(deps.get_db)
) -> list[models.DataMatrixCodeProblem]:
    """
    Add new dmcodes to system
    """
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
            problem_dm_codes.append(models.DataMatrixCodeProblem(dm_code=dm_code.dm_code, problem='Error validating dm code'))
        else:
            # Проверяем существование GTIN
            gtin = await crud.gtin.get_by_code(db=db, gtin=parsed_code.gtin)
            if not gtin:
                problem_dm_codes.append(models.DataMatrixCodeProblem(dm_code=dm_code.dm_code, problem='GTIN does not exist'))
            else:
                valid_codes.append(parsed_code)

    if valid_codes:
        try:
            await crud.dmcode.create_multi(db=db, obj_in=valid_codes)
        except Exception as e:
            raise EXC(ErrorCode.DMCodeAddingError, details={'reason': str(e)})

    return problem_dm_codes

@router.post('/add-gtin')
async def add_gtin(*, gtin: models.GTINCreate, db: AsyncSession = Depends(deps.get_db)) -> models.GTINPublic:
    """
    Add new gtin to system with name
    """
    if not models.GTIN.from_gtin_create(gtin):
        raise EXC(ErrorCode.GTINValidationError)

    if await crud.gtin.get_by_code(gtin=gtin.code, db=db) or await crud.gtin.get_by_name(name=gtin.name, db=db):
        raise EXC(ErrorCode.GTINAlreadyExists)

    result_gtin = await crud.gtin.create(obj_in=gtin, db=db)
    if not result_gtin:
        raise EXC(ErrorCode.GTINAddingError)

    return result_gtin.to_gtin_public()


@router.get('/is-gtin/{gtin_encoded}')
async def is_gtin(*, gtin_encoded: str, db: AsyncSession = Depends(deps.get_db)) -> bool:
    """
    Check if a GTIN exists in DB
    """
    gtin = models.GTINBase(code=unquote(gtin_encoded))
    if not models.GTIN.from_gtin_create(models.GTINCreate(code=gtin.code, name='')):
        raise EXC(ErrorCode.GTINValidationError)

    if await crud.gtin.get_by_code(gtin=gtin.code, db=db):
        return True
    else:
        return False


@router.get('/get-all-gtins')
async def get_all_gtins(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.GTINPublic]:
    """
    Get all existing gtins from DB
    """
    gtin_list = await crud.gtin.get_multi(db=db)
    return gtin_list


@router.get('/get-all-dmcodes')
async def get_all_dmcodes(*, db: AsyncSession = Depends(deps.get_db)) -> list[models.DataMatrixCodePublic]:
    """
    Get last 100 dmcodes from database
    """
    dmcode_list = await crud.dmcode.get_multi(db=db)

    return dmcode_list