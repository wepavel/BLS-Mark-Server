from sqlmodel.ext.asyncio.session import AsyncSession
from app.crud.base import CRUDBase
from app.models import GTIN, GTINCreate, GTINPublic, DataMatrixCode, GTINRemainder
from sqlmodel import select, func, literal_column

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

    async def get_remainder(self, *, db: AsyncSession, gtin: str) -> int:
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

    async def get_all_gtins_with_remainder(self, *, db: AsyncSession) -> list[GTINRemainder]:
        # Подзапрос для подсчета остатка по каждому GTIN
        remainder_subquery = (
            select(
                DataMatrixCode.gtin.label('gtin'),
                func.count().label('remainder')
            )
            .where(DataMatrixCode.export_time == None)
            .group_by(DataMatrixCode.gtin)
            .subquery()
        )

        # Основной запрос, объединяющий GTIN с подсчетом остатка
        query = (
            select(
                GTIN.code,
                GTIN.name,
                func.coalesce(remainder_subquery.c.remainder, literal_column('0')).label('remainder')
            )
            .outerjoin(remainder_subquery, GTIN.code == remainder_subquery.c.gtin)
        )

        result = await db.exec(query)
        return result.all()

gtin =  CRUDGTIN(GTIN)
