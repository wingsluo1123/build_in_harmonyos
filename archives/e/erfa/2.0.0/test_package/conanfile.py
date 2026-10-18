#!/usr/bin/env python3
"""Conan test_package — erfa 2.0.0 L1 test (consumer + OHOS-specific)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ErfaTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_erfa")
        self.run(f'"{test_bin}"', env="conanrun")
        ohos_bin = os.path.join(self.cpp.build.bindirs[0], "test_erfa_ohos")
        self.run(f'"{ohos_bin}"', env="conanrun")
