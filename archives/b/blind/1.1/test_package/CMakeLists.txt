cmake_minimum_required(VERSION 3.15)
project(test_blind C)

# Find the package via Conan-generated CMakeDeps
find_package(blind REQUIRED)

add_executable(test_blind test.c)
target_link_libraries(test_blind blind::blind)

enable_testing()
add_test(NAME test_blind COMMAND test_blind)
