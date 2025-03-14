from sqlmodel.ext.asyncio.session import AsyncSession
from app.crud.base import CRUDBase
from app.models import GTIN, GTINCreate, GTINPublic, DataMatrixCode
from sqlmodel import select, func

class CRUDGTIN(CRUDBase[GTIN, GTIN, GTIN]):
    async def create(self, db: AsyncSession, *, obj_in: GTINCreate) -> GTIN | None:
        db_obj = GTIN.from_gtin_create(obj_in)
        if not db_obj:
            return None
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_code(self, *, db: AsyncSession, gtin: str) -> GTIN | None:
        result = await db.exec(select(GTIN).where(GTIN.code == gtin))
        return result.one_or_none()

    async def get_by_name(self, *, db: AsyncSession, name: str) -> GTIN | None:
        result = await db.exec(select(GTIN).where(GTIN.name == name))
        return result.one_or_none()

    async def get_existing_multi(self, *, db: AsyncSession, gtin_codes: list[str]) -> list[GTIN]:
        result = await db.exec(select(GTIN).where(GTIN.code.in_(gtin_codes)))
        return result.all()

    async def get_remainder(self, *, db: AsyncSession, gtin: str) -> GTIN | None:
        query = (
            select(func.count())
            .select_from(DataMatrixCode)
            .where(
                (DataMatrixCode.gtin == gtin) &
                (DataMatrixCode.export_time == None)
            )
        )

        result = await db.exec(query)
        count = result.one_or_none()

        return count


gtin =  CRUDGTIN(GTIN)
