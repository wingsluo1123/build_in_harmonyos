cmake_minimum_required(VERSION 3.20)
project(libwraster_test_package C)

set(CMAKE_C_EXTENSIONS ON)

find_package(libwraster CONFIG REQUIRED)

add_executable(libwraster_test test.c)
target_link_libraries(libwraster_test PRIVATE libwraster::libwraster)
target_compile_options(libwraster_test PRIVATE -Wall -Wextra -Werror)

add_executable(libwraster_consumer consumer.c)
target_link_libraries(libwraster_consumer PRIVATE libwraster::libwraster)
target_compile_options(libwraster_consumer PRIVATE -Wall -Wextra -Werror)
