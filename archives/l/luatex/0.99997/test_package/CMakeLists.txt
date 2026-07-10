cmake_minimum_required(VERSION 3.15)
project(test_luatex C)

# Find the package via Conan-generated CMakeDeps
find_package(luatex REQUIRED)

add_executable(test_luatex test.c)
target_link_libraries(test_luatex luatex::luatex)

enable_testing()
add_test(NAME test_luatex COMMAND test_luatex)
