cmake_minimum_required(VERSION 3.15)
project(test_json_glib C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(JSON_GLIB REQUIRED IMPORTED_TARGET json-glib-1.0)

add_executable(test_json_glib test.c)
target_link_libraries(test_json_glib PkgConfig::JSON_GLIB)

enable_testing()
add_test(NAME test_json_glib COMMAND test_json_glib)
