cmake_minimum_required(VERSION 3.15)
project(test_cpp-member-accessor CXX)

# Find the package via Conan-generated CMakeDeps
find_package(accessor REQUIRED)

add_executable(test_cpp-member-accessor test.cpp)
target_link_libraries(test_cpp-member-accessor accessor)

enable_testing()
add_test(NAME test_cpp-member-accessor COMMAND test_cpp-member-accessor)
