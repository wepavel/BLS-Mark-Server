from typing import AsyncGenerator
from app.db.session import SessionLocal, db_session


async def get_db() -> AsyncGenerator:
    try:
        # db = SessionLocal()
        db = db_session()
        yield db
    finally:
        await db.close()
