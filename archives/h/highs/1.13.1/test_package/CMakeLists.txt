cmake_minimum_required(VERSION 3.15)
project(test_highs CXX)

# Find the package via Conan-generated CMakeDeps
find_package(highs REQUIRED)

add_executable(test_highs test.cpp)
target_link_libraries(test_highs highs::highs)
# HiGHS headers are installed under include/highs/, add subdir for internal includes
target_include_directories(test_highs PRIVATE $<TARGET_PROPERTY:highs::highs,INTERFACE_INCLUDE_DIRECTORIES>/highs)

enable_testing()
add_test(NAME test_highs COMMAND test_highs)
