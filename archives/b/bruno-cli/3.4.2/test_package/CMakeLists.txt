cmake_minimum_required(VERSION 3.15)
project(test_bruno-cli C)

# Find the package via Conan-generated CMakeDeps
find_package(bruno-cli REQUIRED)

add_executable(test_bruno-cli test.c)
target_link_libraries(test_bruno-cli bruno-cli::bruno-cli)

enable_testing()
add_test(NAME test_bruno-cli COMMAND test_bruno-cli)
