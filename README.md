# meson-cmake-wrapper
Build system wrapper that provides Meson integration in CMake IDE's.

## Install
`pip3 install meson-cmake-wrapper`

## VS Code

### Setup
1. Install [vscode-cmake-tools](https://github.com/vector-of-bool/vscode-cmake-tools).

2. Change `"cmake.cmakePath"` option to `mcw`.

3. Create an empty `CMakeLists.txt` file in root of project.

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
Change CMake option to path of `mcw`.

2. Create an empty `CMakeLists.txt` file in root of project.

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
Add manual CMake option with path of `mcw`.

2. Create an empty `CMakeLists.txt` file in root of project.

### Works
* Detect targets
* Detect toolchain
* Detect target files
* Build target
* Run target
* Run target with valgrind
* Debug target
* Autocompletion

## Code::Blocks

### Setup
1. Generate Code::Blocks project: 

`mcw -G"CodeBlocks - Ninja" -DCMAKE_BUILD_TYPE=Debug <build-dir>`

2. In Code::Blocks open: `<build-dir>/<project-name>.cbp` 

### Works
* Detect targets
* Detect toolchain
* Detect target files
* Build target
* Run target
* Debug target
* Autocompletion
