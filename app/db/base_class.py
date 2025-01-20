from typing import Any

from sqlmodel import SQLModel


# @as_declarative()
class Base(SQLModel):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @classmethod
    @property
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
