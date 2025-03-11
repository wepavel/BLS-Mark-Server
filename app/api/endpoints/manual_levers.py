from fastapi import APIRouter, Path
from app.api.ws_eventbus import send_broadcast_heartbeat_message
from app.api.ws_eventbus import ws_eventbus
from app.api.ws_eventbus import broadcast_msg
from app.api.ws_eventbus import send_personal_heartbeat_message
from app.api.ws_eventbus import send_dmcode as ws_send_dmcode
from app.models import DataMatrixCodePublic
from app.models.dmcode import DataMatrixCode, DataMatrixCodeCreate
from app.core.exceptions import EXC, ErrorCode
from datetime import datetime, timezone

router = APIRouter()

@router.post('/send-broadcast-heartbeat-message')
async def send_broadcast_heartbeat_message() -> None:
    await send_broadcast_heartbeat_message()

@router.post('/send-personal-heartbeat-message/{client_id:path}')
async def send_personal_heartbeat_message(client_id: str) -> None:
    await send_personal_heartbeat_message(client_id)

@router.post('/send-broadcast-message/{msg:path}')
async def broadcast_message_msg(msg: str) -> None:
    await broadcast_msg(msg)

@router.post('/send-dmcode/{client_id}/{entry}/{dm_code:path}')
async def send_dmcode(
        client_id: str,
        entry: bool,
        dm_code: str
) -> DataMatrixCodePublic:
    create_dm = DataMatrixCodeCreate(dm_code=dm_code)
    dm_attrs = DataMatrixCode.from_data_matrix_code_create(data=create_dm)

    if dm_attrs is None:
        raise EXC(ErrorCode.DMCodeValidationError)

    if entry:
        dm_attrs.entry_time = datetime.now()

    await ws_send_dmcode(client_id, dm_attrs)

    return dm_attrs.to_public_data_matrix_code()
