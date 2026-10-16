cmake_minimum_required(VERSION 3.15)
project(phast_test C)

find_package(phast REQUIRED)

add_executable(test_phast test.c)
target_link_libraries(test_phast PRIVATE phast::phast)

enable_testing()
add_test(NAME test_phast COMMAND test_phast)
