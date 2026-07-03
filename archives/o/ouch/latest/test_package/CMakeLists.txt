cmake_minimum_required(VERSION 3.15)
project(test_ouch C)

# Find the package via Conan-generated CMakeDeps
find_package(ouch REQUIRED)

add_executable(test_ouch test.c)
target_link_libraries(test_ouch ouch::ouch)

enable_testing()
add_test(NAME test_ouch COMMAND test_ouch)
