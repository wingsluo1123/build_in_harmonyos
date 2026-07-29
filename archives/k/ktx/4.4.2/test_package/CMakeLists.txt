cmake_minimum_required(VERSION 3.15)
project(test_ktx C)

find_package(KTX REQUIRED)

add_executable(test_ktx test_ktx.c)
target_link_libraries(test_ktx PRIVATE ktx)

enable_testing()
add_test(NAME test_ktx COMMAND test_ktx)
