# meson-cmake-wrapper
Build system wrapper that provides Meson integration in CMake IDE's.

## Install
`pip3 install meson-cmake-wrapper`

## Feature Matrix
| *Feature* | *CLion* | *VS Code* | *QtCreator* | *Code::Blocks* |
|-|-|-|-|-| 
| *Detect targets* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *Detect toolchain* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *Detect target files* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *Build target* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *Run target* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *Debug target* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *Autocompletion* | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |


## Setup
### VS Code
1. Install [vscode-cmake-tools](https://github.com/vector-of-bool/vscode-cmake-tools).

2. Change `"cmake.cmakePath"` option to `mcw`.

3. Create an empty `CMakeLists.txt` file in root of project.

### CLion
1. In Toolchain settings (File > Settings > Build, Execution, Deployment > Toolchains):
Change CMake option to path of `mcw`.

2. Create an empty `CMakeLists.txt` file in root of project.

### QtCreator
1. In CMake settings (Tools > Options... > Build & Run > CMake):
Add manual CMake option with path of `mcw`.

2. Create an empty `CMakeLists.txt` file in root of project.

### Code::Blocks
1. Generate Code::Blocks project: 

`mcw -G"CodeBlocks - Ninja" -DCMAKE_BUILD_TYPE=Debug <build-dir>`

2. In Code::Blocks open: `<build-dir>/<project-name>.cbp` 
