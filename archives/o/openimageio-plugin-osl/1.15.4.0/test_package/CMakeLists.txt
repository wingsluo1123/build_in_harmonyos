cmake_minimum_required(VERSION 3.15)
project(test_osl CXX)

# Find the OSL package via Conan-generated CMakeDeps
find_package(OSL REQUIRED)

add_executable(test_osl src/test.cpp)
target_link_libraries(test_osl OSL::OSL)

enable_testing()
add_test(NAME test_osl COMMAND test_osl)
