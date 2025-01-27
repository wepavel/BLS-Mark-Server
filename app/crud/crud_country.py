from sqlmodel.ext.asyncio.session import AsyncSession

from app.crud.base import CRUDBase
from app.models.country import Country
from fastapi.encoders import jsonable_encoder
# from app.schemas.record import RecordCreate, RecordUpdate


class CRUDUserStatus(CRUDBase[Country, Country, Country]):
    async def create(self, db: AsyncSession, *, obj_in: Country) -> Country:
        db_obj = Country(
            name=obj_in.name,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_multi(self, db: AsyncSession, *, obj_in: list[Country]) -> list[Country]:
        db_obj = [self.model(**jsonable_encoder(obj_in_data)) for obj_in_data in obj_in]
        db.add_all(db_obj)
        await db.commit()
        return db_obj

    async def create_with_owner(self, db: AsyncSession, *, obj_in: Country) -> Country:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


country = CRUDUserStatus(Country)
