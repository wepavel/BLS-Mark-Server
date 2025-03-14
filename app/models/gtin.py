from app.db.base_class import Base
from sqlmodel import Field, SQLModel
from pydantic import constr
from typing import Optional
from sqlalchemy import Column

class GTINBase(SQLModel, table=False):
    code: str = Field(min_length=14, max_length=14)

class GTINCreate(GTINBase, table=False):
    name: str = ''
    desc: str = Field(default='', max_length=32000)

class GTINPublic(GTINCreate, table=False):
    pass

class GTIN(Base, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    code: str = Field(index=True, unique=True, min_length=14, max_length=14)
    name: str = Field(max_length=255, unique=True)
    desc: str = Field(default='', max_length=32000)

    def to_gtin_public(self) -> GTINPublic:
        return GTINPublic(
            code=self.code,
            name=self.name,
            desc=self.desc,
        )

    @classmethod
    def from_gtin_create(cls, gtin: GTINCreate) -> Optional['GTIN']:
        # if len(gtin.code) != 14:
        #   return None
        return GTIN(
            code=gtin.code,
            name=gtin.name,
            desc=gtin.desc,
        )

