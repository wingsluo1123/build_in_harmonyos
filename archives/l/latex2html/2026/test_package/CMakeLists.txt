cmake_minimum_required(VERSION 3.15)
project(test_latex2html C)

# Find the package via Conan-generated CMakeDeps
find_package(latex2html REQUIRED)

add_executable(test_latex2html test.c)
target_link_libraries(test_latex2html latex2html::latex2html)

enable_testing()
add_test(NAME test_latex2html COMMAND test_latex2html)
