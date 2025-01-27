from typing import Generator
from app.db.session import SessionLocal


async def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        await db.close()
