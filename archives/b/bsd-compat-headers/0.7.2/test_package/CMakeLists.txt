cmake_minimum_required(VERSION 3.15)
project(test_bsd_compat_headers C)

find_package(bsd-compat-headers REQUIRED)

add_executable(test_bsd_compat_headers test.c)
target_link_libraries(test_bsd_compat_headers bsd-compat-headers::bsd-compat-headers)

enable_testing()
add_test(NAME test_bsd_compat_headers COMMAND test_bsd_compat_headers)
