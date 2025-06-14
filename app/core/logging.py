import inspect
import logging


class ContextFilter(logging.Filter):
    def filter(self, record):
        frame = inspect.currentframe()
        while frame:
            co = frame.f_code
            filename = co.co_filename
            func_name = co.co_name
            if 'logging' not in filename:  # Исключаем логирующий модуль
                break
            frame = frame.f_back

        record.filename = filename
        record.funcName = func_name
        return True


class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

    def isatty(self) -> bool:
        return False


logging.basicConfig(
    # filename="logs/vc_service.log",
    # format='%(asctime)s %(message)s',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(funcName)s]',
    # filemode='w'
)

class EndpointFilter(logging.Filter):
    def __init__(self, path):
        self.path = path

    def filter(self, record):
        return record.args and len(record.args) >= 3 and record.args[2] != self.path

# Disable logging for ping
logging.getLogger("uvicorn.access").addFilter(EndpointFilter("/api/v1/heartbeat/service-heartbeat/ping"))

logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)
context_filter = ContextFilter()
logger.addFilter(context_filter)
logger.info('Init')
