# from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.config import settings
from app.db import base  # noqa
from app.db.base import Base
from app.db.session import engine


async def init_db(db: AsyncSession) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # _statuses = await crud.userstatus.create_multi(db, obj_in=models.statuses)

    _countries = await crud.

    # user = await crud.user.get_by_login(db, login=settings.FIRST_SUPERUSER)
    # if not user:
    #     user_in = models.UserCreate(
    #         login=settings.FIRST_SUPERUSER,
    #         password=settings.FIRST_SUPERUSER_PASSWORD,
    #         is_superuser=True,
    #     )
    #     user = await crud.user.create(db, obj_in=user_in)
