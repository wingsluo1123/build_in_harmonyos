cmake_minimum_required(VERSION 3.15)
project(test_dante C)

find_package(dante REQUIRED)

add_executable(test_dante test_dante.c)
target_link_libraries(test_dante dante::dante)
# OHOS: allow undefined symbols in shared libs (bindresvport not available)
target_link_options(test_dante PRIVATE "-Wl,--allow-shlib-undefined")

enable_testing()
add_test(NAME dante_api_test COMMAND test_dante)
