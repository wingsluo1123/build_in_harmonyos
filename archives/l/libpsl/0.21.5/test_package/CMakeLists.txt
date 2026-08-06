cmake_minimum_required(VERSION 3.15)
project(test_libpsl C)

# Find libpsl via Conan-generated CMakeDeps
find_package(libpsl REQUIRED)

add_executable(test_libpsl test.c)
target_link_libraries(test_libpsl libpsl::libpsl)

enable_testing()
add_test(NAME test_libpsl COMMAND test_libpsl)
