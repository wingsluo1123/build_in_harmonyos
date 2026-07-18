#!/usr/bin/env python3
"""Conan test_package — qtbase L1 test (R34: 实质调用 Qt6::Core API)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QtBaseTestConan(ConanFile):
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
        # R-CI L0d: test() 必须含 self.run() 直跑测试程序，cmake.test() 不被门禁识别
        test_bin = os.path.join(self.test_build_folder, "test_qtbase")
        self.run(test_bin, env="conanrun")
