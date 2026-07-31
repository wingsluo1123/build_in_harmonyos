#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/qtpositioning/{version}/test_package/conanfile.py
"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class QtpositioningTestConan(ConanFile):
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
        # 按仓库惯例直接运行测试二进制；不做静默跳过守卫，
        # 避免 bindirs 为空时测试被悄悄跳过、掩盖编译/链接问题
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_qtpositioning")
        self.run(test_binary, env="conanrun")
