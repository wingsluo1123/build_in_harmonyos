cmake_minimum_required(VERSION 3.15)
project(test_openscenegraph CXX)

# Find the package via Conan-generated CMakeDeps
find_package(openscenegraph REQUIRED)

# Get include dirs from the conan-generated target
add_executable(test_openscenegraph test_openscenegraph.cpp)
target_link_libraries(test_openscenegraph openscenegraph::openscenegraph)
set_target_properties(test_openscenegraph PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_openscenegraph COMMAND test_openscenegraph)
