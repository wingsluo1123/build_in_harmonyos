cmake_minimum_required(VERSION 3.15)
project(test_libjpeg-turbo C)

# Find the package via Conan-generated CMakeDeps
find_package(libjpeg-turbo REQUIRED)

add_executable(test_libjpeg-turbo test.c)
target_link_libraries(test_libjpeg-turbo libjpeg-turbo::libjpeg-turbo)

enable_testing()
add_test(NAME test_libjpeg-turbo COMMAND test_libjpeg-turbo)
