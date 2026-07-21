#!/usr/bin/env python3
"""Conan test_package — ki18n L1 test (R34: 实质调用 KF6::I18n API)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KI18nTestConan(ConanFile):
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
        # R-CI7: Conan 2.x 属性名是 self.build_folder（非 self.test_build_folder，后者 AttributeError）
        test_bin = os.path.join(self.build_folder, "test_ki18n")
        self.run(test_bin, env="conanrun")
