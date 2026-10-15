cmake_minimum_required(VERSION 3.15)
project(test_lksctp-tools C)

# Find the package via Conan-generated CMakeDeps
find_package(lksctp-tools REQUIRED)

add_executable(test_lksctp-tools test.c)
target_link_libraries(test_lksctp-tools lksctp-tools::lksctp-tools)

enable_testing()
add_test(NAME test_lksctp-tools COMMAND test_lksctp-tools)
