from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.core.config import settings

router = APIRouter()

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
                socket = new WebSocket('ws://127.0.0.1:{settings.PORT}/api/v1/streaming/ws-status/{client_id}');
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


@router.get('/get_ws/{client_id}')
async def get_ws(client_id: str):
    return HTMLResponse(html_ws(client_id))
