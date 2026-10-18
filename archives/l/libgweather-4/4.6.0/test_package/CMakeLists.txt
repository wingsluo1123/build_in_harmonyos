cmake_minimum_required(VERSION 3.15)
project(test_libgweather4 C)

# CMakeDeps target (NOT pkg_check_modules): pkg-config's recursive Libs
# line carries `-l:ld-musl-aarch64.so.1` which cmake's link-flag splitting
# mangles on this host (geocode-glib test_package precedent). The CMakeDeps
# target links libraries directly without the pc Libs passthrough.
find_package(gweather4 REQUIRED CONFIG)
find_package(glib REQUIRED)

add_executable(test_libgweather4 test.c)
target_link_libraries(test_libgweather4 gweather4::gweather4 glib::glib)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_libgweather4 PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_libgweather4 COMMAND $<TARGET_FILE:test_libgweather4>)
