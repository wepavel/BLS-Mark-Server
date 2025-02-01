from fastapi import APIRouter, Path
from app.api.ws_eventbus import send_broadcast_heartbeat_message
from app.api.ws_eventbus import ws_eventbus
from app.api.ws_eventbus import broadcast_msg
from app.api.ws_eventbus import send_personal_heartbeat_message
from app.api.ws_eventbus import send_dmcode
from app.models import DataMatrixCodePublic
from app.core.utils import validate_data_matrix
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

@router.post('/send-dmcode/{client_id:path}/{code:path}/{entry:path}')
async def send(client_id: str, entry: bool, code: str = Path(..., description="Encoded string to validate")) -> DataMatrixCodePublic:
    dmcode = validate_data_matrix(code)
    if dmcode is None:
        raise EXC(ErrorCode.DMCodeValidationError)

    if entry:
        dmcode.entry_time = datetime.now(tz=timezone.utc)

    await send_dmcode(client_id, dmcode)

    return dmcode.to_public_data_matrix_code()
