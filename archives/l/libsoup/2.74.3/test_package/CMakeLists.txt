cmake_minimum_required(VERSION 3.15)
project(test_libsoup C)

# Find libsoup via Conan-generated CMakeDeps
find_package(libsoup REQUIRED)

# Use PkgConfig to find glib (CMakeDeps doesn't propagate glib include dirs)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0 gio-2.0)

add_executable(test_libsoup test.c)
target_link_libraries(test_libsoup libsoup::libsoup PkgConfig::GLIB)

enable_testing()
add_test(NAME test_libsoup COMMAND test_libsoup)
