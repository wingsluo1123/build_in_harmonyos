#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/memory-allocators/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MemoryallocatorsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # R03: 与主配方一致，构建并行度收敛为 -j1（规避 jobserver mkfifo 与并发 fork 限制）。
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        cmake = CMake(self)
        # R03: test 阶段并行度同样收敛为 -j1（规避 jobserver mkfifo 与并发 fork 限制）。
        cmake.test(build_tool_args=["-j1"])
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_memory-allocators')}", env="conanrun")
