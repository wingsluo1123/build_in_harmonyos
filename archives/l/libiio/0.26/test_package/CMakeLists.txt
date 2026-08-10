cmake_minimum_required(VERSION 3.15)
project(test_iio C)

find_package(libiio REQUIRED)

add_executable(test_iio test_iio.c)
target_link_libraries(test_iio libiio::libiio)
set_target_properties(test_iio PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
)
