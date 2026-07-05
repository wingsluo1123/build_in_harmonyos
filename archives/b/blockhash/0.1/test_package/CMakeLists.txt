cmake_minimum_required(VERSION 3.15)
project(test_blockhash C)

# Find the package via Conan-generated CMakeDeps
find_package(blockhash REQUIRED)

add_executable(test_blockhash test.c)
target_link_libraries(test_blockhash blockhash::blockhash)

enable_testing()
add_test(NAME test_blockhash COMMAND test_blockhash)
