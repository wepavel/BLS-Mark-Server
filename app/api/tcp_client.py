# import asyncio
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import logging
# from typing import Dict, Optional
# from app.core.logging import logger
# from app.core.config import settings
# from enum import Enum
#
# app = FastAPI()
#
# class Message(BaseModel):
#     text: str
#     device_id: str
#
# class TCPClient:
#     def __init__(self, host: str, port: int, device_id: str, reconnect_interval: int = 5, send_timeout: float = 0.5):
#         self.host = host
#         self.port = port
#         self.device_id = device_id
#         self.reader: Optional[asyncio.StreamReader] = None
#         self.writer: Optional[asyncio.StreamWriter] = None
#         self.lock = asyncio.Lock()
#         self.reconnect_interval = reconnect_interval
#         self.send_timeout = send_timeout
#         self.is_connected = False
#         self.reconnect_task: Optional[asyncio.Task] = None
#         self.last_activity = asyncio.get_event_loop().time()
#
#     async def connect(self):
#         while not self.is_connected:
#             try:
#                 self.reader, self.writer = await asyncio.wait_for(
#                     asyncio.open_connection(self.host, self.port),
#                     timeout=self.send_timeout
#                 )
#                 self.is_connected = True
#                 self.last_activity = asyncio.get_event_loop().time()
#                 logger.info(f'Подключено к {self.host}:{self.port} (Device ID: {self.device_id})')
#                 if self.reconnect_task:
#                     self.reconnect_task.cancel()
#                 self.reconnect_task = asyncio.create_task(self.keep_alive())
#             except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
#                 logger.error(f'Не удалось подключиться к {self.device_id}: {e}')
#                 self.is_connected = False
#                 await asyncio.sleep(self.reconnect_interval)
#
#     async def keep_alive(self):
#         while True:
#             await asyncio.sleep(5)  # Проверка каждые 5 секунд
#             if not self.is_connected:
#                 await self.connect()
#             else:
#                 await self.check_connection()
#
#     async def send_message(self, message: str):
#         async with self.lock:
#             if not self.is_connected:
#                 await self.connect()
#             try:
#                 message = message.replace('<GS>', chr(29)).replace('<FNC1>', chr(232))
#                 self.writer.write(message.encode('utf-8'))
#                 await asyncio.wait_for(self.writer.drain(), timeout=self.send_timeout)
#                 self.last_activity = asyncio.get_event_loop().time()
#                 logger.info(f'Отправлено на {self.device_id}: {message}')
#                 return True
#             except Exception as e:
#                 logger.error(f'Произошла ошибка при отправке на {self.device_id}: {e}')
#                 self.is_connected = False
#                 return False
#
#     async def check_connection(self) -> bool:
#         if not self.writer:
#             self.is_connected = False
#             return False
#         try:
#             self.writer.write(b'')
#             await asyncio.wait_for(self.writer.drain(), timeout=self.send_timeout)
#             self.last_activity = asyncio.get_event_loop().time()
#             return True
#         except Exception as e:
#             logger.error(f"Ошибка при проверке соединения для {self.device_id}: {e}")
#             self.is_connected = False
#             self.writer = None
#             self.reader = None
#             return False
#
#     async def close(self):
#         self.is_connected = False
#         if self.writer:
#             try:
#                 self.writer.close()
#                 await asyncio.wait_for(self.writer.wait_closed(), timeout=self.send_timeout)
#             except Exception as e:
#                 logger.error(f"Ошибка при закрытии соединения для {self.device_id}: {e}")
#         if self.reconnect_task:
#             self.reconnect_task.cancel()
#         self.writer = None
#         self.reader = None
#         logger.info(f'Соединение закрыто для {self.device_id}.')
#
#
# class TCPDevice(Enum):
#     PRINTER = TCPClient(settings.PRINTER_ADRESS, settings.PRINTER_PORT, 'printer')
#     # PLC = TCPClient()
#
# class ConnectionManager:
#     def __init__(self):
#         self.connections: Dict[TCPDevice, TCPClient] = {}
#         for device in TCPDevice:
#             self.connections[device] = device.value
#             asyncio.run(self.connections[device].connect())
#
#     async def get_connection(self, device: TCPDevice) -> TCPClient:
#         if device not in self.connections:
#             logger.error(f'Could not find connection for device_id: {device}')
#             # self.connections[device_id] = TCPClient(host, port, device_id)
#             # await self.connections[device_id].connect()
#         return self.connections[device]
#
#     async def check_connection_status(self, device: TCPDevice) -> bool:
#         if device not in self.connections:
#             return False
#         return await self.connections[device].check_connection()
#
#     async def close_all(self):
#         for connection in self.connections.values():
#             await connection.close()
#         logger.info('All tcp connections has been closed')
#
# # Создаем глобальный менеджер соединений
# tcp_connection_manager = ConnectionManager()
#
# # @app.post("/send_message")
# # async def send_message(message: Message):
# #     client = await tcp_connection_manager.get_connection(message.device_id, '169.254.36.50', 8031)
# #     success = await client.send_message(message.text)
# #     if success:
# #         return {"status": "success", "message": f"Сообщение успешно отправлено на устройство {message.device_id}"}
# #     else:
# #         raise HTTPException(status_code=500, detail=f"Не удалось отправить сообщение на устройство {message.device_id}")
#
# # @app.on_event("startup")
# # async def startup_event():
# #     # Здесь можно инициализировать начальные соединения, если это необходимо
# #     pass
# #
# # @app.on_event("shutdown")
# # async def shutdown_event():
# #     await tcp_connection_manager.close_all()
#


