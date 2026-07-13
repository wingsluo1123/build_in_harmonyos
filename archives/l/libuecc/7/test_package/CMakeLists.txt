cmake_minimum_required(VERSION 3.15)
project(test_libuecc C)

# Find the package via Conan-generated CMakeDeps
find_package(libuecc REQUIRED)

add_executable(test_libuecc test.c)
target_link_libraries(test_libuecc libuecc::libuecc)

enable_testing()
add_test(NAME test_libuecc COMMAND test_libuecc)
