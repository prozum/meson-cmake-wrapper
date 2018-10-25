import os
import json
import subprocess

from .ninja import NinjaBackend


class Meson:
    """
    Base class that handles data fetching and setting options for Meson.
    """

    def __init__(self, path='meson'):
        self.path = path
        self.backend = None
        self.build_dir = None
        self.source_dir = None
        self.build_type = None
        self.cross_file = None

        # Cache
        self.c_targets = None
        self.c_target_files = {}
        self.c_buildsystem_files = None
        self.c_project_info = None
        self.c_compile_commands = None
        self.c_compile_commands_target = {}
        self.c_default_inc_dirs = {}

    def log(self, msg):
        if isinstance(msg, Exception):
            self.logger.info(msg, exc_info=msg)
        else:
            self.logger.info(msg)

    def call(self, args, show=False):
        child = subprocess.Popen([self.path] + args, stdout=subprocess.PIPE)
        fulloutput = b''
        while True:
            output = child.stdout.readline()
            if output == b'' and child.poll() is not None:
                break
            if output:
                if show:
                    print(output.decode("utf-8"), end='')
                fulloutput += output
        fulloutput = fulloutput.decode("utf-8")
        if child.poll() != 0:
            raise RuntimeError(fulloutput)
        return fulloutput

    def set_backend(self, backend):
        if backend == 'ninja':
            self.backend = NinjaBackend(self)
        else:
            raise RuntimeError('Backend not supported: ' + backend)

    def setup(self):
        if not self.backend:
            raise RuntimeError('Build is not initilized')
        if self.backend.setup():
            return

        meson_file = os.path.join(self.source_dir, 'meson.build')
        if not os.path.exists(meson_file):
            raise RuntimeError('No meson.build in source directory!')

        self.call(['setup'] + self.get_options() + [self.source_dir, self.build_dir], True)

    def build(self, target):
        return self.backend.build(target)

    def get_targets(self):
        if self.c_targets:
            return self.c_targets

        output = self.call(['introspect', '--targets', self.build_dir])
        self.log('(targets) "%s"' % output)
        self.c_targets = json.loads(output)
        return self.c_targets

    def get_target_files(self, target):
        id = target['id']
        if id == 'all' or target['type'] in ('run', 'custom'):
            return []
        if id in self.c_target_files:
            return self.c_target_files[id]

        self.log('(target) "%s"' % id)
        output = self.call(['introspect', '--target-files', id, self.build_dir])
        self.log('(target files) "%s"' % output)

        # Workaround https://github.com/mesonbuild/meson/issues/2783
        if output == '':
            return []

        self.c_target_files[id] = json.loads(output)
        return self.c_target_files[id]

    def get_buildsystem_files(self):
        if self.c_buildsystem_files:
            return self.c_buildsystem_files
        output = self.call(['introspect', '--buildsystem-files', self.build_dir])
        self.log('(buildsystem files) "%s"' % output)
        self.c_buildsystem_files = json.loads(output)
        return self.c_buildsystem_files

    def get_project_info(self):
        if self.c_project_info:
            return self.c_project_info
        output = self.call(['introspect', '--projectinfo', self.build_dir])
        self.log('(project info) "%s"' % output)
        self.c_project_info = json.loads(output)
        return self.c_project_info

    def get_compile_commands(self, target):
        id = target['id']
        if id in self.c_compile_commands_target:
            return self.c_compile_commands_target[id]

        if not self.c_compile_commands:
            compile_commands_file = os.path.join(self.build_dir, 'compile_commands.json')
            if not os.path.exists(compile_commands_file):
                Exception('No compile_commands.json in build dir')
            json_data = open(compile_commands_file).read()
            self.c_compile_commands = json.loads(json_data)

        # Only way to identify target compiler commands from compile_commands.json
        # is by using a file from the wanted target
        if len(self.get_target_files(target)) == 0:
            return []
        target_file = os.path.relpath(os.path.join(self.source_dir, self.get_target_files(target)[0]), self.build_dir)
        self.c_compile_commands_target[id] = next((cmd for cmd in self.c_compile_commands if cmd['file'] == target_file), None)
        return self.c_compile_commands_target[id]

    def get_compiler(self, target=None):
        if not target:
            target = self.get_targets()[0]

        compile_commands = self.get_compile_commands(target)
        if not compile_commands:
            return ''

        return compile_commands['command'].split()[0]

    def get_flags(self, target):
        compile_commands = self.get_compile_commands(target)
        if not compile_commands:
            return []

        args = compile_commands['command'].split()[1:]
        return [arg for arg in args if not arg.startswith(('-D', '-I'))]

    def get_defines(self, target):
        compile_commands = self.get_compile_commands(target)
        if not compile_commands:
            return []

        args = compile_commands['command'].split()
        return [arg for arg in args if arg.startswith('-D')]

    def get_include_directories(self, target=None, def_inc=True):
        if not target:
            target = self.get_targets()[0]

        compile_commands = self.get_compile_commands(target)
        if not compile_commands:
            return []

        if def_inc:
            def_inc_dirs = self.get_default_include_directories(target)
        else:
            def_inc_dirs = []
        args = compile_commands['command'].split()
        return [os.path.abspath(os.path.join(self.build_dir, arg[2:])) for arg in args if
                arg.startswith('-I')] + def_inc_dirs

    def get_default_include_directories(self, target=None):
        compiler = self.get_compiler(target)
        if not compiler:
            return []

        if compiler.endswith('++'):
            lang = 'c++'
        else:
            lang = 'c'

        if lang in self.c_default_inc_dirs:
            return self.c_default_inc_dirs[lang]

        output = subprocess.Popen([compiler, '-x' + lang, '-E', '-v', '-'],
                                  stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE)
        stderr = output.stderr.read().decode()
        start = False
        paths = []
        for line in stderr.split('\n'):
            if not start:
                if line == '#include <...> search starts here:':
                    start = True
            elif start:
                if line == 'End of search list.':
                    break
                else:
                    paths.append(os.path.abspath(line[1:]))

        self.c_default_inc_dirs[lang] = paths
        return self.c_default_inc_dirs[lang]

    def get_output(self, target):
        return os.path.join(self.build_dir, target['filename'])

    def get_options(self):
        meson_options = []

        if self.cross_file:
            meson_options += ['--cross-file', self.cross_file]

        return meson_options
