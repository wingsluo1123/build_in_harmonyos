cmake_minimum_required(VERSION 3.15)
project(test_agg CXX)  # agg is template-only C++; test.cpp uses agg::pod_array

# Find the package via Conan-generated CMakeDeps
find_package(agg REQUIRED)

add_executable(test_agg test.cpp)
target_link_libraries(test_agg agg::agg)
set_target_properties(test_agg PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_agg COMMAND test_agg)
