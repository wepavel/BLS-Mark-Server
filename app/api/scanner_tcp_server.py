# tcp_server.py
import asyncio
from app.core.logging import logger
from app.core.config import settings
from app.core.app_state import app_state
from app import models
import time

class ScannerTCPServer:
    def __init__(self):
        pass

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f'Connected by {addr}')

        while True:
            try:
                data = await reader.read(1024)
                if not data:
                    break

                # logger.info('-' * 25)
                # logger.info(f'Received data: {data}')
                print(f'Received data (str): {data.decode("utf-8", errors="replace")}')

                try:
                    data = data.decode("utf-8", errors="replace").strip()
                    dmcode = models.DataMatrixCodeCreate(dm_code=data)
                    task_1 = asyncio.create_task(app_state.handle_dmcode(dmcode_create=dmcode))

                except ValueError:
                    error_msg = b'Invalid input. Please send an integer.'
                    writer.write(error_msg)
                    await writer.drain()
                    logger.info(f'Error response: {error_msg}')
                    logger.info(f'Error response (str): {error_msg.decode("utf-8")}')
                    logger.info(f'Error response (hex): {error_msg.hex()}')

                # logger.info('-' * 50)

            except asyncio.CancelledError:
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error handling client {addr}: {e}')
                break

        # writer.close()
        # await writer.wait_closed()
        logger.info(f'Disconnected from {addr}')

    async def start_server(self, host=settings.HOST, port=settings.SCANNER_TCP_PORT):
        server = await asyncio.start_server(self.handle_client, host, port)
        addr = server.sockets[0].getsockname()
        logger.info(f'Serving Scanner TCP server on {addr}')

        async with server:
            await server.serve_forever()