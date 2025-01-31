import time
from uuid import UUID

from sqlmodel import Field

from app.db.base_class import Base
from datetime import datetime, timezone
from .country import CountryEnum
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


class DataMatrixCodeBase(SQLModel, table=False):
    dm_code: str


class DataMatrixCodeCreate(DataMatrixCodeBase, table=False):
    dm_code: str


class DataMatrixCodePublic(DataMatrixCodeBase, table=False):
    dm_code: str
    gtin: str
    serial_number: str
    country: str
    is_long_format: bool
    verification_key: str
    verification_key_value: str | None
    upload_date: str
    entry_time: str | None
    export_time: str | None


class DataMatrixCode(Base, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    dm_code: str = Field(default=None, nullable=True)
    gtin: str = Field(index=True, max_length=14, foreign_key="gtin.code")
    serial_number: str = Field(max_length=5)
    country_id: int = Field(foreign_key="country.id")
    verification_key: str = Field(max_length=4)
    verification_key_value: str | None = Field(default=None, max_length=44)
    is_long_format: bool = Field(default=False)
    upload_date: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc).strftime("%Y_%m_%d_%H%M%S"))
    entry_time: datetime | None = Field(default=None)
    export_time: datetime | None = Field(default=None)

    def to_public_data_matrix_code(self) -> DataMatrixCodePublic:
        return DataMatrixCodePublic(
            dm_code=self.dm_code,
            gtin=self.gtin,
            serial_number=self.serial_number,
            country=CountryEnum.from_code(
                self.country_id).label if self.country_id is not None else CountryEnum.UNKNOWN.label,
            is_long_format=self.is_long_format,
            verification_key=self.verification_key,
            verification_key_value=self.verification_key_value,
            upload_date=self.upload_date,
            entry_time=self.entry_time.strftime("%Y_%m_%d_%H%M%S") if self.entry_time is not None else None,
            export_time = self.export_time.strftime("%Y_%m_%d_%H%M%S") if self.export_time is not None else None,
        )


