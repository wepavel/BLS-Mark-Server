from app.core.utils import validate_data_matrix

from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from fastapi import Depends
from app.models.dmcode import DataMatrixCodePublic
from app.core.exceptions import EXC
from app.api import deps

from fastapi import APIRouter

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.utils import validate_data_matrix
from app import crud
from app import models


router = APIRouter()


@router.post('/add-dmcode/{dmcode}')
async def add_dmcode(*, dm_code: str, db: AsyncSession = Depends(deps.get_db)) -> DataMatrixCodePublic:
    """
    Add new dmcode to system
    """
    dm_attrs = validate_data_matrix(dm_code)
    if dm_attrs is None:
        raise EXC(ErrorCode.DMCodeValidationError)

    return dm_attrs.to_public_data_matrix_code()

@router.get('/device-states/{dm_code}')
async def download_file(dm_code: str) -> DataMatrixCodePublic:
    dm_code_attrs = DataMatrixCodePublic()
    return dm_code_attrs
