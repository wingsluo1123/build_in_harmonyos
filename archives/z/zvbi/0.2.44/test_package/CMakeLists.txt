cmake_minimum_required(VERSION 3.15)
project(test_zvbi C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(zvbi CONFIG REQUIRED)

add_executable(test_zvbi test_zvbi.c)
target_compile_options(test_zvbi PRIVATE -Wall -Wextra -Werror)
target_link_libraries(test_zvbi PRIVATE zvbi::zvbi)

enable_testing()
add_test(NAME test_zvbi COMMAND test_zvbi)
