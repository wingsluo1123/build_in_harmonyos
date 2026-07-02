cmake_minimum_required(VERSION 3.15)
project(test_mdbook C)

# Find the package via Conan-generated CMakeDeps
find_package(mdbook REQUIRED)

add_executable(test_mdbook test.c)
target_link_libraries(test_mdbook mdbook::mdbook)

enable_testing()
add_test(NAME test_mdbook COMMAND test_mdbook)
