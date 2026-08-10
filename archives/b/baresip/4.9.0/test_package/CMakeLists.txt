cmake_minimum_required(VERSION 3.15)
project(test_baresip C)

find_package(baresip REQUIRED)
find_package(re REQUIRED)

add_executable(test_baresip test_baresip.c)
target_link_libraries(test_baresip PRIVATE baresip::baresip re::re)
