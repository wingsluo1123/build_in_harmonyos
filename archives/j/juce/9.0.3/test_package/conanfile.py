#!/usr/bin/env python3
"""Conan test_package — juce 9.0.3 消费者验证 (鸿蒙专项).

Consumer model follows JUCE's official usage: an application includes the
public module headers and compiles the module sources into its own target.
This test compiles juce_core module sources from the installed include tree,
links and runs the binary on the OHOS target — verifying a third-party
consumer can build, link, call a public API and observe a real result.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JuceTestConan(ConanFile):
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
        # 直接运行鸿蒙专项消费者测试二进制, 验证链接与公开 API 可用性
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_juce"), env="conanrun")