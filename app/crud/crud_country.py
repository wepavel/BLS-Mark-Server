from sqlmodel.ext.asyncio.session import AsyncSession

from app.crud.base import CRUDBase
from app.models.country import Country
from fastapi.encoders import jsonable_encoder
from sqlmodel import select, Session
from sqlalchemy.exc import IntegrityError
from app.core.logging import logger

class CRUDUserStatus(CRUDBase[Country, Country, Country]):
    async def create_multi_if_not_exist(self, db: AsyncSession, *, obj_in: list[Country]) -> list[Country]:
        result = []
        for item in obj_in:
            item_data = item.model_dump()
            test = await db.exec(select(Country).where(Country.id == item_data.get('id')))
            existing_obj = test.first()

            if existing_obj is None:
                db_obj = self.model(**item_data)  # type: ignore
                db.add(db_obj)
                try:
                    await db.flush()
                    result.append(db_obj)
                except IntegrityError:
                    await db.rollback()
                    print(f"Object with id {item_data.get('id')} already exists or violates constraints")
            else:
                result.append(existing_obj)

        await db.commit()
        return result

    # async def create(self, db: AsyncSession, *, obj_in: Country) -> Country:
    #     db_obj = Country(
    #         name=obj_in.name,
    #     )
    #     db.add(db_obj)
    #     await db.commit()
    #     await db.refresh(db_obj)
    #     return db_obj

    # async def create_multi(self, db: AsyncSession, *, obj_in: list[Country]) -> list[Country]:
    #     db_obj = [self.model(**jsonable_encoder(obj_in_data)) for obj_in_data in obj_in]
    #     db.add_all(db_obj)
    #     await db.commit()
    #     return db_obj
    #
    # async def create_with_owner(self, db: AsyncSession, *, obj_in: Country) -> Country:
    #     obj_in_data = jsonable_encoder(obj_in)
    #     db_obj = self.model(**obj_in_data)
    #     db.add(db_obj)
    #     await db.commit()
    #     await db.refresh(db_obj)
    #     return db_obj


country = CRUDUserStatus(Country)
