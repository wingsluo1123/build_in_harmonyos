cmake_minimum_required(VERSION 3.15)
project(test_xetex C)

# Find the package via Conan-generated CMakeDeps
find_package(xetex REQUIRED)

add_executable(test_xetex test.c)
target_link_libraries(test_xetex xetex::xetex)

enable_testing()
add_test(NAME test_xetex COMMAND test_xetex)
