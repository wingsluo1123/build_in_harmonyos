cmake_minimum_required(VERSION 3.15)
project(test_scst C)

# Find the package via Conan-generated CMakeDeps
find_package(scst REQUIRED)

add_executable(test_scst test.c)
target_link_libraries(test_scst scst::scst)

enable_testing()
add_test(NAME test_scst COMMAND test_scst)
