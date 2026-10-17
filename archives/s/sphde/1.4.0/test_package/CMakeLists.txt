cmake_minimum_required(VERSION 3.15)
project(test_sphde C)

# sphde 无 CMake config 包，手动定位头文件与库。
find_path(SPHDE_INCLUDE_DIR "sassim.h" PATH_SUFFIXES "sphde")
find_path(SPHDE_INCLUDE_DIR2 "sassimpleheap.h" PATH_SUFFIXES "sphde")
find_library(SPHDE_LIB "sphde")

add_executable(test_sphde test.c)
target_include_directories(test_sphde PRIVATE ${SPHDE_INCLUDE_DIR} ${SPHDE_INCLUDE_DIR2})
# SPHDE 依赖 librt/pthread/m
target_link_libraries(test_sphde ${SPHDE_LIB} rt pthread m)

enable_testing()
add_test(NAME test_sphde COMMAND test_sphde)
