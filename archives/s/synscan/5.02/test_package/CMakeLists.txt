cmake_minimum_required(VERSION 3.15)
project(test_synscan_api LANGUAGES C)

find_package(synscan CONFIG REQUIRED)

add_executable(test_synscan_api test.c)
target_link_libraries(test_synscan_api PRIVATE synscan::synscan)
target_compile_features(test_synscan_api PRIVATE c_std_99)
target_compile_options(test_synscan_api PRIVATE -Wall -Wextra)
