import socket
import sys
import json

header='\n[== "CMake Server" ==[\n'
footer='\n]== "CMake Server" ==]\n'

class PipeReader:
    def __init__(self, pipe, source_dir, build_dir, gen):
        self.pipe = pipe
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.gen = gen
    
    def main(self):
        self.connect()
        self.handle_hello()
        self.loop()

    def connect(self):
        try:
            self.sock.connect(self.pipe)
            return True
        except socket.error, msg:
            print >>sys.stderr, msg
            return False

    def recv(self):
        data = ''
        while True:
            data += self.sock.recv(1024)
            if data.endswith(footer):
                return self.parse(data)

    def parse(self, data):
        data = data[len(header):-len(footer)] # Strip header footer
        return json.loads(data)

    def loop(self):
        try:
            data = self.recv()
        finally:
            print >>sys.stderr, 'closing socket'
            self.sock.close()
    
    def handle_hello(self):
        hello_data = self.recv()
        print >>sys.stderr, 'received "%s"' % hello_data


if __name__ == '__main__':
    pipereader = PipeReader(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    pipereader.main()
