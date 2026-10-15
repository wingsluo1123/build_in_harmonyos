cmake_minimum_required(VERSION 3.15)
project(test_metal CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(metal REQUIRED)

add_executable(test_metal test.cpp)
target_link_libraries(test_metal metal::metal)

enable_testing()
add_test(NAME test_metal COMMAND test_metal)