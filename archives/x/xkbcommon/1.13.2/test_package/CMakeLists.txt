cmake_minimum_required(VERSION 3.15)
project(test_xkbcommon C)

# Find the package via Conan-generated CMakeDeps
find_package(xkbcommon REQUIRED)

add_executable(test_xkbcommon test.c)
target_link_libraries(test_xkbcommon xkbcommon::xkbcommon)

enable_testing()
add_test(NAME test_xkbcommon COMMAND test_xkbcommon)
