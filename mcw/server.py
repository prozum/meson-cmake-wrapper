import os
import json
import socket

SERVER_HEADER = b'\n[== "CMake Server" ==[\n'
SERVER_FOOTER = b'\n]== "CMake Server" ==]\n'


class ServerWrapper:
    """
    Class that emulates CMake Server Mode.
    """

    def __init__(self, cmake):
        self.cmake = cmake
        self.meson = cmake.meson
        self.logger = None
        self.pipe = None
        self.connected = False
        self.requests = []
        self.protocol_version = (1, 1)
        self.cookies = {}

    def log(self, msg):
        if isinstance(msg, Exception):
            self.logger.info(msg, exc_info=msg)
        else:
            self.logger.info(msg)

    def run(self, args):
        try:
            self.connect(args)
            self.connected = True
            self.handle_hello()
            self.handle_handshake()
            self.log('running on "%s"' % self.pipe)
            while 1:
                request = self.recv()
                if not request:
                    self.connected = False
                    break

                if not hasattr(self, 'handle_' + request['type'].lower()):
                    self.log('unhandled request: "%s"' % request)
                    break
                getattr(self, 'handle_' + request['type'].lower())(request)
        except BrokenPipeError:
            self.connected = False
            self.log('lost connection to client')
        finally:
            self.log('closing connection')
            self.cleanup()

    def connect(self, args):
        raise NotImplementedError()

    def cleanup(self):
        raise NotImplementedError()

    def read(self, size):
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()

    def recv(self):
        data = b''
        while True:
            if any(self.requests):
                return self.requests.pop(0)

            new_data = self.read(1024)
            if not new_data:
                return None
            data += new_data
            if data.endswith(SERVER_FOOTER):
                self.parse_recv(data)

    def send(self, response, log=True):
        if 'inReplyTo' in response:
            if response['inReplyTo'] in self.cookies:
                response['cookie'] = self.cookies[response['inReplyTo']]
            if log:
                self.log('%s (%s) "%s"' % (response['inReplyTo'], response['type'], response))
        elif log:
            self.log(response)

        response = SERVER_HEADER + json.dumps(response).encode('utf-8') + SERVER_FOOTER
        self.write(response)

    def parse_recv(self, data):
        requests = data.split(SERVER_FOOTER + SERVER_HEADER)
        requests[0] = requests[0][len(SERVER_HEADER):]
        requests[-1] = requests[-1][:-len(SERVER_FOOTER)]

        for request in requests:
            request = json.loads(request)
            if 'cookie' in request:
                self.cookies[request['type']] = request['cookie']
            self.log('received (%s) "%s"' % (request['type'], request))
            self.requests.append(request)

    def send_reply(self, reply_to, log=True):
        response = {
            'inReplyTo': reply_to,
            'type': 'reply'
        }
        self.send(response, log)

    def send_message(self, msg, reply_to=None, log=True):
        response = {
            'type': 'message',
            'message': msg,
        }
        if reply_to:
            response['inReplyTo'] = reply_to

        self.send(response, log)

    def send_progress(self, reply_to, progress_cur, progress_max=1000, progress_min=0, msg='', log=True):
        response = {
            'inReplyTo': reply_to,
            'type': 'progress',
            'progressCurrent': progress_cur,
            'progressMaximum': progress_max,
            'progressMessage': progress_min,
            'progressMinimum': 0,
        }
        self.send(response, log)

    def handle_hello(self):
        response = {
            'supportedProtocolVersions': [{
                'isExperimental': True,
                'major': self.protocol_version[0],
                'minor': self.protocol_version[1]
            }],
            'type': 'hello'
        }
        self.send(response)

    def handle_handshake(self):
        request = self.recv()
        if not request:
            return
        self.cmake.set_build_dir(request['buildDirectory'])
        if 'generator' in request:
            self.cmake.set_generator(request['generator'])
        if 'sourceDirectory' in request:
            self.cmake.set_source_dir(request['sourceDirectory'])

        self.cmake.load_cache_entries()

        self.send_reply('handshake')

    def handle_configure(self, request):
        for entry in request['cacheArguments']:
            if entry.startswith('-D'):
                self.cmake.parse_cache_entry(entry)

        self.send_progress('configure', 1000, msg='Configuring')
        self.send_message('Configuring done', 'configure')
        self.send_reply('configure')

    def handle_compute(self, request):
        self.cmake.generate_cmd()

        self.send_progress('compute', 1000, msg='Generating')
        self.send_message('Generating done', 'compute')
        self.send_reply('compute')

    def handle_globalsettings(self, request):
        response = {
            'inReplyTo': 'globalSettings',
            'type': 'reply',
            'capabilities': {
                'generators': [
                    {
                        'name': 'Ninja',
                        'platformSupport': False,
                        'toolsetSupport': False,
                        'extraGenerators': [
                            'CodeBlocks',
                        ]
                    },
                    {
                        'name': 'Unix Makefiles',
                        'platformSupport': False,
                        'toolsetSupport': False,
                        'extraGenerators': [
                            "CodeBlocks",
                        ],
                    },
                ],
                'serverMode': True,
                'version': {
                    'isDirty': False,
                    'major': self.cmake.version[0],
                    'minor': self.cmake.version[1],
                    'patch': self.cmake.version[2],
                    'string': '.'.join(map(str, self.cmake.version)),
                    'suffix': '',
                }
            },
            'buildDirectory': self.cmake.build_dir,
            'sourceDirectory': self.cmake.source_dir,
            'generator': self.cmake.generator,
            'checkSystemVars': False,
            'debugOutput': False,
            'extraGenerator': '',
            'trace': False,
            'traceExpand': False,
            'warnUninitialized': False,
            'warnUnused': False,
            'warnUnusedCli': True
        }
        self.send(response)

    def handle_cmakeinputs(self, request):
        response = {
            'inReplyTo': 'cmakeInputs',
            'type': 'reply',
            'buildFiles': [
                {
                    'sources': 'CMakeLists.txt',
                    'isCMake': False,
                    'isTemporary': False
                }
            ],
            'cmakeRootDirectory': '/usr/share/cmake',
            'sourceDirectory': self.cmake.source_dir,
        }
        self.send(response)

    def get_cache_entries(self):
        cache_entries = []
        for key, val in self.cmake.cache_entries.items():
            cache_entries.append({
                'key': key.upper(),
                'value': val[0],
                'type': val[1],
                'properties': {}
            })
        return cache_entries

    def handle_cache(self, request):
        response = {
            'inReplyTo': 'cache',
            'type': 'reply',
            'cache': self.get_cache_entries(),
        }
        self.send(response)

    def get_include_paths(self, target):
        include_paths = []
        for include_path in self.meson.get_include_directories(target, False):
            include_paths.append({'path': include_path, 'isSystem': False})
        for include_path in self.meson.get_default_include_directories(target):
            include_paths.append({'path': include_path, 'isSystem': True})
        return include_paths

    def get_file_groups(self, target):
        sources = []
        for target_file in self.meson.get_target_files(target):
            sources.append(os.path.relpath(target_file, os.path.dirname(target['filename'])))
        file_group = {
            'isGenerated': False,
            'sources': sources,
            'compileFlags': ' '.join(self.meson.get_flags(target)),
            'defines': [define[2:] for define in self.meson.get_defines(target)],
            'includePath': self.get_include_paths(target),
            'language': 'CXX' if self.meson.get_compiler(target).endswith('++') else 'C'
        }

        meson_group = {
            'isGenerated': False,
            'sources': ['meson.build']
        }

        return [file_group, meson_group]

    def get_project(self):
        project = {
            'name': self.meson.get_project_info()['name'],
            'buildDirectory': self.cmake.build_dir,
            'sourceDirectory': self.cmake.source_dir,
            'targets': []
        }

        type_mapper = {
            'executable': 'EXECUTABLE',
            'static library': 'STATIC_LIBRARY',
            'shared library': 'SHARED_LIBRARY',
            'custom': 'UTILITY'
        }

        for mtarget in self.meson.get_targets():
            target = {}
            target['name'] = mtarget['name']
            target['fullName'] = mtarget['name']
            target['artifacts'] = [
                os.path.join(self.meson.build_dir, mtarget['filename'])
            ]
            target['buildDirectory'] = os.path.join(self.cmake.build_dir, os.path.dirname(mtarget['filename']))
            target['sourceDirectory'] = os.path.join(self.cmake.source_dir, os.path.dirname(mtarget['filename']))
            target['type'] = type_mapper[mtarget['type']]
            target['fileGroups'] = self.get_file_groups(mtarget)
            project['targets'].append(target)
        return project

    def handle_codemodel(self, request):
        response = {
            'inReplyTo': 'codemodel',
            'type': 'reply',
            'configurations': [
                {
                    'name': self.cmake.build_type,
                    'projects': [
                        self.get_project(),
                    ]
                }
            ],
        }
        self.send(response)


class UnixSocketServer(ServerWrapper):
    def __init__(self, cmake):
        super().__init__(cmake)
        self.sock = None
        self.conn = None

    def connect(self, args):
        for arg in args:
            if arg.startswith('--pipe='):
                self.pipe = arg[7:]
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.pipe)
        self.sock.listen(1)

        self.conn, _ = self.sock.accept()

    def cleanup(self):
        if self.conn:
            self.conn.close()
        if self.sock:
            self.sock.close()

    def read(self, size):
        return self.conn.recv(size)

    def write(self, data):
        self.conn.sendall(data)


class NamedPipeServer(ServerWrapper):
    def __init__(self, cmake):
        super().__init__(cmake)

    def connect(self, args):
        raise NotImplementedError()

    def cleanup(self):
        raise NotImplementedError()

    def read(self, size):
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()
