cmake_minimum_required(VERSION 3.15)
project(test_buildifier C)

# Find the package via Conan-generated CMakeDeps
find_package(buildifier REQUIRED)

add_executable(test_buildifier test.c)
target_link_libraries(test_buildifier buildifier::buildifier)

enable_testing()
add_test(NAME test_buildifier COMMAND test_buildifier)
