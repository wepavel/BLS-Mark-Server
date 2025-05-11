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
from app.db.init_db import init_db, create_database
from app.db.session import SessionLocal
from app.core.license_manager import LicenseManager
from app.core.logging import logger
from app.api.ws_eventbus import periodic_send_applicator_state
from app.api.tcp_client import tcp_connection_manager
from app.core.app_state import app_state
from app.api.tcp_server import TCPServer
from app.api.scanner_tcp_server import ScannerTCPServer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_database()
    db = SessionLocal()
    await init_db(db)
    task = asyncio.create_task(periodic_send_applicator_state())
    # app_state_task = asyncio.create_task(app_state.initialize_buffer())
    tcp_server = TCPServer()
    task2 = asyncio.create_task(tcp_server.start_server())
    scanner_tcp_server = ScannerTCPServer()
    task3 = asyncio.create_task(scanner_tcp_server.start_server())

    task4 = asyncio.create_task(app_state.device_heartbeat())

    app.state.background_tasks = [task, task2, task3, task4]



    yield
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
    await tcp_connection_manager.close_all()
    # await event_bus.close_all_connections()
    # Отменяем все фоновые задачи при завершении работы приложения
    for task in app.state.background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

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

def check_license() -> bool:
    # serial = LicenseManager.get_motherboard_serial()
    # current_hash =  LicenseManager.create_augmented_hash(serial,  LicenseManager._default_salt)
    license_manager = LicenseManager()
    valid_license =  license_manager.check_license(LicenseManager._default_salt)
    if not valid_license:
        logger.error('License validation failed: stored key does not match the expected key.')
        return False
    else:
        logger.info('License validated successfully: stored hash matches the current hash.')
        return True


def main() -> None:
    if not check_license():
        return

    uvicorn.run(
        app,
        host=str(settings.HOST),
        port=settings.PORT,
        log_config='log_config.json',
    )  # ,log_config='./app/log_config.json'


if __name__ == '__main__':
    main()

