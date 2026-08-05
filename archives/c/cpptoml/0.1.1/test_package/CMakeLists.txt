cmake_minimum_required(VERSION 3.15)
project(test_cpptoml CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpptoml REQUIRED)

add_executable(test_cpptoml test.cpp)
target_link_libraries(test_cpptoml cpptoml::cpptoml)
set_target_properties(test_cpptoml PROPERTIES
  CXX_STANDARD 11
  CXX_EXTENSIONS OFF
  CXX_STANDARD_REQUIRED YES)

enable_testing()
add_test(NAME test_cpptoml COMMAND test_cpptoml)
