cmake_minimum_required(VERSION 3.15)
project(test_hwloc C)

# Find the package via Conan-generated CMakeDeps
find_package(hwloc REQUIRED)

add_executable(test_hwloc test.c)
target_link_libraries(test_hwloc hwloc::hwloc)

enable_testing()
add_test(NAME test_hwloc COMMAND test_hwloc)
