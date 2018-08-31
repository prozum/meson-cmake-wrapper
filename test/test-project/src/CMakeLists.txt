include_directories(inc library_one library_two)

add_subdirectory(library_one)
add_subdirectory(library_two)

add_executable(main main.cpp)
target_link_libraries(main library_one library_two)
