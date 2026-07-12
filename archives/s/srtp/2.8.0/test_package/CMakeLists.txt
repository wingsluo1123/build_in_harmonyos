cmake_minimum_required(VERSION 3.15)
project(test_srtp C)

# Find the package via Conan-generated CMakeDeps
find_package(srtp REQUIRED)

add_executable(test_srtp test.c)
target_link_libraries(test_srtp srtp::srtp)

enable_testing()
add_test(NAME test_srtp COMMAND test_srtp)
