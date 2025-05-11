# tcp_server.py
import asyncio
from app.core.logging import logger
from app.core.config import settings
from app.core.app_state import app_state
import time

class TCPServer:
    def __init__(self):
        self.timer_13 = time.time()
        self.timer_11 = time.time()
        self.timer_13_delay = 0.1
        self.timer_11_delay = 0.3
        self.resp_buffer: bool = False

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f'Connected by {addr}')

        while True:
            try:
                data = await reader.read(1)
                if not data:
                    break

                # logger.info('-' * 25)
                # logger.info(f'Received data: {data}')
                # logger.info(f'Received data (str): {data.decode("utf-8", errors="replace")}')
                # logger.info(f'Received data (hex): {data.hex()}')
                # logger.info(f'Received data (int): {int.from_bytes(data, byteorder="big")}')
                # logger.info('-' * 25)

                try:
                    value = int.from_bytes(data, byteorder='little')
                    # result = value + 2
                    result = 1
                    # print(value)

                    if value == 0:
                        # PLC is not working
                        pass
                    elif value > 0 and value <= 9:
                        # print('PLC is working')
                        # PLC is working
                        result = 6 if app_state.get_working() else 5
                    elif value == 10:
                        # Printer not need to a new code
                        # print('Recieve 10')
                        pass
                    elif value == 11:
                        if not ((time.time() - self.timer_11) < self.timer_11_delay):
                            # Request for new code on printer
                            print('Rotating dmcode')
                            await asyncio.sleep(0.05)
                            await app_state.rotate_dmcode()
                            self.timer_11 = time.time()
                    elif value == 12:
                        # Тары нету
                        # print('Тары нету')
                        pass
                    elif value == 13:
                        if not ((time.time()-self.timer_13)<self.timer_13_delay):

                            init = time.time()
                            print(f'Recieve 13')
                            result = await app_state.handle_dmcode_confirmation()
                            result = 13 if result else 12
                            self.resp_buffer = result
                            print(f'Recieve 13, end {result}: {time.time()-init}')
                            self.timer_13 = time.time()
                        else:
                            print(f'Double recieve 13')
                            result = self.resp_buffer
                            self.resp_buffer = False
                            print(f'Recieve 13, end {result}')

                    response_bytes = result.to_bytes((result.bit_length() + 7) // 8, byteorder='little')
                    # logger.info(f'Receive: {value}')
                    # result = value + 2
                    # response_bytes = result.to_bytes((result.bit_length() + 7) // 8, byteorder='little')

                    # logger.info(f'Server response: {response_bytes}')
                    # logger.info(f'Server response (str): {response_bytes.decode("utf-8", errors="replace")}')
                    # logger.info(f'Server response (hex): {response_bytes.hex()}')
                    # logger.info(f'Server response (int): {int.from_bytes(response_bytes, byteorder="big")}')
                    #
                    writer.write(response_bytes)
                    await writer.drain()
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
            except Exception as e:
                logger.error(f'Error handling client {addr}: {e}')
                break

        try:
            writer.close()
            await writer.wait_closed()
            logger.info(f'Disconnected from {addr}')
        except:
            logger.info(f'Disconnected from {addr} with error')

    async def start_server(self, host=settings.HOST, port=settings.TCP_PORT):
        server = await asyncio.start_server(self.handle_client, host, port)
        addr = server.sockets[0].getsockname()
        logger.info(f'Serving PLC TCP server on {addr}')

        async with server:
            await server.serve_forever()