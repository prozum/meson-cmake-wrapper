incdir = include_directories('library')
subdir('library')
main = executable('main', 
                  'main.cpp',
                  link_with: library,
                  include_directories: incdir)
