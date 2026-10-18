cmake_minimum_required(VERSION 3.15)
project(test_GTK C)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK REQUIRED IMPORTED_TARGET gtk+-3.0)
# 3.24.43.1 为 X11 后端变体：必须安装 gtk+-x11-3.0.pc。
# X11-only 消费者（如 vino 3.22.0）正是通过该 pc 文件探测 X11 后端，缺失即 configure 失败。
pkg_check_modules(GTK_X11 REQUIRED gtk+-x11-3.0)
add_executable(test_GTK test.c)
target_link_libraries(test_GTK PkgConfig::GTK)
# Fallback: also support Conan CMakeDeps find_package
# find_package(GTK QUIET)
# if(GTK_FOUND)
#   target_link_libraries(test_GTK GTK::GTK)
# endif()
enable_testing()
add_test(NAME test_GTK COMMAND test_GTK)
