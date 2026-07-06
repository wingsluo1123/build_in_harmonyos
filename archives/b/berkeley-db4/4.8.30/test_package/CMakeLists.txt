cmake_minimum_required(VERSION 3.15)
project(test_berkeley-db4 C)

# Find the package via Conan-generated CMakeDeps
find_package(berkeley-db4 REQUIRED)

add_executable(test_berkeley-db4 test.c)
target_link_libraries(test_berkeley-db4 berkeley-db4::berkeley-db4)

enable_testing()
add_test(NAME test_berkeley-db4 COMMAND test_berkeley-db4)
