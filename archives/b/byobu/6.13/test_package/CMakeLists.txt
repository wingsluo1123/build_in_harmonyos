cmake_minimum_required(VERSION 3.15)
project(test_byobu C)

# Find the package via Conan-generated CMakeDeps
find_package(byobu REQUIRED)

add_executable(test_byobu test.c)
target_link_libraries(test_byobu byobu::byobu)

enable_testing()
add_test(NAME test_byobu COMMAND test_byobu)
