import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from app.api import api_router

# from app.api.sse_eventbus import event_bus
from app.core.config import settings
from app.core.exceptions import exception_handler

# from app.core.logging import UvicornAccessLogFormatter, UvicornCommonLogFormatter
from app.core.openapi import custom_openapi
from starlette.middleware.cors import CORSMiddleware

class Message(BaseModel):
    content: str


class TCPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        self.clients.add(writer)
        print(f'New connection from {addr}')

        try:
            while True:
                data = await reader.read(100)
                if not data:
                    break
                message = data.decode()
                print(f'Received {message} from {addr}')

                # Broadcast message to all clients
                for client in self.clients:
                    if client != writer:
                        client.write(data)
                        await client.drain()
        finally:
            self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()
            print(f'Connection closed for {addr}')

    async def run(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)

        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # server = TCPServer('127.0.0.1', 8888)
    # print('Start TCP Server')
    # await asyncio.create_task(server.run())
    #
    #     level = settings.LOG_LEVEL
    #
    #     uvicorn_logger = logging.getLogger('uvicorn')
    #     uvicorn_logger.setLevel(level)
    #     uvicorn_logger.handlers[0].setFormatter(UvicornCommonLogFormatter())
    #
    #     access_logger = logging.getLogger('uvicorn.access')
    #     access_logger.setLevel(level)
    #     access_logger.handlers[0].setFormatter(UvicornAccessLogFormatter())
    #
    yield

    # await event_bus.close_all_connections()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    # openapi_url=f'{settings.API_V1_STR}/openapi.json',
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
    # root_path=settings.API_V1_STR
    # prefix=settings.API_V1_STR,
    docs_url='/docs',
    # openapi_url="/openapi.json",
    # static_url="/static"
)


custom_openapi(app)
exception_handler(app)
# app.add_middleware(RequestIDMiddleware)

# for origin in settings.BACKEND_CORS_ORIGINS: print(str(origin).rstrip('/'))


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == '__main__':
    uvicorn.run(
        app,
        host=str(settings.HOST),
        port=settings.PORT,
        log_config='./log_config.json',
    )  # ,log_config='./app/log_config.json'
