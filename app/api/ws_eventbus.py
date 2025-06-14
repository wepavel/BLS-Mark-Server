import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from math import remainder
from typing import Any

from fastapi import WebSocket
from sqlmodel import Field, SQLModel

from app.core.config import settings
from app.core.logging import logger
from app.models import Device, DataMatrixCode, Applicator, DataMatrixCodePublic
import random
from app.core.utils import ping_device
from .deps import get_db
from app import crud
from app.core.app_state import app_state
from app.api.tcp_client import tcp_connection_manager, TCPDevice

class NotificationType(str, Enum):
    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'
    SUCCESS = 'SUCCESS'


class EventData(SQLModel, table=False):
    user_id: str
    message: str | dict[str, Any] | list[dict[str, Any]]
    notification_type: NotificationType = Field(default=NotificationType.SUCCESS)
    info: dict | None = None


class Event(SQLModel, table=False):
    name: str
    data: EventData

    def as_ws_dict(self) -> dict[str, str]:
        return {
            'event': self.name,
            'data': self.data.model_dump(),
        }



class WSConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        logger.info(f'Websocket accepted: session_id={client_id}')
        if client_id in self.active_connections:
            await self.active_connections[client_id].close()
        self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections.pop(client_id)
            await websocket.close()
        logger.info(f'Websocket closed: session_id={client_id}')

    @staticmethod
    async def receive_message(websocket: WebSocket):
        try:
            data = await websocket.receive_json()
            return data
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

    @staticmethod
    async def handle_message(client_id: str, message: dict):
        message_type = message.get('type')

        if message_type == 'heartbeat':
            await send_personal_heartbeat_message(client_id)
        else:
            logger.warning(f"Unknown message type: {message_type}")

    @staticmethod
    async def send_personal_message_static(websocket: WebSocket, event: Event):
        await websocket.send_json(event.as_ws_dict())

    async def send_personal_message(self, client_id: str, event: Event):
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(event.as_ws_dict())
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
        else:
            logger.warning(f"Attempted to send message to non-existent client: {client_id}")

    async def broadcast(self, event: Event):
        if not self.active_connections:
            return
        await asyncio.gather(
            *[connection.send_json(event.as_ws_dict()) for connection in self.active_connections.values()]
        )

    async def client_exists(self, client_id: str) -> bool:
        return client_id in self.active_connections

    @asynccontextmanager
    async def connect_manager(self, websocket: WebSocket, client_id: str):
        try:
            await self.connect(websocket, client_id)
            yield
        finally:
            await self.disconnect(client_id)


ws_eventbus = WSConnectionManager()

#--------------HEARTBEAT--------------
async def send_personal_heartbeat_message(client_id: str):
    # is_scanner = await ping_device(settings.SCANNER_ADRESS)
    # is_printer = await ping_device(settings.PRINTER_ADRESS)
    # is_plc = await ping_device(settings.PLC_ADRESS)
    # is_scanner = app_state.is_scanner
    # is_printer = app_state.is_printer
    # is_plc = app_state.is_plc
    # is_database = app_state.is_database
    is_scanner = True
    is_printer = True
    is_plc = True
    is_database = True

    # async for db in get_db():
    #     is_database = await crud.gtin.check_database_connection(db)

    devices = [
        Device(name='printer', ping=is_printer, heartbeat=is_printer),
        Device(name='scanner', ping=is_scanner, heartbeat=is_scanner),
        Device(name='plc', ping=is_plc, heartbeat=is_plc),
        Device(name='database', ping=is_database, heartbeat=is_database),
    ]

    device_dicts = [device.model_dump() for device in devices]

    broadcast_event = Event(
        name='heartbeat',
        data=EventData(user_id=client_id, message=device_dicts, notification_type=NotificationType.SUCCESS),
    )
    event = Event.model_validate_json(broadcast_event.model_dump_json())
    # await ws_eventbus.send_personal_message(client_id, event)
    await ws_eventbus.send_personal_message(client_id, event)


async def send_broadcast_heartbeat_message():
    devices = [
        Device(name='printer', ping=random.choice([True, False]), heartbeat=random.choice([True, False])),
        Device(name='scanner', ping=random.choice([True, False]), heartbeat=random.choice([True, False])),
        Device(name='plc', ping=random.choice([True, False]), heartbeat=random.choice([True, False])),
    ]

    # device_dicts = DeviceList(devices=devices)
    device_dicts = [device.model_dump() for device in devices]
    # devices_json = json.dumps(device_dicts)
    # return json.dumps(device_dicts, indent=2)

    broadcast_event = Event(
        name='heartbeat',
        data=EventData(user_id='broadcast', message=device_dicts, notification_type=NotificationType.SUCCESS),
    )
    event = Event.model_validate_json(broadcast_event.model_dump_json())
    await ws_eventbus.broadcast(event)



#--------------APPLICATOR STATE--------------
async def send_applicator_state():
    current_gtin = app_state.get_current_gtin()
    remainder = 0
    async for db in get_db():
        remainder = await crud.gtin.get_remainder(db=db, gtin=current_gtin.code) if current_gtin else 0

    applicator = Applicator(
        remainder=remainder,
        in_work=app_state.get_working(),
        current_product=current_gtin.name if current_gtin else None,
    )

    applicator_event = Event(
        name='applicator_state',
        data=EventData(user_id="-1", message=applicator.model_dump(), notification_type=NotificationType.SUCCESS),
    )
    event = Event.model_validate_json(applicator_event.model_dump_json())

    await ws_eventbus.broadcast(event)

async def periodic_send_applicator_state():
    while True:
        await send_applicator_state()
        await asyncio.sleep(3)  # Ждем 3 секунды перед следующим вызовом



#--------------CUSTOM MESSAGES--------------
async def broadcast_msg(
    msg: str,
    notification_type: NotificationType = NotificationType.INFO,
) -> None:
    event = Event(
        name='broadcast_message',
        data=EventData(user_id='broadcast', message=msg, notification_type=notification_type),
    )
    await ws_eventbus.broadcast(event)


async def broadcast_messagebox(
    msg: str,
    notification_type: NotificationType = NotificationType.INFO,
) -> None:
    event = Event(
        name='broadcast_messagebox',
        data=EventData(user_id='broadcast', message=msg, notification_type=notification_type),
    )
    await ws_eventbus.broadcast(event)
#--------------SEND DMCODE--------------
async def send_dmcode(client_id: str, dmcode: DataMatrixCode):
    dmcode_public = dmcode.to_public_data_matrix_code()

    # device_dicts = [device.model_dump() for device in devices]

    broadcast_event = Event(
        name='dmcode_stream',
        data=EventData(user_id=client_id, message=dmcode_public.model_dump(), notification_type=NotificationType.SUCCESS),
    )
    event = Event.model_validate_json(broadcast_event.model_dump_json())
    # await ws_eventbus.send_personal_message(client_id, event)
    await ws_eventbus.broadcast(event)

async def broadcast_dmcode(dmcode: DataMatrixCode):
    dmcode_public = dmcode.to_public_data_matrix_code()

    # device_dicts = [device.model_dump() for device in devices]

    broadcast_event = Event(
        name='dmcode_stream',
        data=EventData(user_id="-1", message=dmcode_public.model_dump(), notification_type=NotificationType.SUCCESS),
    )
    event = Event.model_validate_json(broadcast_event.model_dump_json())
    # await ws_eventbus.send_personal_message(client_id, event)
    # await ws_eventbus.send_personal_message(client_id, event)
    await ws_eventbus.broadcast(broadcast_event)
