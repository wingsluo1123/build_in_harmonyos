cmake_minimum_required(VERSION 3.15)
project(test_alac C)

# Find the package via Conan-generated CMakeDeps
find_package(alac REQUIRED)

add_executable(test_alac test.c)
target_link_libraries(test_alac alac::alac)

enable_testing()
add_test(NAME test_alac COMMAND test_alac)
