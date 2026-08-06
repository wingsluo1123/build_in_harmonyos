cmake_minimum_required(VERSION 3.15)
project(test_notcurses C)

# Find the package via Conan-generated CMakeDeps
find_package(notcurses REQUIRED)

add_executable(test_notcurses test.c)
target_link_libraries(test_notcurses notcurses::notcurses)

enable_testing()
add_test(NAME test_notcurses COMMAND test_notcurses)
