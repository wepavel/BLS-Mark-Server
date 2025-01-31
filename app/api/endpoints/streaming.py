from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.ws_eventbus import send_broadcast_heartbeat_message, ws_eventbus, broadcast_msg
from app.core.logging import logger


router = APIRouter()

@router.websocket('/ws-status/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    try:
        async with ws_eventbus.connect_manager(websocket, client_id):
            while True:
                try:
                    data = await ws_eventbus.receive_message(websocket)
                    if data is None:
                        break

                    await ws_eventbus.handle_message(client_id, data)

                except WebSocketDisconnect:
                    # Клиент отключился, выходим из цикла
                    break
    except Exception as e:
        # Обработка других исключений
        logger.error(f'Error in WebSocket connection: {e!s}')
    finally:
        # Убедимся, что соединение закрыто и удалено из менеджера
        if client_id in ws_eventbus.active_connections:
            await ws_eventbus.disconnect(client_id)

