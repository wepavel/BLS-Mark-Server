from sqlmodel.ext.asyncio.session import AsyncSession
from app.crud.base import CRUDBase
from app import crud, models
from app.models import DataMatrixCode, DataMatrixCodeCreate, DataMatrixCodePublic, GTINPublic, DataMatrixCodeUpdate
from sqlmodel import select, func
from typing import Any
from datetime import datetime


class CRUDUDmCode(CRUDBase[DataMatrixCode, DataMatrixCodeCreate, DataMatrixCodeUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: DataMatrixCodeCreate) -> DataMatrixCodePublic | None:

        db_obj = DataMatrixCode.from_data_matrix_code_create(obj_in)
        if not db_obj:
            return None
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Получаем имя продукта из GTIN
        query = select(models.GTIN.name).where(models.GTIN.code == db_obj.gtin)
        result = await db.exec(query)
        product_name = result.one_or_none() or "Unknown Product"

        public_obj = db_obj.to_public_data_matrix_code()
        public_obj.product_name = product_name

        return public_obj


    async def create_multi(self, *, db: AsyncSession, obj_in: list[DataMatrixCodeCreate]) -> list[DataMatrixCodePublic]:
        db_objs = [DataMatrixCode.from_data_matrix_code_create(obj) for obj in obj_in if obj]
        db.add_all(db_objs)
        await db.commit()

        # Получаем все DataMatrixCode объекты вместе с именами продуктов из GTIN
        gtin_codes = [obj.gtin for obj in db_objs]
        query = (
            select(DataMatrixCode, models.GTIN.name.label("product_name"))
            .join(models.GTIN, DataMatrixCode.gtin == models.GTIN.code)
            .where(DataMatrixCode.gtin.in_(gtin_codes))
        )
        result = await db.exec(query)
        rows = result.all()

        public_objs = []
        for row in rows:
            dm_code, product_name = row
            public_obj = dm_code.to_public_data_matrix_code()
            public_obj.product_name = product_name or "Unknown Product"
            public_objs.append(public_obj)

        return public_objs

    async def get_by_code(self, db: AsyncSession, dm_code: str) -> DataMatrixCodePublic | None:
        query = (
            select(DataMatrixCode, models.GTIN.name.label("product_name"))
            .join(models.GTIN, DataMatrixCode.gtin == models.GTIN.code)
            .where(DataMatrixCode.dm_code == dm_code)
        )
        result = await db.exec(query)
        row = result.one_or_none()

        if not row:
            return None

        dm_code_attrs, product_name = row
        public_obj = dm_code_attrs.to_public_data_matrix_code()
        public_obj.product_name = product_name or "Unknown Product"
        return public_obj

    async def _get_by_code(self, db: AsyncSession, dm_code: str) -> DataMatrixCode | None:
        result = await db.exec(select(DataMatrixCode).where(DataMatrixCode.dm_code == dm_code))

        return result.one_or_none()


    async def get_existing_multi(self, *, db: AsyncSession, dm_codes: list[str]) -> list[DataMatrixCodePublic]:
        query = (
            select(DataMatrixCode, models.GTIN.name.label("product_name"))
            .join(models.GTIN, DataMatrixCode.gtin == models.GTIN.code)
            .where(DataMatrixCode.dm_code.in_(dm_codes))
        )
        result = await db.exec(query)
        rows = result.all()

        public_objs = []
        for row in rows:
            dm_code, product_name = row
            public_obj = dm_code.to_public_data_matrix_code()
            public_obj.product_name = product_name or "Unknown Product"
            public_objs.append(public_obj)

        return public_objs


    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[DataMatrixCodePublic]:
        query = (
            select(DataMatrixCode, models.GTIN.name.label("product_name"))
            .join(models.GTIN, DataMatrixCode.gtin == models.GTIN.code)
            .offset(skip)
            .limit(limit)
        )
        result = await db.exec(query)
        rows = result.all()

        public_objs = []
        for row in rows:
            dm_code, product_name = row
            public_obj = dm_code.to_public_data_matrix_code()
            public_obj.product_name = product_name or "Unknown Product"
            public_objs.append(public_obj)

        return public_objs


    async def update(
            self,
            db: AsyncSession,
            *,
            db_obj: DataMatrixCode,
            obj_in: DataMatrixCodeUpdate | dict[str, Any]
    ) -> DataMatrixCodePublic:

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Обработка временных полей
        if 'entry_time' in update_data:
            if update_data['entry_time'] is not None:
                if isinstance(update_data['entry_time'], str):
                    update_data['entry_time'] = datetime.fromisoformat(update_data['entry_time'])
            else:
                # Если entry_time равно None, удаляем его из update_data
                del update_data['entry_time']

        if 'export_time' in update_data:
            if update_data['export_time'] is not None:
                if isinstance(update_data['export_time'], str):
                    update_data['export_time'] = datetime.fromisoformat(update_data['export_time'])
            else:
                # Если export_time равно None, удаляем его из update_data
                del update_data['export_time']

        result = await super().update(db, db_obj=db_obj, obj_in=update_data)
        result = result.to_public_data_matrix_code()
        product_name = await crud.gtin.get_by_code(db=db, gtin=result.gtin)
        if product_name:
            result.product_name = product_name.name

        return result

    async def get_unique_export_dates(self, db: AsyncSession, gtin: str, month: datetime) -> list[datetime]:
        query = select(func.date(DataMatrixCode.entry_time)).distinct()\
            .where(DataMatrixCode.gtin == gtin)\
            .where(DataMatrixCode.entry_time.isnot(None))\
            .where(func.extract('year', DataMatrixCode.entry_time) == month.year)\
            .where(func.extract('month', DataMatrixCode.entry_time) == month.month)\
            .order_by(func.date(DataMatrixCode.entry_time))

        result = await db.exec(query)
        results = result.fetchall()
        # results = [date for (date,) in result.fetchall()]
        return results

dmcode =  CRUDUDmCode(DataMatrixCode)

