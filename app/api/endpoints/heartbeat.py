from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.api.ws_eventbus import send_broadcast_heartbeat_message, ws_eventbus, broadcast_msg
from app.core.config import settings
from app.core.exceptions import EXC, ErrorCode
from app.core.logging import logger
from app.models.device import Device

router = APIRouter()


@router.get('/device-states/{key:path}')
async def download_file(key: int) -> Device:
    if key == 0:
        raise EXC(ErrorCode.CoreFileUploadingError, details={'reason': 'Test'})

    logger.info('Hello world from endpoint')
    device = Device()
    # device.name = 'Test'
    # device.heartbeat = True
    # device.ping = True

    return device


@router.get('/service-heartbeat/{ping}')
async def ping(ping: str) -> PlainTextResponse:
    if ping == 'ping':
        return PlainTextResponse('pong')

    raise EXC(ErrorCode.InternalError)


@router.post('/broadcast-heartbeat-message')
async def broadcast_message() -> None:
    await send_broadcast_heartbeat_message()

@router.post('/broadcast-message/{msg}')
async def broadcast_message(msg: str) -> None:
    await broadcast_msg(msg)

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


def html_ws(client_id: str):
    p0 = """<!DOCTYPE html>
<html>
    <head>
        <title>Test</title>
    </head>
    <style>
    html * {
      font-size: 12px !important;
      color: #0f0 !important;
      font-family: Andale Mono !important;
      background-color: #000;
    }
    </style>
    """
    p2 = f"""
    <body>
        <h1>WebSocket connection</h1>
        <script>
            let socket;

            function connect() {{
                socket = new WebSocket('ws://{settings.HOST}:{settings.PORT}/api/v1/heartbeat/ws-status/{client_id}');
    """
    p3 = """
                socket.onopen = function(e) {
                    log("Connection established");
                };

                socket.onmessage = function(event) {
                    log("Received data: " + event.data);
                };

                socket.onerror = function(error) {
                    log("WebSocket Error: " + error.message);
                };

                socket.onclose = function(event) {
                    if (event.wasClean) {
                        log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
                    } else {
                        log('Connection died');
                    }
                };
            }

            function stop() {
                if (socket) {
                    socket.close();
                    log("Disconnected");
                }
            }

            function log(msg) {
                let time = new Date()
                let timeval = time.getHours() + ':' + time.getMinutes() + ':' + time.getSeconds() + '  ';
                logElem.innerHTML = timeval + msg + "<br>" + logElem.innerHTML;
            }

            // Автоматически подключаемся при загрузке страницы
            connect();
        </script>

        <button onclick="stop()">Stop</button>
        <button onclick="connect()">Reconnect</button>
        <div id="logElem" style="margin: 6px 0"></div>

    </body>
</html>
"""
    return p0 + p2 + p3


@router.get('/get_heartbeat_ws/{client_id}')
async def get_ws(client_id: str):
    return HTMLResponse(html_ws(client_id))
