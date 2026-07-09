#!/usr/bin/env python3
"""Conan test_package for libzippp — L1 official test.

验证 libzippp 包可以被发现、链接和运行时可用。
CI 通过 conan create 自动执行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibzipppTestConan(ConanFile):
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
