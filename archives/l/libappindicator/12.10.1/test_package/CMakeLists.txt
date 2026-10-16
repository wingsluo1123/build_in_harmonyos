cmake_minimum_required(VERSION 3.15)
project(test_package C)

# 经 Conan 生成的 CMakeDeps 配置找到被测包；头文件搜索路径（libappindicator/
# libdbusmenu-glib/libdbusmenu-gtk 三种前缀）由 recipe 的 cpp_info.includedirs
# 提供，这里不额外手写路径。
find_package(libappindicator REQUIRED)

# 1) 鸿蒙特有消费者端到端用例（rule12，真实运行）
add_executable(test_package test_consumer.c)
target_link_libraries(test_package PRIVATE libappindicator::libappindicator)
target_compile_definitions(test_package PRIVATE E2E_SRCDIR="${CMAKE_CURRENT_SOURCE_DIR}")

# 2) 上游 tests/test-libappindicator.c 逐字复制（未修改）：
#    9 个 g_test 用例，真实编译 + 真实执行（rule4）。
#    上游源码用 SRCDIR 拼接 tests/ 下的 .desktop 夹具路径。
add_executable(test-libappindicator upstream-test-libappindicator.c)
target_compile_definitions(test-libappindicator PRIVATE SRCDIR="${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(test-libappindicator PRIVATE libappindicator::libappindicator)
