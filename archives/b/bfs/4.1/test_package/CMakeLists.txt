cmake_minimum_required(VERSION 3.15)
project(test_bfs C)

# Find the package via Conan-generated CMakeDeps
find_package(bfs REQUIRED)

add_executable(test_bfs test.c)
target_link_libraries(test_bfs bfs::bfs)

enable_testing()
add_test(NAME test_bfs COMMAND test_bfs)
