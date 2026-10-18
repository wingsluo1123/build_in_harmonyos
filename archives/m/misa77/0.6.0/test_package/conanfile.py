#!/usr/bin/env python3
"""misa77 0.6.0 test_package — 消费者视角 L1 测试。

CI 通过 `conan create` 自动运行：构建两个测试可执行文件
（test_misa77 与 test_misa77_harmonyos）并在 test() 中显式
以 conanrun 环境执行（E298 virtual-run-env-explicit-run，
满足 L0d 静态指纹 self.run）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Misa77TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_misa77")
        self.run(f'"{test_bin}"', env="conanrun")
        harmonyos_bin = os.path.join(self.cpp.build.bindirs[0], "test_misa77_harmonyos")
        self.run(f'"{harmonyos_bin}"', env="conanrun")