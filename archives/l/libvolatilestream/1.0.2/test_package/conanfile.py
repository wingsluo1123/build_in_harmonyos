#!/usr/bin/env python3
"""Conan test_package for libvolatilestream 1.0.2.

构建并运行消费者测试 test_libvolatilestream（test_package/test.c）。
测试只使用公开 API：volstream_open / volstream_trunc / volstream_getbuf
以及普通 stdio 操作。13 个用例各自输出 TEST PASS/TEST FAIL，
末尾输出 TEST SUMMARY，任一用例失败则进程退出 1。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibvolatilestreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def configure(self):
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile and link validation only")
            return
        test_bin = os.path.join(
            self.cpp.build.bindirs[0], "test_libvolatilestream"
        )
        self.run(test_bin, env="conanrun")
