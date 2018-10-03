from distutils.spawn import find_executable


def debug_connect():
    connected = False
    while not connected:
        try:
            import socket
            server = socket.socket(proto=socket.IPPROTO_TCP)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', 3018))
            server.close()
            connected = True
        except OSError:
            import time
            time.sleep(1)

    import ptvsd
    ptvsd.enable_attach('SECRET', ('127.0.0.1', 3018))
    ptvsd.wait_for_attach()
    return True


def find_executables(file_names):
    for file_name in file_names:
        res = find_executable(file_name)
        if res:
            return res
    raise RuntimeError('Executables "%s" not found in path.' % file_names)
