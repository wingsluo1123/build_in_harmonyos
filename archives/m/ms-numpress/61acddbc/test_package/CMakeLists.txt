cmake_minimum_required(VERSION 3.15)
project(test_ms-numpress CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ms-numpress REQUIRED)

add_executable(test_ms-numpress test.cpp)
target_link_libraries(test_ms-numpress ms-numpress::ms-numpress)
target_compile_features(test_ms-numpress PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_ms-numpress COMMAND test_ms-numpress)