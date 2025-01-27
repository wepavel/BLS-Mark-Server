import asyncio

from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import logger

logger.info(str(settings.SQLALCHEMY_DATABASE_URI).replace('postgresql', 'postgresql+asyncpg'))

DATABASE_URI = str(settings.SQLALCHEMY_DATABASE_URI).replace('postgresql', 'postgresql+asyncpg')

engine = create_async_engine(DATABASE_URI, pool_pre_ping=True)

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_session = async_scoped_session(SessionLocal, scopefunc=asyncio.current_task)
