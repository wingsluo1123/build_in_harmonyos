cmake_minimum_required(VERSION 3.15)
project(test_gsm C)

# Find the package via Conan-generated CMakeDeps
find_package(gsm REQUIRED)

add_executable(test_gsm test.c)
target_link_libraries(test_gsm gsm::gsm)

enable_testing()
add_test(NAME test_gsm COMMAND test_gsm)
