cmake_minimum_required(VERSION 3.15)
project(test_cdparanoia C)

find_package(cdparanoia REQUIRED)

add_executable(test_cdparanoia test.c)
target_link_libraries(test_cdparanoia cdparanoia::cdparanoia)

enable_testing()
add_test(NAME test_cdparanoia COMMAND test_cdparanoia)
