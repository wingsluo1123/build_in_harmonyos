cmake_minimum_required(VERSION 3.15)
project(test_boost-build C)

# Find the package via Conan-generated CMakeDeps
find_package(boost-build REQUIRED)

add_executable(test_boost-build test.c)
target_link_libraries(test_boost-build boost-build::boost-build)

enable_testing()
add_test(NAME test_boost-build COMMAND test_boost-build)
