#!/usr/bin/env python3
"""Conan recipe — limonp 0.6.1 (yanyiwu/limonp) on OpenHarmony PC.

limonp 是 cppjieba 作者 yanyiwu 抽出来的 C++ 基础设施头文件库（MIT）：字符串
工具（Split/Join/StringFormat/Trim/Utf8<->Unicode/GBK<->Unicode）、Logging
（XLOG/XCHECK）、Config（key=value 配置解析）、LocalVector（栈上内联缓冲的
小向量）、Closure、ArgvContext、Colors 等。纯 header-only：上游 0.6.1 时代
没有 `add_library(limonp INTERFACE)`，只有测试目标（demo / thread_pool_demo
/ test.run），头文件由消费者直接 `#include <limonp/*.hpp>` 使用。

OHOS 适配要点（四个上游缺陷，见 patches/）：
- **C++11 精确匹配导致 tr1 fallback**：`StdExtension.hpp` 的
  `#elif(__cplusplus == 201103L)` 只在 C++11 精确成立时走
  `<unordered_map>/<unordered_set>`；OHOS 用 C++17（libc++ 无
  `<tr1/unordered_map>`），于是掉进 `#include <tr1/unordered_map>` 编译失败。
  patch 0002 放宽为 `>= 201103L`。
- **ADD_TEST 相对路径 fixture**：顶层 CMakeLists 的
  `ADD_TEST(NAME ./test/test.run COMMAND ./test/test.run)` 用相对 COMMAND +
  默认 WORKING_DIRECTORY（= build 目录），而 TConfig/TMd5/TStdExtension/
  TStringUtil 用相对路径 "../test/testdata/..." 打开 fixture —— 只有 build
  目录恰好是源码根的直接子目录时才解析得到。patch 0001 换成
  `$<TARGET_FILE:...>` + `WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test`。
- **assert(!pthread_create(...)) 在 Release（NDEBUG）下被整体裁剪**：
  TMutexLock.cpp 的 `assert(!pthread_create(...))` 在 Release 下不执行任何
  pthread_create 调用 → 线程从未创建、结果恒空。patch 0004 拆成先调用再断言。
- **/tmp 只读**：TFileLock.cpp 硬编码 "/tmp/limonp_test_filelock"，OHOS 上
  /tmp 是只读 erofs。patch 0003 改用 $TMPDIR（回退当前目录）。

上游测试：顶层 3 个 ctest 用例（./test/test.run / ./test/demo /
./test/thread_pool_demo）；其中 test.run 由 test/unittest/*.cpp 里的 35 个
gtest TEST 宏组成（源码声明 36 个：TCastFloat.cpp 引用缺失头
limonp/CastFloat.hpp，上游从未将其纳入 ADD_EXECUTABLE，aarch64/OHOS 上其余
35 个全部注册、全部执行）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# 上游在顶层 CMakeLists.txt 注册的 ctest 用例数（0.6.1 为 3 个）：
#   ADD_TEST(./test/test.run) + ADD_TEST(./test/demo) +
#   ADD_TEST(./test/thread_pool_demo)
CTEST_EXPECTED_TESTS = 3

# test.run 里实跑的 gtest 用例数。test/unittest/*.cpp 合计 36 个 TEST 宏，
# 其中 TCastFloat.cpp 引用不存在的 limonp/CastFloat.hpp 且未被
# ADD_EXECUTABLE(test.run ...) 收录，因此注册并执行的是 35 个。
GTEST_EXPECTED_TESTS = 35

# ctest 汇总行：`100% tests passed, 0 tests failed out of 3`
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")
# gtest 汇总行：`[  PASSED  ] 35 tests.`
_GTEST_PASSED = re.compile(r"\[\s+PASSED\s+\]\s+(\d+)\s+tests?\.")


class LimonpConan(ConanFile):
    name = "limonp"
    version = "0.6.1"
    description = "Header-only C++ utility library (string utils, logging, config, LocalVector, Closure, ArgvContext)"
    license = "MIT"
    homepage = "https://github.com/yanyiwu/limonp"
    url = ""  # CI fills this
    topics = ("header-only", "string-util", "logging", "utf8", "gbk", "cppjieba", "limonp")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库：package_id 不依赖编译器/构建类型/架构
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(2.6) 太老；CMake 4.x 移除了 <3.5 兼容，
        # 显式放宽策略版本下限，避免 patch 构建元数据。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 层1：上游 ctest 套件（3 个 ctest 用例，含 35 个 gtest 用例）实跑 ──
        # cwd 必须是 build 根目录（CTestTestfile.cmake 在这里）。`-V` 是必需
        # 的：test.run 的 gtest 汇总行只在**测试**的输出里，而
        # --output-on-failure 会把通过用例的输出吃掉，于是"35 个用例"这条
        # 信息就没了 —— 只看 ctest 的 3/3 无法发现 gtest 用例集缩水。
        log = os.path.join(self.build_folder, "ctest.log")
        # 末尾 `|| true` 是为了把 ctest 的原文读回来再判 —— 有用例失败时
        # ctest 返回非 0，self.run 会先抛异常而丢掉日志。
        self.run(
            'ctest -V > "{}" 2>&1 || true'.format(log),
            cwd=self.build_folder,
        )
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        if "No tests were found" in text:
            raise ConanException(
                "ctest registered 0 tests —— 零执行不能算通过。\n" + text[-2000:]
            )
        m = _CTEST_SUMMARY.search(text)
        if m is None:
            raise ConanException(
                "ctest summary line not found — the suite did not run:\n" + text[-2000:]
            )
        failed, total = int(m.group(2)), int(m.group(3))
        if failed != 0:
            raise ConanException(
                "upstream ctest not all green: {} failed out of {}\n".format(failed, total)
                + text[-4000:]
            )
        if total < CTEST_EXPECTED_TESTS:
            raise ConanException(
                "only {} ctest cases were registered (expected >= {}) — test set shrank"
                "\n".format(total, CTEST_EXPECTED_TESTS) + text[-2000:]
            )

        # gtest 层：test.run 内部的逐用例账。ctest 只把整个二进制当成 1 个
        # 用例，所以必须解析 gtest 自己的汇总行才能确认 35 个 TEST 宏全都
        # 注册并执行了。
        if re.search(r"\[\s+FAILED\s+\]", text):
            raise ConanException(
                "gtest reported FAILED cases inside test.run:\n" + text[-4000:]
            )
        g = _GTEST_PASSED.search(text)
        if g is None:
            raise ConanException(
                "gtest summary line '[  PASSED  ] N tests.' not found — "
                "test.run did not run to completion:\n" + text[-4000:]
            )
        gtest_total = int(g.group(1))
        if gtest_total < GTEST_EXPECTED_TESTS:
            raise ConanException(
                "only {} gtest cases ran (expected >= {}) — test set shrank\n".format(
                    gtest_total, GTEST_EXPECTED_TESTS
                )
                + text[-2000:]
            )
        self.output.info(
            "upstream ctest: {} cases registered, {} gtest cases ran, all passed".format(
                total, gtest_total
            )
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # 0.6.1 上游没有 install(EXPORT) / 安装规则：头文件直接打包
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include", "limonp"),
            dst=os.path.join(self.package_folder, "include", "limonp"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "limonp")
        self.cpp_info.set_property("cmake_target_name", "limonp::limonp")
