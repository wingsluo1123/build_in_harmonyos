cmake_minimum_required(VERSION 3.15)
project(test_consumer CXX)

# Find the package via Conan-generated CMakeDeps
find_package(clreflect REQUIRED)

add_executable(test_consumer test_consumer.cpp)
target_link_libraries(test_consumer clreflect::clreflect)

enable_testing()
add_test(NAME test_consumer COMMAND test_consumer)
