cmake_minimum_required(VERSION 3.15)
project(test_bmd-tools C)

# Find the package via Conan-generated CMakeDeps
find_package(bmd-tools REQUIRED)

add_executable(test_bmd-tools test.c)
target_link_libraries(test_bmd-tools bmd-tools::bmd-tools)

enable_testing()
add_test(NAME test_bmd-tools COMMAND test_bmd-tools)
