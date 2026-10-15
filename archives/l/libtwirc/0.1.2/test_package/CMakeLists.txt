cmake_minimum_required(VERSION 3.15)
project(test_libtwirc C)

# Find the package via Conan-generated CMakeDeps
find_package(libtwirc REQUIRED)

add_executable(test_libtwirc test.c)
target_link_libraries(test_libtwirc libtwirc::libtwirc)

enable_testing()
add_test(NAME test_libtwirc COMMAND test_libtwirc)
