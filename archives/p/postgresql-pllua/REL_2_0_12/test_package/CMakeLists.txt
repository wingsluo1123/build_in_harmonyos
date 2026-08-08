cmake_minimum_required(VERSION 3.15)
project(test_pllua C)

# pllua.so is a PostgreSQL extension loaded at runtime via dlopen,
# not linked at compile time. No find_package needed.
add_executable(test_pllua src/test_pllua.c)
target_link_libraries(test_pllua ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_pllua COMMAND test_pllua)
