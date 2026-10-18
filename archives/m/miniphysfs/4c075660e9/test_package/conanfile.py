#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/miniphysfs/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MiniphysfsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # CI 设备沙箱限制 make jobserver mkfifo/fork（EPERM/EAGAIN，见知识 E074/E525、
        # memory-allocators 3.5 CI #64417 同类）：并行构建（-j20）触发
        # "make: jobserver mkfifo: ...: Operation not permitted"。限制为 -j1 串行构建，
        # 避免 jobserver 机制，不改上游源码与共享 CI 脚本。
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_miniphysfs')}", env="conanrun")
