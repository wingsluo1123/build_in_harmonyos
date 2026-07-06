cmake_minimum_required(VERSION 3.15)
project(test_bonnie++ C)

# Find the package via Conan-generated CMakeDeps
find_package(bonnie++ REQUIRED)

add_executable(test_bonnie++ test.c)
target_link_libraries(test_bonnie++ bonnie++::bonnie++)

enable_testing()
add_test(NAME test_bonnie++ COMMAND test_bonnie++)
