import asyncio

from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import logger
from sqlmodel.ext.asyncio.session import AsyncSession
# from sqlalchemy.orm import sessionmaker


logger.info(str(settings.SQLALCHEMY_DATABASE_URI).replace('postgresql', 'postgresql+asyncpg'))

DATABASE_URI = str(settings.SQLALCHEMY_DATABASE_URI).replace('postgresql', 'postgresql+asyncpg')

engine = create_async_engine(DATABASE_URI, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
# SessionLocal = sessionmaker(
#     engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
#     autocommit=False,
#     autoflush=False
# )

db_session = async_scoped_session(SessionLocal, scopefunc=asyncio.current_task)
