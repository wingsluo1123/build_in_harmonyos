cmake_minimum_required(VERSION 3.15)
project(test_uSockets C)

# Find the package via Conan-generated CMakeDeps
find_package(usockets REQUIRED)

add_executable(test_usockets test.c)
target_link_libraries(test_usockets usockets::usockets)

enable_testing()
add_test(NAME test_uSockets COMMAND test_uSockets)
