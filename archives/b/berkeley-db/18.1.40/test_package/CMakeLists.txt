cmake_minimum_required(VERSION 3.15)
project(test_berkeley-db C)

# Find the package via Conan-generated CMakeDeps
find_package(berkeley-db REQUIRED)

add_executable(test_berkeley-db test.c)
target_link_libraries(test_berkeley-db berkeley-db::berkeley-db)

enable_testing()
add_test(NAME test_berkeley-db COMMAND test_berkeley-db)
