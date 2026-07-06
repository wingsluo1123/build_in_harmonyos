cmake_minimum_required(VERSION 3.15)
project(test_bcal C)

# Find the package via Conan-generated CMakeDeps
find_package(bcal REQUIRED)

add_executable(test_bcal test.c)
target_link_libraries(test_bcal bcal::bcal)

enable_testing()
add_test(NAME test_bcal COMMAND test_bcal)
