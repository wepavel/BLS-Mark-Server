from sqlmodel import Field, SQLModel


class Device(SQLModel, table=False):
    name: str | None = Field(unique=True, index=True, nullable=False, default='Device name')
    ping: bool | None = Field(default=False)
    heartbeat: bool | None = Field(default=False)


class DeviceList(SQLModel):
    devices: list[Device]
