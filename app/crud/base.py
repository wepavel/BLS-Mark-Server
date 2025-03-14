from typing import Any, Generic, TypeVar

from fastapi.encoders import jsonable_encoder
# from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.logging import logger

from app.db.base_class import Base
from app.api import deps
from sqlmodel import text

ModelType = TypeVar('ModelType', bound=Base)
CreateModelType = TypeVar('CreateModelType', bound=SQLModel)
UpdateModelType = TypeVar('UpdateModelType', bound=SQLModel)


def merge_dicts(d1: dict, d2: dict) -> dict:
    for k, v in d2.items():
        if isinstance(v, dict) and isinstance(d1.get(k), dict):
            d1_node = d1.setdefault(k, {})
            merge_dicts(d1_node, v)
        else:
            d1[k] = v
    return d1


class CRUDBase(Generic[ModelType, CreateModelType, UpdateModelType]):
    def __init__(self, model: type[ModelType]) -> None:
        """
        CRUD object with default methods to
        Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLModel by Tiangolo class
        * `schema`: A SQLModel by Tiangolo (schema) class
        """
        self.model = model

    @staticmethod
    async def check_database_connection(db: AsyncSession) -> bool:
        try:
            # Используем text() для создания текстового SQL-выражения
            result = await db.exec(text("SELECT 1"))

            # Получаем первый результат
            row = result.scalar()

            # Проверяем, равен ли результат 1
            return row == 1

        except Exception as e:
            # В случае ошибки выводим сообщение и возвращаем False
            logger.error(f"Error connecting to database: {str(e)}")
            return False

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        result = await db.exec(select(self.model).where(self.model.id == id))
        return result.one_or_none()

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await db.exec(select(self.model).offset(skip).limit(limit))
        return list(result.fetchall())

    async def create(self, db: AsyncSession, *, obj_in: CreateModelType) -> ModelType:
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_multi(self, db: AsyncSession, *, obj_in: list[CreateModelType]) -> list[ModelType]:
        db_objs = [self.model(**obj.model_dump()) for obj in obj_in]
        db.add_all(db_objs)
        await db.commit()
        for obj in db_objs:
            await db.refresh(obj)
        return db_objs

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateModelType | dict[str, Any]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                if isinstance(obj_data[field], dict) and isinstance(update_data[field], dict):
                    setattr(db_obj, field, merge_dicts(obj_data[field], update_data[field]))
                else:
                    setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> ModelType | None:
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
