incdir = include_directories(['inc', 'library_one', 'library_two'])

subdir('library_one')
subdir('library_two')

main = executable('main',
                  'main.cpp',
                  link_with: [library_one, library_two],
                  include_directories: incdir)
