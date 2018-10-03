import logging


class ServerLogHandler(logging.Handler):
    def __init__(self, server):
        super().__init__()
        self.server = server

    def emit(self, record):
        log_entry = self.format(record)
        if self.server.connected:
            self.server.send_message(log_entry, log=False)
