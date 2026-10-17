cmake_minimum_required(VERSION 3.15)
project(test_totem-pl-parser C)

# Find the package via Conan-generated CMakeDeps
find_package(totem-pl-parser REQUIRED CONFIG)

add_executable(test_totem-pl-parser test.c)
target_link_libraries(test_totem-pl-parser totem-pl-parser::totem-pl-parser)

enable_testing()
add_test(NAME test_totem-pl-parser COMMAND test_totem-pl-parser)
