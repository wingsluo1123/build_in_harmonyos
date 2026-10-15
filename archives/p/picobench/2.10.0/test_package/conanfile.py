#!/usr/bin/env python3
"""Conan test_package — picobench 2.10.0 消费者测试 + 上游官方测试镜像.

三类测试（conan create test 阶段全部真跑）：
1. test_picobench（消费者测试）：以 PICOBENCH 宏注册基准（上游单头实现），
   runner API 运行并验证报告生成（迭代计数>0）
2. test_picobench_basic：上游 test/basic.cpp 原样镜像（6 个 TEST_CASE /
   235 断言：test utils / picostring / state / cmd line / test / compare）
3. test_picobench_multi_cpp：上游 test/multi_cpp/ 原样镜像（1 个 TEST_CASE /
   86 断言，4 个翻译单元验证同套件跨 TU 注册）

上游测试框架为 doctest（上游 CPM 拉取 doctest-util 0.1.2 → doctest-lib
2.4.11），此处以 ohpcd 仓 doctest/2.4.11 同版本等价还原（cpp-lazy/
intrusive-shared-ptr 同款先例）。PICOBENCH_TEST 宏激活假时钟
（picobench.hpp:1519 计数器实现，非真实睡眠），测试为确定性断言。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PicobenchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 上游测试框架：doctest 2.4.11（上游 test/ 经 CPM doctest-util 拉取
        # 的同一版本；ohpcd 仓已发布，CI --build=missing 可直接消费）
        self.requires("doctest/2.4.11")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2 precedent).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d/R34：实际运行全部测试二进制（cmake.test 跑 CTest 注册的
        # 3 个目标 + 显式 self.run 逐一真跑双保险；conanbuild 环境携带
        # profile 的 LD_LIBRARY_PATH，OHOS libc++ 可正确加载）
        cmake = CMake(self)
        cmake.test()
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_picobench", "test_picobench_basic", "test_picobench_multi_cpp"):
            self.run(os.path.join(bindir, exe), env="conanbuild")
