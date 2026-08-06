cmake_minimum_required(VERSION 3.15)
project(test_libsoup C)

# Find libsoup and glib via Conan-generated CMakeDeps
find_package(libsoup REQUIRED)
find_package(glib REQUIRED)

add_executable(test_libsoup test.c)
target_link_libraries(test_libsoup libsoup::libsoup glib::glib)

enable_testing()
add_test(NAME test_libsoup COMMAND test_libsoup)
