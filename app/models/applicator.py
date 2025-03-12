from sqlmodel import Field, SQLModel


class Applicator(SQLModel, table=False):
    current_product: str | None = Field(default=None)
    remainder: int | None = Field(default=0)
    in_work: bool | None = Field(default=False)



