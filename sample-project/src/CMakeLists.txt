add_subdirectory(library)

include_directories(library)

add_executable(main main.cpp)
target_link_libraries(main library)
