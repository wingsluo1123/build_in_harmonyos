cmake_minimum_required(VERSION 3.15)
project(test_epub C)

# TARGET_SO is passed from conanfile.py test() as a -D flag, pointing to
# the installed epub.so path inside the package folder.
add_executable(test_epub test.c)
target_compile_definitions(test_epub PRIVATE TARGET_SO="${TARGET_SO}")
target_link_libraries(test_epub PRIVATE ${CMAKE_DL_LIBS})
