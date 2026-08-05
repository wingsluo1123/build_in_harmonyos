cmake_minimum_required(VERSION 3.15)
project(test_docbook C)

# TARGET_SO is passed from conanfile.py test() as a -D flag, pointing to
# the installed docbook.so path inside the package folder.
add_executable(test_docbook test.c)
target_compile_definitions(test_docbook PRIVATE TARGET_SO="${TARGET_SO}")
target_link_libraries(test_docbook PRIVATE ${CMAKE_DL_LIBS})
