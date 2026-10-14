cmake_minimum_required(VERSION 3.27)
project(test_chewing C)

find_package(Chewing REQUIRED)

add_executable(test_chewing test_chewing.c)
target_link_libraries(test_chewing Chewing::chewing)

enable_testing()
add_test(NAME test_chewing COMMAND test_chewing)
