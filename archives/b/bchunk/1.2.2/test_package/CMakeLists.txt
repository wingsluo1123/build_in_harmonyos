cmake_minimum_required(VERSION 3.15)
project(test_bchunk C)

# Find the package via Conan-generated CMakeDeps
find_package(bchunk REQUIRED)

add_executable(test_bchunk test.c)
target_link_libraries(test_bchunk bchunk::bchunk)

enable_testing()
add_test(NAME test_bchunk COMMAND test_bchunk)
