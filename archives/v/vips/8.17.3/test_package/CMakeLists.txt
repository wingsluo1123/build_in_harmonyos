cmake_minimum_required(VERSION 3.15)
project(test_vips C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(VIPS REQUIRED vips)

add_executable(test_vips test.c)
target_include_directories(test_vips PRIVATE
    ${VIPS_INCLUDE_DIRS}
    /storage/Users/currentUser/usr/local/include/glib-2.0
    /storage/Users/currentUser/usr/local/lib/glib-2.0/include
)
target_link_directories(test_vips PRIVATE
    /storage/Users/currentUser/usr/local/lib
)
target_link_libraries(test_vips ${VIPS_LIBRARIES})

enable_testing()
add_test(NAME test_vips COMMAND test_vips)
