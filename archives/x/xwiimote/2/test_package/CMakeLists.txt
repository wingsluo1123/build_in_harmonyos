cmake_minimum_required(VERSION 3.15)
project(test_xwiimote C)

# Find the package via Conan-generated CMakeDeps
find_package(xwiimote REQUIRED)

add_executable(test_xwiimote test.c)
target_link_libraries(test_xwiimote xwiimote::xwiimote)

enable_testing()
add_test(NAME test_xwiimote COMMAND test_xwiimote)
