cmake_minimum_required(VERSION 3.15)
project(test_libzmf CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libzmf REQUIRED)

add_executable(test_libzmf test.cpp)
target_link_libraries(test_libzmf libzmf::libzmf)

enable_testing()
add_test(NAME test_libzmf COMMAND test_libzmf)
