from sqlmodel import Field
from app.db.base_class import Base


class GTIN(Base, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    code: str = Field(index=True, unique=True, max_length=14)
    name: str = Field(max_length=255)
