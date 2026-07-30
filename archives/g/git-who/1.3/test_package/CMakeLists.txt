cmake_minimum_required(VERSION 3.5)
project(test_git_who)
add_executable(test_git_who test.c)
# No target_link_libraries — just verify the binary exists via test code
