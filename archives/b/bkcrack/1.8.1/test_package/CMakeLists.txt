cmake_minimum_required(VERSION 3.15)
project(test_bkcrack C)

# Find the package via Conan-generated CMakeDeps
find_package(bkcrack REQUIRED)

add_executable(test_bkcrack test.c)
target_link_libraries(test_bkcrack bkcrack::bkcrack)

enable_testing()
add_test(NAME test_bkcrack COMMAND test_bkcrack)
