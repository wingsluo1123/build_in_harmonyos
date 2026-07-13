cmake_minimum_required(VERSION 3.15)
project(test_pth C)

# Find the package via Conan-generated CMakeDeps
find_package(pth REQUIRED)

add_executable(test_pth test.c)
target_link_libraries(test_pth pth::pth)

enable_testing()
add_test(NAME test_pth COMMAND test_pth)
