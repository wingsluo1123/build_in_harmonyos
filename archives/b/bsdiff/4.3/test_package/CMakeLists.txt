cmake_minimum_required(VERSION 3.15)
project(test_bsdiff C)

# Find the package via Conan-generated CMakeDeps
find_package(bsdiff REQUIRED)

add_executable(test_bsdiff test.c)
target_link_libraries(test_bsdiff bsdiff::bsdiff)

enable_testing()
add_test(NAME test_bsdiff COMMAND test_bsdiff)
