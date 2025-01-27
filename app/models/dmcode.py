import time
from uuid import UUID

from sqlmodel import Field

from app.db.base_class import Base
from datetime import datetime
# NEW_UUID = lambda: str(uuid.uuid4())


# class DMCode(Base, table=True):
#     id: UUID | None = Field(primary_key=True, index=True, unique=True, default=ULID.from_timestamp(time.time()))
#     gtin: str | None = Field(unique=True, index=True, nullable=False, foreign_key='gtin.id')
#     login: str | None = Field(unique=True, index=True, nullable=False)
#     country_id: int | None = Field(default=1, foreign_key='country.id')


import re
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class DataMatrixCode(Base, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    dm_code: str = Field(default=None, nullable=True)
    gtin: str = Field(index=True, max_length=14, foreign_key="gtin.code")
    serial_number: str = Field(max_length=5)
    country_id: int = Field(foreign_key="country.id")
    verification_key: str = Field(max_length=4)
    verification_key_value: str | None = Field(default=None, max_length=44)
    is_long_format: bool = Field(default=False)
    upload_date: datetime = Field(default_factory=lambda: datetime.utcnow().strftime("%Y_%m_%d_%H%M%S"))
    entry_time: datetime | None = Field(default=None)


class DataMatrixCodeBase(SQLModel, table=False):
    dm_code: str | None = None


class DataMatrixCodeCreate(DataMatrixCodeBase, table=False):
    dm_code: str


class DataMatrixCodePublic(DataMatrixCodeBase):
    dm_code: str
    gtin: str
    serial_number: str
    country: str
    is_long_format: bool
    verification_key: str
    verification_key_value: str | None
    upload_date: str
    entry_time: str | None
