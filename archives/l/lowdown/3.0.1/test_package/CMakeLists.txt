cmake_minimum_required(VERSION 3.15)
project(test_lowdown C)

# Find the package via Conan-generated CMakeDeps
find_package(lowdown REQUIRED)

add_executable(test_lowdown test.c)
target_link_libraries(test_lowdown lowdown::lowdown)
target_include_directories(test_lowdown PRIVATE ${lowdown_INCLUDE_DIRS})

enable_testing()
add_test(NAME test_lowdown COMMAND test_lowdown)
