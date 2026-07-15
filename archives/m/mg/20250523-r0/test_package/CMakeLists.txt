cmake_minimum_required(VERSION 3.15)
project(test_mg C)

# Find the package via Conan-generated CMakeDeps
find_package(mg REQUIRED)

add_executable(test_mg test.c)
target_link_libraries(test_mg mg::mg)

enable_testing()
add_test(NAME test_mg COMMAND test_mg)
