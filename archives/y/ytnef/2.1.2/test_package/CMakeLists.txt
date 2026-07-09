cmake_minimum_required(VERSION 3.15)
project(test_ytnef C)

# Find the package via Conan-generated CMakeDeps
find_package(ytnef REQUIRED)

add_executable(test_ytnef test.c)
target_link_libraries(test_ytnef ytnef::ytnef)

enable_testing()
add_test(NAME test_ytnef COMMAND test_ytnef)
