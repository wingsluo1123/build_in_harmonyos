cmake_minimum_required(VERSION 3.15)
project(test_lwdtc C)

# Find the package via Conan-generated CMakeDeps
find_package(lwdtc REQUIRED)

add_executable(test_lwdtc test.c)
target_link_libraries(test_lwdtc lwdtc::lwdtc)

enable_testing()
add_test(NAME test_lwdtc COMMAND test_lwdtc)
