cmake_minimum_required(VERSION 3.15)
project(test_mir C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(mir REQUIRED)

add_executable(test_mir test.c)
target_link_libraries(test_mir mir::mir)
target_compile_options(test_mir PRIVATE -UNDEBUG)

enable_testing()
add_test(NAME test_mir COMMAND test_mir)
