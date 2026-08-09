cmake_minimum_required(VERSION 3.15)
project(test_libgda C)

find_package(libgda REQUIRED)

add_executable(test_libgda src/test_libgda.c)
target_link_libraries(test_libgda libgda::libgda)

enable_testing()
add_test(NAME libgda_test COMMAND test_libgda)
