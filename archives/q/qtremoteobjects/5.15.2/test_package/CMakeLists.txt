cmake_minimum_required(VERSION 3.15)
project(test_qtremoteobjects CXX)

# OHOS 平台限制：stripped ELF 无法 dlopen
# test_package 使用 conanfile.py 中的 readelf/nm 做静态验证
# 此 CMakeLists.txt 仅作为占位符，不链接 Qt5 库
add_executable(test_qtremoteobjects test.cpp)
enable_testing()
add_test(NAME test_qtremoteobjects COMMAND test_qtremoteobjects)