import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from app.core.logging import logger
from app.core.config import settings
from enum import Enum
import struct
import socket
import time

app = FastAPI()


class Message(BaseModel):
    text: str
    device_id: str


class TCPClient:
    def __init__(self, host: str, port: int, device_id: str, timeout: float = 0.1):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.timeout = timeout
        self.writer: Optional[asyncio.StreamWriter] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.lock = asyncio.Lock()
    #
    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            logger.info(f'Подключено к {self.host}:{self.port} (Device ID: {self.device_id})')
        except asyncio.TimeoutError:
            logger.error(f'Таймаут при подключении к {self.device_id}')
        except Exception as e:
            logger.error(f'Ошибка при подключении к {self.device_id}: {e}')

    # async def connect(self, buf_size: int):
    #     self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
    #     sock = self.writer.get_extra_info('socket')
    #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buf_size)

    async def send_message(self, message: str) -> bool:
        if not self.writer:
            await self.connect()
        if not self.writer:
            return False

        try:
            message = message.replace('<GS>', chr(29)).replace('<FNC1>', chr(232))
            # length_prefix = struct.pack('>I', len(message))
            # self.writer.write(message.encode('utf-8')+length_prefix)

            self.writer.write(message.encode('utf-8'))
            # await self.writer.drain()

            # encoded_message = message.encode('utf-8')
            # length_prefix = struct.pack('>I', len(message))
            # self.writer.write(length_prefix + message)
            # await self.writer.drain()
            # init = time.time()
            await asyncio.wait_for(self.writer.drain(), timeout=self.timeout)
            # await asyncio.sleep(0.1)
            # print(f'Wait for clear buffer: {time.time() - init}')
            logger.info(f'Отправлено на {self.device_id}: {message}')
            # self.writer.close()
            # await self.writer.wait_closed()
            return True
        except asyncio.TimeoutError:
            logger.error(f'Таймаут при отправке на {self.device_id}')
        except Exception as e:
            logger.error(f'Ошибка при отправке на {self.device_id}: {e}')

        self.writer = None
        self.reader = None
        return False

    # async def send_message(self, message: str) -> bool:
    #     if not self.writer:
    #         await self.connect()
    #     if not self.writer:
    #         return False
    #
    #     try:
    #         message = message.replace('<GS>', chr(29)).replace('<FNC1>', chr(232))
    #         encoded_message = message.encode('utf-8')
    #         length_prefix = struct.pack('>I', len(encoded_message))
    #
    #         # Начинаем группировку операций записи
    #         self.writer.transport.cork()
    #
    #         try:
    #             self.writer.write(length_prefix)
    #             self.writer.write(encoded_message)
    #         finally:
    #             # Завершаем группировку и отправляем данные
    #             self.writer.transport.uncork()
    #
    #         # Ожидаем отправки данных с таймаутом
    #         await asyncio.wait_for(self.writer.drain(), timeout=self.timeout)
    #
    #         logger.info(f'Отправлено на {self.device_id}: {message}')
    #         return True
    #     except asyncio.TimeoutError:
    #         logger.error(f'Таймаут при отправке на {self.device_id}')
    #     except Exception as e:
    #         logger.error(f'Ошибка при отправке на {self.device_id}: {e}')
    #
    #     self.writer = None
    #     self.reader = None
    #     return False

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.writer = None
        self.reader = None
        logger.info(f'Соединение закрыто для {self.device_id}')


class TCPDevice(Enum):
    PRINTER = TCPClient(settings.PRINTER_ADRESS, settings.PRINTER_PORT, 'printer')


class ConnectionManager:
    def __init__(self):
        self.connections: Dict[TCPDevice, TCPClient] = {device: device.value for device in TCPDevice}

    async def get_connection(self, device: TCPDevice) -> TCPClient:
        return self.connections[device]

    async def close_all(self):
        for connection in self.connections.values():
            await connection.close()
        logger.info('Все TCP соединения закрыты')


tcp_connection_manager = ConnectionManager()

