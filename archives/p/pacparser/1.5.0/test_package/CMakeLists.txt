cmake_minimum_required(VERSION 3.15)
project(test_pacparser C)

# Find the package via Conan-generated CMakeDeps
find_package(pacparser REQUIRED)

add_executable(test_pacparser test.c)
target_link_libraries(test_pacparser pacparser::pacparser)

enable_testing()
add_test(NAME test_pacparser COMMAND test_pacparser)
