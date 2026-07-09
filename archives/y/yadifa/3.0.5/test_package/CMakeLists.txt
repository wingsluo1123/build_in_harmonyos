cmake_minimum_required(VERSION 3.15)
project(test_yadifa C)

# Find the package via Conan-generated CMakeDeps
find_package(yadifa REQUIRED)

add_executable(test_yadifa test.c)
target_link_libraries(test_yadifa yadifa::yadifa)

enable_testing()
add_test(NAME test_yadifa COMMAND test_yadifa)
