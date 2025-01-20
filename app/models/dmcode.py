import time
from uuid import UUID

from sqlmodel import Field, SQLModel


from app.db.base_class import Base

# NEW_UUID = lambda: str(uuid.uuid4())


class DMCode(Base, table=True):
    id: UUID | None = Field(primary_key=True, index=True, unique=True, default=ULID.from_timestamp(time.time()))
    gtin: str | None = Field(unique=True, index=True, nullable=False, foreign_key='gtin.id')
    login: str | None = Field(unique=True, index=True, nullable=False)
    country_id: int | None = Field(default=1, foreign_key='country.id')
