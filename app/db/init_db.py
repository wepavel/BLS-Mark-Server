# from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud
from app.core.config import settings
from app.db import base  # noqa
from app.db.base import Base
from app.db.session import engine
import asyncpg
from app.core.logging import logger
from app.models.country import CountryEnum

async def init_db(db: AsyncSession) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # _statuses = await crud.userstatus.create_multi(db, obj_in=models.statuses)

    _countries = CountryEnum.get_all_countries()
    _countries_new = await crud.country.create_multi_if_not_exist(db, obj_in=_countries)

    # user = await crud.user.get_by_login(db, login=settings.FIRST_SUPERUSER)
    # if not user:
    #     user_in = models.UserCreate(
    #         login=settings.FIRST_SUPERUSER,
    #         password=settings.FIRST_SUPERUSER_PASSWORD,
    #         is_superuser=True,
    #     )
    #     user = await crud.user.create(db, obj_in=user_in)


async def create_database():
    conn = None
    try:
        # Подключаемся к 'postgres' базе данных для создания новой БД
        conn = await asyncpg.connect(
            host=settings.POSTGRES_SERVER,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database='postgres'
        )

        # Проверяем, существует ли уже база данных
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.POSTGRES_DB
        )

        if not exists:
            # Если база данных не существует, создаем её
            await conn.execute(f"CREATE DATABASE {settings.POSTGRES_DB}")
            logger.info(f"Database {settings.POSTGRES_DB} created successfully")
        else:
            logger.info(f"Database {settings.POSTGRES_DB} already exists")

    except asyncpg.exceptions.PostgresError as e:
        logger.warn(f"An error occurred while working with PostgreSQL: {e}")
    finally:
        if conn:
            await conn.close()