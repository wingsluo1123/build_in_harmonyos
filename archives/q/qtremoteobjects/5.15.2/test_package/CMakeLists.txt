cmake_minimum_required(VERSION 3.15)
project(test_qtremoteobjects CXX)

# Find the package via Conan-generated CMakeDeps
find_package(qtremoteobjects REQUIRED)

add_executable(test_qtremoteobjects test.cpp)
target_link_libraries(test_qtremoteobjects qtremoteobjects::qtremoteobjects)

enable_testing()
add_test(NAME test_qtremoteobjects COMMAND test_qtremoteobjects)
