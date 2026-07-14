cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(lp_solve REQUIRED)

enable_testing()

add_executable(test_lp_solve test_lp_solve.c)
target_link_libraries(test_lp_solve lp_solve::lp_solve)

add_test(NAME lp_solve_api_test COMMAND test_lp_solve)
