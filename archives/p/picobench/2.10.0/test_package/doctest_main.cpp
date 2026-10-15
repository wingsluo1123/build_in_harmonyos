// doctest_main.cpp — 上游测试入口 wrapper（等价还原 doctest-util 的 main 链接形态）
//
// 上游 test/CMakeLists.txt 经 CPM（doctest-util 0.1.2）的
// add_doctest_lib_test(basic basic.cpp) 注册测试——doctest-util 为每个测试
// 提供 doctest 官方 main 入口（doctest_with_main）。Conan doctest/2.4.11 包
// 仅暴露 doctest::doctest header-only 目标，故以 DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
// wrapper 等价还原：basic.cpp / multi_cpp 源文件保持上游原样零改动。
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>
