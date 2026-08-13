cmake_minimum_required(VERSION 3.15)
project(test_aiosignal C)

# Find the package via Conan-generated CMakeDeps
find_package(aiosignal REQUIRED)

add_executable(test_aiosignal test.c)
target_link_libraries(test_aiosignal aiosignal::aiosignal)

enable_testing()
add_test(NAME test_aiosignal COMMAND test_aiosignal)
