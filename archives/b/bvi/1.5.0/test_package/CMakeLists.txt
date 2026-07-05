cmake_minimum_required(VERSION 3.15)
project(test_bvi C)

# Find the package via Conan-generated CMakeDeps
find_package(bvi REQUIRED)

add_executable(test_bvi test.c)
target_link_libraries(test_bvi bvi::bvi)

enable_testing()
add_test(NAME test_bvi COMMAND test_bvi)
