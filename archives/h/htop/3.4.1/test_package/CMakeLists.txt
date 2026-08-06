cmake_minimum_required(VERSION 3.15)
project(test_htop C)

# Find the package via Conan-generated CMakeDeps
find_package(htop REQUIRED)

add_executable(test_htop test.c)
target_link_libraries(test_htop htop::htop)

enable_testing()
add_test(NAME test_htop COMMAND test_htop)
