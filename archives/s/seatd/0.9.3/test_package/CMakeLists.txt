cmake_minimum_required(VERSION 3.15)
project(test_seatd C)

# Find the package via Conan-generated CMakeDeps
find_package(seatd REQUIRED)

add_executable(test_seatd test_package.c)
target_link_libraries(test_seatd seatd::seatd)

enable_testing()
add_test(NAME test_seatd COMMAND test_seatd)
