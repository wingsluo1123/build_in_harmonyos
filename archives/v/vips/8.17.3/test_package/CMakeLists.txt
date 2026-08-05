cmake_minimum_required(VERSION 3.15)
project(test_vips C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(VIPS REQUIRED vips)
pkg_check_modules(GLIB REQUIRED glib-2.0)

add_executable(test_vips test.c)
target_include_directories(test_vips PRIVATE
    ${VIPS_INCLUDE_DIRS}
    ${GLIB_INCLUDE_DIRS}
)
target_link_directories(test_vips PRIVATE
    ${GLIB_LIBRARY_DIRS}
)
target_link_libraries(test_vips ${VIPS_LIBRARIES} ${GLIB_LIBRARIES})

enable_testing()
add_test(NAME test_vips COMMAND test_vips)
