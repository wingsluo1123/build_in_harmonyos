cmake_minimum_required(VERSION 3.15)
project(test_sratom C)

# Find the package via Conan-generated CMakeDeps
find_package(sratom REQUIRED)

add_executable(test_sratom test.c)
target_link_libraries(test_sratom sratom::sratom)

enable_testing()
add_test(NAME test_sratom COMMAND test_sratom)
