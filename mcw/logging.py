import logging

logger_fmt_with_func = logging.Formatter(
    '%(asctime)s - %(name)s'
    '-%(funcName)s()'
    ': %(message)s'
)

logger_fmt = logging.Formatter(
    '%(asctime)s - %(name)s'
    ': %(message)s'
)

class ServerLogHandler(logging.Handler):
    def __init__(self, server):
        super().__init__()
        self.server = server

    def emit(self, record):
        log_entry = self.format(record)
        if self.server.connected:
            self.server.send_message(log_entry, log=False)
