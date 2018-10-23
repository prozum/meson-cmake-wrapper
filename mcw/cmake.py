import os
import sys
import pickle
import pathlib
import logging
import json
import xml.etree.ElementTree as ETree

from .logging import ServerLogHandler
from .util import find_executables
from .commandtool import CommandToolWrapper
from .server import (UnixSocketServer, NamedPipeServer)
from .meson import Meson


class CMakeWrapper:
    """
    Class that emulates CMake commands and translates them to the equivalent in Meson.
    """

    def __init__(self):
        self.version = [3, 10, 0]
        self.path = sys.argv[0]
        self.debug = False
        self.command = 'generate'
        self.generator = None
        self.build_type = None
        self.cache_entries = {}
        self.target = 'all'
        self.target_args = []
        self.build_dir = None
        self.source_dir = None
        self.gen_cmake = False
        self.meson = Meson()
        if os.name == 'nt':
            self.server = NamedPipeServer(self)
        else:
            self.server = UnixSocketServer(self)
        self.tool = CommandToolWrapper(self)
        self.logger = None

    def run(self, args):
        self.init_logging()

        self.log('(args) "%s"' % args)
        self.log('(cwd) "%s"' % os.getcwd())

        # debug_connect()

        self.parse_args(args)

        # Unknown command
        if not hasattr(self, self.command + '_cmd'):
            self.help_cmd()
            return

        # Run command
        try:
            getattr(self, self.command + '_cmd')()
        except RuntimeError as e:
            print(e.args[0])
            self.log(e)
            exit(1)
        except Exception as e:
            self.log(e)
            raise e
        self.save_cache_entries()

    def parse_args(self, args):
        if len(args) == 1:
            self.command = 'none'
        i = 1
        while i < len(args):
            if args[i] in ('-version', '--version'):
                self.command = 'version'
            elif args[i] in ('-h', '-help', '--help'):
                self.command = 'help'
            elif args[i] == '--debug-output':
                self.debug = True
            elif args[i] == '--help-module-list':
                self.command = 'module_list'
            # Undocumented CMake flags -H -B
            elif args[i].startswith('-H'):
                self.set_source_dir(args[i][2:])
            elif args[i].startswith('-B'):
                self.set_build_dir(args[i][2:])
            elif args[i] == '-G':
                self.command = 'generate'
                i += 1
                self.set_generator(args[i])
            elif args[i].startswith('-G'):
                self.command = 'generate'
                self.set_generator(args[i][2:])
            elif args[i] == '--build':
                self.command = 'build'
                i += 1
                self.set_build_dir(args[i])
            elif args[i] == '--target':
                i += 1
                self.target = args[i]
            elif args[i] == '--config':
                i += 1
                self.set_build_type(args[i])
            elif args[i] == '--':
                self.target_args = args[i + 1:]
                break
            elif args[i] == '-E':
                self.command = 'tool'
                self.command_args = args[i + 1:]
                break
            elif args[i].startswith('-D'):
                self.parse_cache_entry(args[i])
            else:
                self.set_source_dir(args[i])
            i += 1

    def none_cmd(self):
        print('Usage\n')
        print('  meson-cmake-wrapper [options] <path-to-source>')
        print('  meson-cmake-wrapper [options] <path-to-existing-build>\n')
        print('Specify a source directory to (re-)generate a build system for it in the')
        print('current working directory.  Specify an existing build directory to')
        print('re-generate its build system.\n')
        print('Run \'meson-cmake-wrapper --help\' for more information.\n')

    def version_cmd(self):
        print('cmake version {0}'.format('.'.join(map(str, self.version))))

    def help_cmd(self):
        print('Usage\n')
        print('meson-cmake-wrapper [options] <path-to-source>')
        print('meson-cmake-wrapper [options] <path-to-existing-build>\n')
        print('Specify a source directory to (re-)generate a build system for it in the')
        print('current working directory.  Specify an existing build directory to')
        print('re-generate its build system.\n')
        print('Options')
        print('  -C <initial-cache>           = Pre-load a script to populate the cache.')
        print('  -D <var>[:<type>]=<value>    = Create a cmake cache entry.')
        print('  -G <generator-name>          = Specify a build system generator.')
        print('  -E                           = CMake command mode.\n')
        print('  --build <dir>                = Build a CMake-generated project binary tree.')
        print('  --version,-version,/V [<f>]  = Print version number and exit.')
        print('  --debug-output               = Put cmake in a debug mode.\n')
        print('Generators\n')
        print('The following generators are available on this platform:')
        print('  Unix Makefiles               = Generates standard UNIX makefiles.')
        print('  Ninja                        = Generates build.ninja files.')
        print('  CodeBlocks - Ninja           = Generates CodeBlocks project files.\n')
        print('  CodeBlocks - Unix Makefiles  = Generates CodeBlocks project files.\n')

    def module_list_cmd(self):
        pass  # meson-cmake-wrapper does not support modules

    def generate_cmd(self):
        # Set default generator
        if not self.generator:
            self.set_generator('Unix Makefiles')

        # Set default build dir
        if not self.build_dir:
            self.set_build_dir(os.getcwd())

        print('Generate to build directory: ' + self.build_dir)

        # Make sure meson is setup
        self.load_cache_entries()
        self.meson.setup()

        # Create CMakeCache.txt
        self.gen_cmake_cache()

        if self.gen_cmake:
            self.gen_cmake_project()

        if self.generator.endswith('Unix Makefiles'):
            self.gen_make_project()

        if self.generator.startswith('CodeBlocks'):
            self.gen_codeblocks_project()

        if self.generator.startswith('Android Gradle'):
            self.gen_android_gradle_project()

    def build_cmd(self):
        # Set default build dir
        if not self.build_dir:
            self.set_build_dir(os.getcwd())

        # Make sure meson is setup
        self.load_cache_entries()
        self.meson.setup()

        print('Building target: ' + self.target)
        self.meson.build(self.target)

    def tool_cmd(self):
        self.tool.run(self.command_args)

    def init_logging(self, dir=None):
        # Setup loggers
        loggers = []
        self.logger = logging.getLogger('CMake Wrapper')
        loggers.append(self.logger)
        self.meson.logger = logging.getLogger('Meson')
        loggers.append(self.meson.logger)
        self.server.logger = logging.getLogger('Server')
        loggers.append(self.server.logger)

        # Cleanup if reinitialized
        for logger in loggers:
            logger.handlers = []

        if not dir and self.debug:
            dir = os.getcwd()

        # Setup handlers and formatters
        handlers = []
        if dir:
            handler = logging.FileHandler(os.path.join(dir, 'meson-cmake-wrapper.log'))
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s: %(message)s')
            handler.setFormatter(formatter)
            handlers.append(handler)

        if self.debug:
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(name)s: %(message)s')
            handler.setFormatter(formatter)
            handlers.append(handler)

            handler = ServerLogHandler(self.server)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(name)s: %(message)s')
            handler.setFormatter(formatter)
            handlers.append(handler)

        for logger in loggers:
            logger.setLevel(logging.INFO)
            for handler in handlers:
                logger.addHandler(handler)

    def log(self, msg):
        if isinstance(msg, Exception):
            self.logger.info(msg, exc_info=msg)
        else:
            self.logger.info(msg)

    def set_generator(self, generator):
        if generator == 'Ninja':
            self.meson.set_backend('ninja')
        elif generator == 'Unix Makefiles':
            self.meson.set_backend('ninja')
        elif generator == 'CodeBlocks - Ninja':
            self.meson.set_backend('ninja')
        elif generator == 'CodeBlocks - Unix Makefiles':
            self.meson.set_backend('ninja')
        elif generator == 'Android Gradle - Ninja':
            self.meson.set_backend('ninja')
        else:
            raise Exception('Generator not supported: ' + generator)
        self.generator = generator

        self.log('(generator) "%s"' % self.generator)

    def set_source_dir(self, source_dir):
        if not os.path.exists(source_dir):
            raise RuntimeError('No such source directory: ' + source_dir)
        if not os.path.isdir(source_dir):
            raise RuntimeError('Source directory path is not a directory: ' + source_dir)

        self.source_dir = os.path.abspath(source_dir)
        self.meson.source_dir = self.source_dir

        self.log('(source_dir) "%s"' % self.source_dir)

    def set_build_dir(self, build_dir):
        if not os.path.exists(build_dir):
            raise RuntimeError('No such build directory: ' + build_dir)
        if not os.path.isdir(build_dir):
            raise RuntimeError('Build directory path is not a directory: ' + build_dir)

        self.build_dir = os.path.abspath(build_dir)
        self.meson.build_dir = self.build_dir

        self.init_logging(build_dir)

        # Handle cmake_test_run (CLion)
        if self.source_dir:
            cmake_file = os.path.join(self.source_dir, 'CMakeLists.txt')
            meson_file = os.path.join(self.source_dir, 'meson.build')
            if not os.path.exists(meson_file) and os.path.getsize(cmake_file) > 0:
                with open(meson_file, 'w') as file:
                    file.write('project(\'empty\')')

        self.log('(build_dir) "%s"' % self.build_dir)

    def set_build_type(self, build_type):
        self.build_type = build_type
        if build_type.upper() in ('DEBUG', ''):
            self.meson.build_type = 'debug'
        elif build_type.upper() == 'RELEASE':
            self.meson.build_type = 'release'
        elif build_type.upper() == 'RELWITHDEBINFO':
            self.meson.build_type = 'debugoptimized'
        elif build_type.upper() == 'MINSIZEREL':
            self.meson.build_type = 'minsize'
        else:
            self.meson.build_type = 'plain'

        self.cache_entries['CMAKE_BUILD_TYPE'] = (build_type, 'STRING')

        self.log('(build_type) "%s"' % self.build_type)

    def get_entry(self, entry):
        if entry in self.cache_entries:
            return self.cache_entries[entry][0]
        else:
            return None

    def init_cache_entries(self):
        if not self.source_dir:
            raise Exception('Source dir not provided')

        self.meson.setup()

        cache_entries = {
            'CMAKE_EXPORT_COMPILE_COMMANDS': ('YES', 'BOOL'),
            'CMAKE_INSTALL_PREFIX': ('c:/Program Files' if os.name == 'nt' else '/usr/local', 'PATH'),
            'CMAKE_C_COMPILER': (find_executables(['cc', 'gcc', 'clang']), 'FILEPATH'),
            'CMAKE_CXX_COMPILER': (find_executables(['c++', 'g++', 'clang++']), 'FILEPATH'),
            'CMAKE_MAKE_PROGRAM': (find_executables(['make']), 'FILEPATH'),
            'CMAKE_RANLIB': (find_executables(['ranlib']), 'FILEPATH'),
            'CMAKE_AR': (find_executables(['ar']), 'FILEPATH'),
            'CMAKE_PROJECT_NAME': (self.meson.get_project_info()['name'], 'STATIC'),
            '%s_BINARY_DIR' % self.meson.get_project_info()['name']: (self.build_dir, 'STATIC'),
            '%s_SOURCE_DIR' % self.meson.get_project_info()['name']: (self.source_dir, 'STATIC'),
            'CMAKE_CACHEFILE_DIR': (self.build_dir, 'INTERNAL'),
            'CMAKE_CACHE_MAJOR_VERSION': (str(self.version[0]), 'INTERNAL'),
            'CMAKE_CACHE_MINOR_VERSION': (str(self.version[1]), 'INTERNAL'),
            'CMAKE_CACHE_PATCH_VERSION': (str(self.version[2]), 'INTERNAL'),
            'CMAKE_COMMAND': (self.path, 'INTERNAL'),
            'CMAKE_GENERATOR': (self.generator, 'INTERNAL'),
            'CMAKE_HOME_DIRECTORY': (self.source_dir, 'INTERNAL'),
            'CMAKE_ROOT': (os.path.dirname(self.path), 'INTERNAL'),
        }

        for key, val in self.cache_entries.items():
            cache_entries[key] = val
        self.cache_entries = cache_entries

    def parse_cache_entry(self, entry):
        if ':' in entry:
            key, rest = entry[2:].split(':', 1)
            ty, val = rest.split('=', 1)
        else:
            key, val = entry[2:].split('=', 1)
            ty = 'STRING'
        self.cache_entries[key] = (val, ty, '')
        self.update_cache_entry(key, val)

    def update_cache_entry(self, key, val):
        if key == 'CMAKE_GENERATOR':
            self.set_generator(val)
        elif key == 'CMAKE_BUILD_TYPE':
            self.set_build_type(val)
        elif key == 'CMAKE_HOME_DIRECTORY':
            self.set_source_dir(val)
        elif key == 'CMAKE_C_COMPILER':
            os.environ['CC'] = val
        elif key == 'CMAKE_CXX_COMPILER':
            os.environ['CXX'] = val
        elif key == 'CMAKE_C_FLAGS':
            os.environ['CFLAGS'] = val
        elif key == 'CMAKE_CXX_FLAGS':
            os.environ['CXXFLAGS'] = val
        # Use CMake variable 'MESON' for custom Meson path
        elif key == 'MESON':
            self.meson.path = val
        # Use CMake variable 'CROSS_FILE' for setting Meson cross-file
        elif key == 'CROSS_FILE':
            self.meson.cross_file = val
        # Use CMake variable 'GEN_CMAKE' to toggle cmake project generation
        elif key == 'GEN_CMAKE':
            self.gen_cross = True

    def save_cache_entries(self):
        if self.build_dir:
            cache_file = os.path.join(self.build_dir, 'cmake-cache.pk1')
            with open(cache_file, 'wb') as output:
                pickle.dump(self.cache_entries, output, pickle.HIGHEST_PROTOCOL)

    def load_cache_entries(self):
        cache_file = os.path.join(self.build_dir, 'cmake-cache.pk1')
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as input:
                loaded_entries = pickle.load(input)
                diff_entries = set(loaded_entries) - set(self.cache_entries)

                for key in diff_entries:
                    self.cache_entries[key] = loaded_entries[key]
                    self.update_cache_entry(key, loaded_entries[key][0])
        elif self.build_dir:
            self.init_cache_entries()

    def gen_cmake_cache(self):
        with open(os.path.join(self.build_dir, 'CMakeCache.txt'), 'w') as file:
            file.write('# Generated by meson-cmake-wrapper\n\n')
            file.write('########################\n')
            file.write('# Cache entries\n')
            file.write('########################\n\n')
            for entry in self.cache_entries.items():
                file.write('%s:%s=%s\n' % (entry[0], entry[1][1], entry[1][0]))

    def gen_cmake_project(self):
        with open(os.path.join(self.source_dir, 'CMakeLists.txt'), 'w') as file:
            file.write('cmake_minimum_required(VERSION %s)\n' % '.'.join(map(str, self.version)))
            file.write('project(%s)\n\n' % self.meson.get_project_info()['name'])

            include_dirs = set()
            for target in self.meson.get_targets():
                include_dirs = include_dirs.union(self.meson.get_include_directories(target, False))

            file.write('include_directories(\n    ')
            file.write('\n    '.join(include_dirs) + ')\n\n')

            for target in self.meson.get_targets():
                file.write('# Target %s\n' % target['name'])
                if target['type'] == 'executable':
                    file.write('add_executable(%s\n    ' % (target['name']))
                elif target['type'] == 'static library':
                    file.write('add_library(%s\n    ' % (target['name']))
                elif target['type'] == 'shared library':
                    file.write('add_library(%s SHARED\n    ' % (target['name']))

                target_files = self.meson.get_target_files(target)
                file.write('\n    '.join(target_files) + ')\n')

                # file.write('target_include_directories(%s PUBLIC\n    ' % (target['name']))
                # file.write('\n    '.join(self.meson.get_include_directories(target, False)) + ')\n\n')

    def gen_codeblocks_project(self):
        root = ETree.Element('CodeBlocks_project_file')
        tree = ETree.ElementTree(root)
        ETree.SubElement(root, 'FileVersion', {'major': '1', 'minor': '6'})
        project = ETree.SubElement(root, 'Project')
        ETree.SubElement(project, 'Option', {'title': self.meson.get_project_info()['name']})
        ETree.SubElement(project, 'Option', {'makefile_is_custom': '1'})
        ETree.SubElement(project, 'Option', {'compiler': 'gcc'})
        ETree.SubElement(project, 'Option', {'virtualFolders': 'Meson Files'})

        build = ETree.SubElement(project, 'Build')

        all_target = {
            'name': 'all',
            'id': 'all',
            'type': 'custom',
            'filename': ''
        }

        for target in [all_target] + self.meson.get_targets():
            build_target = ETree.SubElement(build, 'Target', {'title': target['name']})
            output = os.path.join(self.meson.build_dir, target['filename'])
            output_dir = os.path.split(output)[0]
            ETree.SubElement(build_target, 'Option', {'output': output})
            ETree.SubElement(build_target, 'Option', {'working_dir': output_dir})
            ETree.SubElement(build_target, 'Option', {'object_output': os.path.join(output_dir, target['id'])})
            ty = {
                'executable': '1',
                'static library': '2',
                'shared library': '3',
                'custom': '4',
                'run': '4'
            }[target['type']]
            ETree.SubElement(build_target, 'Option', {'type': ty})

            compiler = self.meson.get_compiler(target)
            if compiler:
                ETree.SubElement(build_target, 'Option', {'compiler': 'gcc'})

            compiler = ETree.SubElement(build_target, 'Compiler')
            for define in self.meson.get_defines(target):
                ETree.SubElement(compiler, 'Add', {'option': define})
            for include_dir in self.meson.get_include_directories(target):
                ETree.SubElement(compiler, 'Add', {'directory': include_dir})

            make_commands = ETree.SubElement(build_target, 'MakeCommands')
            ETree.SubElement(make_commands, 'Build', {'command': self.meson.backend.path + ' -v ' + self.meson.backend.get_target(target['name'])})
            ETree.SubElement(make_commands, 'CompileFile', {'command': self.meson.backend.path + ' -v ' + self.meson.backend.get_target(target['name'])})
            ETree.SubElement(make_commands, 'Clean', {'command': self.meson.backend.path + ' -v clean'})
            ETree.SubElement(make_commands, 'DistClean', {'command': self.meson.backend.path + ' -v clean'})

        for target in self.meson.get_targets():
            target_files = self.meson.get_target_files(target)
            for target_file in target_files:
                unit = ETree.SubElement(project, 'Unit', {'filename': os.path.join(self.source_dir, target_file)})
                ETree.SubElement(unit, 'Option', {'target': target['name']})

                base = os.path.splitext(os.path.basename(target_file))[0]
                header_exts = ('h', 'hpp')
                for ext in header_exts:
                    header_file = os.path.abspath(
                        os.path.join(self.source_dir, os.path.dirname(target_file), os.path.join(base + '.' + ext)))
                    if os.path.exists(header_file):
                        unit = ETree.SubElement(project, 'Unit', {'filename': header_file})
                        ETree.SubElement(unit, 'Option', {'target': target['name']})

        for file in self.meson.get_buildsystem_files():
            unit = ETree.SubElement(project, 'Unit', {'filename': os.path.join(self.source_dir, file)})
            ETree.SubElement(unit, 'Option', {'virtualFolder': os.path.join('Meson Files', os.path.dirname(file))})

        project_file = os.path.join(self.build_dir, self.meson.get_project_info()['name'] + '.cbp')
        tree.write(project_file, 'unicode', True)

    def gen_make_project(self):
        # CLion requires a CMakeFiles directory at root of build directory
        root_cmakefiles_dir = os.path.join(self.build_dir, 'CMakeFiles')
        if not os.path.exists(root_cmakefiles_dir):
            os.mkdir(root_cmakefiles_dir)

        version_cmakefiles_dir = os.path.join(root_cmakefiles_dir, '.'.join(map(str, self.version)))
        if not os.path.exists(version_cmakefiles_dir):
            os.mkdir(version_cmakefiles_dir)
        with open(os.path.join(version_cmakefiles_dir, 'CMakeCCompiler.cmake'), 'w') as file:
            file.write('set(CMAKE_C_COMPILER "%s")' % self.get_entry('CMAKE_C_COMPILER'))
        with open(os.path.join(version_cmakefiles_dir, 'CMakeCXXCompiler.cmake'), 'w') as file:
            file.write('set(CMAKE_CXX_COMPILER "%s")' % self.get_entry('CMAKE_CXX_COMPILER'))

        # TODO: support for non-linux systems
        with open(os.path.join(version_cmakefiles_dir, 'CMakeSystem.cmake'), 'w') as file:
            file.write('set(CMAKE_HOST_SYSTEM_NAME "Linux")\n')
            file.write('set(CMAKE_SYSTEM_NAME "Linux")\n')

        # CLion requires Makefile.cmake
        with open(os.path.join(root_cmakefiles_dir, 'Makefile.cmake'), 'w') as file:
            file.write('set(CMAKE_DEPENDS_GENERATOR "%s")\n' % self.generator)

            file.write('set(CMAKE_MAKEFILE_DEPENDS\n')
            file.write('    "CMakeCache.txt"\n')
            file.write('    "%s/CMakeLists.txt"\n' % os.path.relpath(self.source_dir, self.build_dir))
            file.write('    "%s/CMakeCCompiler.cmake"\n' % os.path.relpath(version_cmakefiles_dir, self.build_dir))
            file.write('    "%s/CMakeCXXCompiler.cmake"\n' % os.path.relpath(version_cmakefiles_dir, self.build_dir))
            file.write('    "%s/CMakeSystem.cmake"\n' % os.path.relpath(version_cmakefiles_dir, self.build_dir))
            file.write('  )\n')

            file.write('set(CMAKE_MAKEFILE_DEPENDS\n')
            file.write('    "CMakeFiles/CMakeDirectoryInformation.cmake"\n')
            file.write('  )\n')

            file.write('set(CMAKE_DEPEND_INFO_FILES\n')
            for target in self.meson.get_targets():
                target_depend = os.path.join(os.path.dirname(target['filename']), 'CMakeFiles',
                                             target['name'] + '.dir', 'DependInfo.cmake')
                file.write('  "%s"\n' % target_depend)
            file.write('  )')

        with open(os.path.join(root_cmakefiles_dir, 'CMakeDirectoryInformation.cmake'), 'w') as dir_info_file:
            dir_info_file.write('set(CMAKE_RELATIVE_PATH_TOP_SOURCE "%s")\n' % self.source_dir)
            dir_info_file.write('set(CMAKE_RELATIVE_PATH_TOP_BINARY "%s")\n' % self.build_dir)
            dir_info_file.write('set(CMAKE_C_INCLUDE_REGEX_SCAN "^.*$")\n')
            dir_info_file.write('set(CMAKE_C_INCLUDE_REGEX_COMPLAIN "^$")\n')
            dir_info_file.write('set(CMAKE_CXX_INCLUDE_REGEX_SCAN ${CMAKE_C_INCLUDE_REGEX_SCAN})\n')
            dir_info_file.write('set(CMAKE_CXX_INCLUDE_REGEX_COMPLAIN ${CMAKE_C_INCLUDE_REGEX_COMPLAIN})\n')

        # CLion fetches target directories from TargetDirectories.txt
        with open(os.path.join(root_cmakefiles_dir, 'TargetDirectories.txt'), 'w') as target_dir_file:
            targets = self.meson.get_targets()

            for target in targets:
                # Detect language
                lang = None
                compiler = self.meson.get_compiler(target)
                if compiler:
                    if compiler.endswith('++'):
                        lang = 'CXX'
                    else:
                        lang = 'CC'

                # All directories under the build directory should have a CMakeFiles directory
                cmakefiles_dir = os.path.join(self.build_dir, os.path.dirname(target['filename']), 'CMakeFiles')
                pathlib.Path(cmakefiles_dir).mkdir(parents=True, exist_ok=True)

                # CLion fetches target name from TARGET_NAME.dir directories
                target_path = os.path.join(self.build_dir, os.path.dirname(target['filename']), 'CMakeFiles',
                                           target['name'] + '.dir')
                target_dir_file.write(target_path + '\n')
                pathlib.Path(target_path).mkdir(exist_ok=True)

                # CLion requires TARGET_PATH/DependInfo.cmake
                with open(os.path.join(target_path, 'DependInfo.cmake'), 'w') as depend_file:
                    if lang:
                        depend_file.write('set(CMAKE_DEPENDS_LANGUAGES\n')
                        depend_file.write('    "%s"\n' % lang)
                        depend_file.write('    )\n')
                        depend_file.write('set(CMAKE_DEPENDS_CHECK_%s\n' % lang)
                        for target_file in self.meson.get_target_files(target):
                            object_path = os.path.join(self.build_dir, os.path.dirname(target['filename']), target['id'], os.path.basename(target_file) + '.o')
                            depend_file.write('  "%s" "%s"\n' % (os.path.join(self.source_dir, target_file), object_path))
                        depend_file.write('  )\n')
                        depend_file.write('set(CMAKE_TARGET_DEFINITIONS_%s\n' % lang)
                        for define in self.meson.get_defines(target):
                            depend_file.write('  "%s"\n' % define[2:])
                        depend_file.write('  )\n')
                        depend_file.write('set(CMAKE_%s_TARGET_INCLUDE_PATH\n' % lang)
                        for inc_dir in self.meson.get_include_directories(target, False):
                            depend_file.write('  "%s"\n' % os.path.relpath(inc_dir, self.build_dir))
                        depend_file.write('  )')

                # CLion requires TARGET_PATH/link.txt
                with open(os.path.join(target_path, 'link.txt'), 'w') as link_file:
                    link_file.write('%s qc %s ' % (self.get_entry('CMAKE_AR'), os.path.basename(target['filename'])))
                    for target_file in self.meson.get_target_files(target):
                        link_file.write('%s ' % os.path.join(os.path.dirname(target['filename']), target['id'], os.path.basename(target_file) + '.o'))
                    link_file.write('\n%s %s' % (self.get_entry('CMAKE_RANLIB'), os.path.basename(target['filename'])))

                # CLion fetches target name from TARGET_PATH/build.make
                with open(os.path.join(target_path, 'build.make'), 'w') as build_file:
                    build_file.write('%s: %s' % (os.path.join(target_path, 'build'), self.meson.get_output(target)))

                with open(os.path.join(target_path, 'flags.make'), 'w') as flags_file:
                    if lang:
                        flags_file.write('%s_FLAGS = %s\n' % (lang, ' '.join([flag for flag in self.meson.get_flags(target) if flag.startswith('-std')])))
                        flags_file.write('%s_DEFINES = %s\n' % (lang, ' '.join(self.meson.get_defines(target))))
                        flags_file.write('%s_INCLUDES = %s\n' % (lang, ' '.join(['-I' + inc_dir for inc_dir in self.meson.get_include_directories(target, False)])))

    def gen_android_gradle_project(self):
        if not self.get_entry('ANDROID_ABI'):
            raise RuntimeError('ANDROID_ABI must be set in Gradle projects')

        # android_gradle_build_mini.json
        libs = {}
        for target in self.meson.get_targets():
            if self.get_entry('CMAKE_BUILD_TYPE'):
                lib = '%s-%s-%s' % (target['name'], self.get_entry('CMAKE_BUILD_TYPE'), self.get_entry('ANDROID_ABI'))
            else:
                lib = '%s-%s' % (target['name'], self.get_entry('ANDROID_ABI'))
            libs[lib] = {
                'artifactName': target['name'],
                'buildCommand': '%s --build %s --target %s' % (self.path, self.build_dir, target['name']),
                'abi': self.get_entry('ANDROID_ABI'),
                'output': self.meson.get_output(target)
            }
        gradle_mini = {
            'buildFiles': os.path.join(self.source_dir, 'CMakeLists.txt'),
            'cleanCommands': [
                '%s --build %s --target clean' % (self.path, self.build_dir)
            ],
            'libraries': libs,
        }
        with open(os.path.join(self.build_dir, 'android_gradle_build_mini.json'), 'w') as file:
            json.dump(gradle_mini, file)

        # android_gradle_build.json
        libs = {}
        for target in self.meson.get_targets():
            if self.get_entry('CMAKE_BUILD_TYPE'):
                lib = '%s-%s-%s' % (target['name'], self.get_entry('CMAKE_BUILD_TYPE'), self.get_entry('ANDROID_ABI'))
            else:
                lib = '%s-%s' % (target['name'], self.get_entry('ANDROID_ABI'))

            files = []
            for mfile in self.meson.get_target_files(target):
                file = {}
                file['flags'] = ' '.join(self.meson.get_flags(target))
                file['src'] = os.path.join(self.source_dir, mfile)
                file['workingDirectory'] = self.build_dir
                files.append(file)

            libs[lib] = {
                'abi': self.get_entry('ANDROID_ABI'),
                'artifactName': target['name'],
                'buildCommand': '%s --build %s --target %s' % (self.path, self.build_dir, target['name']),
                'files': files,
                'output': self.meson.get_output(target),
                'toolchain': '1111111111111111111'
            }
        gradle = {
            'buildFiles': os.path.join(self.source_dir, 'CMakeLists.txt'),
            'cleanCommands': [
                '%s --build %s --target clean' % (self.path, self.build_dir)
            ],
            'cppFileExtensions': ['cpp'],
            'libraries': libs,
            'toolchains': {
                '1111111111111111111': {
                    'cCompilerExecutable': self.get_entry('CMAKE_C_COMPILER'),
                    'cppCompilerExecutable': self.get_entry('CMAKE_CXX_COMPILER')
                }
            }
        }
        with open(os.path.join(self.build_dir, 'android_gradle_build.json'), 'w') as file:
            json.dump(gradle, file)
