#!/usr/bin/env python3
"""Conan test_package — nr_micro_shell 2.0.0 消费者验证 + 鸿蒙专项测试。

ctest 运行 test.c：通过 shell() 逐字符输入 "hex2dec 0xff\r\n" 等命令，
断言 stdout 出现预期输出 "0xff = 255"，验证第三方使用者可编译、链接、
调用并正常运行（R34：实质调用被测包 API，非空壳）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NrMicroShellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_nr_micro_shell"), env="conanrun")