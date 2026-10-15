cmake_minimum_required(VERSION 3.15)
project(test_cpp-async CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpp-async REQUIRED)

add_executable(test_cpp-async test.cpp)
target_link_libraries(test_cpp-async cpp-async::cpp-async)
target_compile_features(test_cpp-async PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_cpp-async COMMAND test_cpp-async)
