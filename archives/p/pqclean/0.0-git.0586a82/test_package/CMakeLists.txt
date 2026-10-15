cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(PQClean CONFIG REQUIRED)

add_executable(test_pqclean test_pqclean.c)
target_link_libraries(test_pqclean PRIVATE PQClean::PQClean)
target_compile_features(test_pqclean PRIVATE c_std_99)
