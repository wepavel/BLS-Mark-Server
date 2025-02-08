from sqlmodel.ext.asyncio.session import AsyncSession
from app.crud.base import CRUDBase
from app import crud, models
from app.models import DataMatrixCode, DataMatrixCodeCreate, DataMatrixCodePublic, GTINPublic
from sqlmodel import select


class CRUDUser(CRUDBase[DataMatrixCode, DataMatrixCodeCreate, DataMatrixCode]):

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

        if row is None:
            return None

        dm_code, product_name = row
        public_obj = dm_code.to_public_data_matrix_code()
        public_obj.product_name = product_name or "Unknown Product"
        return public_obj

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

dmcode =  CRUDUser(DataMatrixCode)