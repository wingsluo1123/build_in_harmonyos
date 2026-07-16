cmake_minimum_required(VERSION 3.15)
project(test_torchvision CXX)

# Find the package via Conan-generated CMakeDeps
find_package(torchvision REQUIRED)

add_executable(test_torchvision test.cpp)
target_link_libraries(test_torchvision torchvision::torchvision)

enable_testing()
add_test(NAME test_torchvision COMMAND test_torchvision)
