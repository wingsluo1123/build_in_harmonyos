#!/usr/bin/env python3
"""Conan test_package — c-blosc2 消费者测试。

构建并运行 test_package，验证 blosc1_compress/blosc1_decompress 往返正确性。
"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(test_bin, env="conanrun")
