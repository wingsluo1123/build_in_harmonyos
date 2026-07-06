cmake_minimum_required(VERSION 3.15)
project(test_bsd-compat-headers C)

# Find the package via Conan-generated CMakeDeps
find_package(bsd-compat-headers REQUIRED)

add_executable(test_bsd-compat-headers test.c)
target_link_libraries(test_bsd-compat-headers bsd-compat-headers::bsd-compat-headers)

enable_testing()
add_test(NAME test_bsd-compat-headers COMMAND test_bsd-compat-headers)
