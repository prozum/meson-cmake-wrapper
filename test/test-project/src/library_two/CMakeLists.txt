add_library(library_two SHARED library-two.cpp)
target_link_libraries(library_two library_one)