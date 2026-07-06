cmake_minimum_required(VERSION 3.15)
project(test_bwfmetaedit C)

# Find the package via Conan-generated CMakeDeps
find_package(bwfmetaedit REQUIRED)

add_executable(test_bwfmetaedit test.c)
target_link_libraries(test_bwfmetaedit bwfmetaedit::bwfmetaedit)

enable_testing()
add_test(NAME test_bwfmetaedit COMMAND test_bwfmetaedit)
