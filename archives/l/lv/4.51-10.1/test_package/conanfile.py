#!/usr/bin/env python3
"""Conan test_package — lv 4.51-10.1"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LvTestConan(ConanFile):
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
        self.run("which lv", env="conanrun")
        # 用 lv --help 验证二进制可执行（非交互式，不会挂起）
        self.run("lv --help", env="conanrun")
        # 运行 CTest 执行 test.c 的编译验证
        cmake = CMake(self)
        cmake.test()
