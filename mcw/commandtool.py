import os
import json
import hashlib

class CommandToolWrapper:
    """
    Class that emulates CMake Command-Line Tool Mode.
    """

    def __init__(self, cmake):
        self.cmake = cmake

    def list_cmds(self):
        print('CMake Error: cmake version ' + '.'.join(map(str, self.cmake.version)))
        print('Usage: meson-cmake-wrapper -E <command> [arguments...]')
        print('Available commands:')
        print('  capabilities              - Report capabilities built into cmake in JSON format')
        print('  chdir dir cmd [args...]   - run command in a given directory')
        print('  compare_files file1 file2 - check if file1 is same as file2')
        print('  copy <file>... destination  - copy files to destination (either file or directory)')
        print('  copy_directory <dir>... destination   - copy content of <dir>... directories to \'destination\' directory')
        print('  copy_if_different <file>... destination  - copy files if it has changed')
        print('  echo [<string>...]        - displays arguments as text')
        print('  echo_append [<string>...] - displays arguments as text but no new line')
        print('  env [--unset=NAME]... [NAME=VALUE]... COMMAND [ARG]...')
        print('                            - run command in a modified environment')
        print('  environment               - display the current environment')
        print('  make_directory <dir>...   - create parent and <dir> directories')
        print('  md5sum <file>...          - create MD5 checksum of files')
        print('  sha1sum <file>...         - create SHA1 checksum of files')
        print('  sha224sum <file>...       - create SHA224 checksum of files')
        print('  sha256sum <file>...       - create SHA256 checksum of files')
        print('  sha384sum <file>...       - create SHA384 checksum of files')
        print('  sha512sum <file>...       - create SHA512 checksum of files')
        print('  remove [-f] <file>...     - remove the file(s), use -f to force it')
        print('  remove_directory dir      - remove a directory and its contents')
        print('  rename oldname newname    - rename a file or directory (on one volume)')
        print('  server                    - start cmake in server mode')
        print('  sleep <number>...         - sleep for given number of seconds')
        print('  tar [cxt][vf][zjJ] file.tar [file/dir1 file/dir2 ...]')
        print('                            - create or extract a tar or zip archive')
        print('  time command [args...]    - run command and return elapsed time')
        print('  touch file                - touch a file.')
        print('  touch_nocreate file       - touch a file but do not create it.')
        print('Available on UNIX only:')
        print('  create_symlink old new    - create a symbolic link new -> old')

    def run(self, args):
        if not hasattr(self, args[0] + '_cmd'):
            self.list_cmds()
            exit(1)
        getattr(self, args[0] + '_cmd')(args[1:])

    def capabilities_cmd(self, args):
        data = {
            'generators': [
                {
                    'extraGenerators': ['CodeBlocks'],
                    'name': 'Unix Makefiles',
                    'platformSupport': False,
                    'toolsetSupport': False
                },
                {
                    'extraGenerators': ['CodeBlocks'],
                    'name': 'Ninja',
                    'platformSupport': False,
                    'toolsetSupport': False
                }
            ],
            'serverMode': True,
            'version': {
                'isDirty': False,
                'major': self.cmake.version[0],
                'minor': self.cmake.version[1],
                'patch': self.cmake.version[2],
                'string': '.'.join(map(str, self.cmake.version)),
                'suffix': ''
            }
        }
        print(json.dumps(data))

    def chdir_cmd(self, args):
        os.chdir(args[0])
        call(args[1:])

    def compare_files_cmd(self, args):
        if filecmp.cmp(args[0], args[1]):
            exit(0)
        print('Files "%s" to "%s" are different.' % (args[0], args[1]))
        exit(1)

    def copy_cmd(self, args):
        files = args[:-1]
        dir = args[-1]
        if not os.path.exists(dir):
            os.makedirs(dir)
        for file in files:
            copy(file, dir)

    def copy_if_different_cmd(self, args):
        raise NotImplementedError()

    def copy_directory_cmd(self, args):
        cp_dirs = args[:-1]
        dir = args[-1]
        if not os.path.exists(dir):
            os.makedirs(dir)
        for cp_dir in cp_dirs:
            copytree(cp_dir, dir)

    def echo_cmd(self, args):
        print(' '.join(args))

    def echo_append_cmd(self, args):
        print(' '.join(args), end='')

    def env_cmd(self, args):
        env = dict(os.environ)
        for i in range(len(args)):
            if '=' in args[i]:
                if args[i].startswith('--unset'):
                    env.pop(args[i].splits('=')[1], None)
                else:
                    key, val = args[i].split('=')
                    env[key] = val
            else:
                cmd = args[i:]
                break
        Popen(cmd, env=env)

    def environment_cmd(self, args):
        for key, val in os.environ.items():
            print('%s=%s' % (key, val))

    def make_directory_cmd(self, args):
        for dir in args:
            os.makedirs(dir)

    def md5sum_cmd(self, args):
        crypt = hashlib.md5()
        for file in args:
            with open(file, 'rb') as f:
                crypt.update(f.read())
            print('%s %s' % (crypt.hexdigest(), file))

    def sha224sum_cmd(self, args):
        crypt = hashlib.sha224()
        for file in args:
            with open(file, 'rb') as f:
                crypt.update(f.read())

    def sha256sum_cmd(self, args):
        crypt = hashlib.sha256()
        for file in args:
            with open(file, 'rb') as f:
                crypt.update(f.read())

    def sha384sum_cmd(self, args):
        crypt = hashlib.sha384()
        for file in args:
            with open(file, 'rb') as f:
                crypt.update(f.read())

    def sha512sum_cmd(self, args):
        crypt = hashlib.md5()
        for file in args:
            with open(file, 'rb') as f:
                crypt.update(f.read())

    def remove_cmd(self, args):
        for file in args:
            if file != '-f':
                os.remove(file)

    def remove_directory_cmd(self, args):
        rmtree(args[0])

    def rename_cmd(self, args):
        os.rename(args[0], args[1])

    def server_cmd(self, args):
        self.cmake.server.run(args)

    def sleep_cmd(self, args):
        sleep(float(args[0]))

    def tar_cmd(self, args):
        raise NotImplementedError()

    def touch_cmd(self, args):
        with open(args[0], 'a'):
            os.utime(args[0])

    def touch_nocreate_cmd(self, args):
        if os.path.isfile(args[0]):
            with open(args[0], 'a'):
                os.utime(args[0])

    def create_symlink_cmd(self, args):
        os.symlink(args[0], args[1])
