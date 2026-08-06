cmake_minimum_required(VERSION 3.5)
project(test_libgphoto2 C)

find_package(libgphoto2 REQUIRED)

add_executable(test_libgphoto2 test_libgphoto2.c)
target_link_libraries(test_libgphoto2 PRIVATE libgphoto2::libgphoto2)

enable_testing()
add_test(NAME test_libgphoto2 COMMAND test_libgphoto2)
