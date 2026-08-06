cmake_minimum_required(VERSION 3.15)
project(test_talloc C)

# Find the package via Conan-generated CMakeDeps
find_package(talloc REQUIRED)

add_executable(test_talloc test.c)
target_link_libraries(test_talloc talloc::talloc)

enable_testing()
add_test(NAME test_talloc COMMAND test_talloc)
