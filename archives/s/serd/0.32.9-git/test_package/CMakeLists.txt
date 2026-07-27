cmake_minimum_required(VERSION 3.15)
project(test_serd C)

# Find the package via Conan-generated CMakeDeps
find_package(serd REQUIRED)

add_executable(test_serd test.c)
target_link_libraries(test_serd serd::serd)

enable_testing()
add_test(NAME test_serd COMMAND test_serd)
