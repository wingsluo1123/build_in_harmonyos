#!/usr/bin/env python3
"""Conan test_package — nanojsonc 1.3.0

L1 test: verify the packaged library can be found, linked, and that
the event-driven parser drives real callbacks for object and array JSON.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NanojsoncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # L0d: 必须 self.run() 真实运行消费者二进制（静态库，无需 LD_LIBRARY_PATH）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_nanojsonc")
        self.run(bin_path, env="conanrun")