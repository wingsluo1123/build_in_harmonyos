cmake_minimum_required(VERSION 3.15)
project(test_fuse C)

find_package(fuse REQUIRED)

add_executable(test_fuse test.c pthread_stubs.c)
target_link_libraries(test_fuse fuse::fuse)
# fuse_common.h enforces _FILE_OFFSET_BITS=64 via #error (also declared by the
# recipe's cpp_info.defines; repeated here so the test builds stand-alone)
target_compile_definitions(test_fuse PRIVATE _FILE_OFFSET_BITS=64)

enable_testing()
add_test(NAME test_fuse COMMAND test_fuse)
