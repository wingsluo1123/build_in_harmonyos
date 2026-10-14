cmake_minimum_required(VERSION 3.15)
project(svox_test LANGUAGES C)

find_package(svox CONFIG REQUIRED)
add_executable(test_svox test_svox.c)
target_link_libraries(test_svox PRIVATE svox::svox)

enable_testing()
add_test(NAME test_svox COMMAND test_svox)
