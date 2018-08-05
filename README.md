# meson-cmake-wrapper
Build system wrapper that provides Meson integration in CMake IDE's.

## VS Code

### Setup
1. Install [vscode-cmake-tools](https://github.com/vector-of-bool/vscode-cmake-tools).

2. Change "cmake.cmakePath" option to meson-cmake-wrapper.

3. Create an empty CMakeLists.txt file in root of project.

### Works
* Detect targets
* Detect toolchain
* Detect target files
* Build target
* Run target
* Debug target
* Autocompletion

## CLion

### Setup
1. In Toolchain settings (File > Settings > Build, Execution, Deployment > Toolchains):
Change CMake option to path of meson-cmake-wrapper.

2. Create an empty CMakeLists.txt file in root of project.

### Works
* Detect targets
* Detect toolchain
* Detect target files
* Build target
* Run target
* Run target with valgrind
* Debug target
* Autocompletion

## QtCreator

### Setup
1. In CMake settings (Tools > Options... > Build & Run > CMake):
Add manual CMake option with path of meson-cmake-wrapper.

2. Create an empty CMakeLists.txt file in root of project.

### Works
* Detect targets
* Detect toolchain
* Detect target files
* Build target
* Run target
* Run target with valgrind
* Debug target
* Autocompletion
