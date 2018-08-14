add_subdirectory(library_one)
add_subdirectory(library_two)

include_directories(library_one)
include_directories(library_two)

add_executable(main main.cpp)
target_link_libraries(main library_one library_two)
