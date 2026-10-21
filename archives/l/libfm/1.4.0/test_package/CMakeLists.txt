cmake_minimum_required(VERSION 3.16)
project(libfm_extra_consumer LANGUAGES C)

find_package(libfm-extra REQUIRED CONFIG)

# 手动查找 glib（glib 无 CMake config 文件）
find_path(GLIB_INCLUDE_DIR glib.h
    PATHS $ENV{GLIB_ROOT}/include
    PATH_SUFFIXES glib-2.0)
find_path(GLIB_CONFIG_DIR glibconfig.h
    PATHS $ENV{GLIB_ROOT}/lib
    PATH_SUFFIXES glib-2.0/include)
find_library(GLIB_LIBRARY NAMES glib-2.0)

add_executable(test_libfm_extra_consumer test_libfm_extra_consumer.c)
target_include_directories(test_libfm_extra_consumer PRIVATE ${GLIB_INCLUDE_DIR} ${GLIB_CONFIG_DIR})
target_link_libraries(test_libfm_extra_consumer PRIVATE libfm::libfm ${GLIB_LIBRARY})

enable_testing()
add_test(NAME consumer_xml_parse COMMAND test_libfm_extra_consumer)
